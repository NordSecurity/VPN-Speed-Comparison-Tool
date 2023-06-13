import asyncio
from aiorwlock import RWLock
from copy import deepcopy
from datetime import datetime, date
from typing import List, Set, Dict, Tuple

from vpnspeed import log, errors
from vpnspeed.probe import make_probe
from vpnspeed.constans import DEFAULT_TESTING_INTERVAL
from vpnspeed.datasink import DataSink, DynamicDataSink, DynamicDataBackup, MasterSink
from vpnspeed.vpn import DynamicVPN
from vpnspeed.tester import Tester, SpeedTestCliTester
from vpnspeed.reporting import *

from .model import *
from .diff import *
from .select import select
from .runner import Runner


class Service:
    _tester: Tester
    _context: Context
    _clock: RWLock
    _task: asyncio.Task = None

    _probe: Probe
    _credentials: Dict[str, VPNCredentials]

    _sink: MasterSink
    _vpn: DynamicVPN
    _runner: Runner

    def __init__(self, tester: Tester = None):
        self._tester = tester or SpeedTestCliTester()
        self._clock = RWLock()
        self._probe = None
        self._vpn = DynamicVPN()
        self._sink = MasterSink()
        self._runner = Runner(self._vpn, self._tester, self._sink)

    async def make_report(
        self, path: str, filter_: ReportFilter = ReportFilter.default()
    ):
        return await ReportGenerator(self._sink.backup).make_plots(path, filter_)

    async def get_data(
        self, group: TestGroup = None, start: date = None, end: date = None
    ) -> List[dict]:
        return await self._sink.backup.retrieve()

    async def get_context(self) -> Context:
        async with self._clock.reader:
            c = deepcopy(self._context)
            c.probe = Probe(
                **{
                    **vars(self._probe),
                    **(c.probe and vars(c.probe) or {}),
                    "start_time": self._probe.start_time,
                }
            )
            c.groups = await self._runner.get_groups()
            return c

    async def start(self, context: Context = None):
        async with self._clock.writer:
            self._probe = await make_probe()
            if context:
                self._context = context
                self._context.state = State.idle
            else:
                self._context = Context(
                    state=State.idle,
                    config=Config(
                        mode=Mode.continuous,
                        repeats=1,
                        interval=DEFAULT_TESTING_INTERVAL,
                    ),
                )
            await self._sink.set_probe(self._probe)

    async def update(self, context: Context, context_config_update: bool = False):
        """Update internal state based on context differences."""
        async with self._clock.writer:
            if context_config_update:
                self._context, actions = diff_context(self._context, context)
            else:
                # Clean current configuration and set new context:
                default_context = Context(
                    state=State.idle,
                    config=Config(
                        mode=Mode.continuous,
                        repeats=1,
                        interval=DEFAULT_TESTING_INTERVAL,
                    ),
                )
                self._context, actions = diff_context(self._context, default_context)
                await self.execute(actions)
                self._context, actions = diff_context(self._context, context)
            await self._runner.set_context_params(
                self._context.config.interval, self._context.config.common_cities
            )
            await self.execute(actions)
            if self._context.probe is not None:
                await self._sink.set_probe(
                    Probe(
                        ip=self._probe.ip,
                        country=self._probe.country,
                        country_code=self._probe.country_code,
                        city=self._probe.city,
                        provider=self._probe.provider,
                        start_time=self._probe.start_time,
                        name=self._context.probe.name,
                    )
                )

    async def execute(self, actions: List[Action]):
        for action in sorted(actions, key=lambda x: x.mark):
            log.debug("ACTION: %s", repr(action))
            await _ACTION_MAP[action.mark](self, action)

    async def _stop(self, _=None):
        if self._task and self._task.cancel():
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None

    async def _quit(self, _=None):
        await self._stop()
        asyncio.get_event_loop().stop()

    async def _start(self, _=None):
        await self._stop()
        self._task = asyncio.create_task(
            self._runner.run(self._context.config.mode, self._context.config.repeats)
        )
        self._context.state = State.run
        self._task.add_done_callback(self._idle)

    def _idle(self, future=None):
        self._context.state = State.idle

    async def _remove_groups(self, act: RemoveGroups):
        await self._runner.remove_groups(act.groups)

    async def _add_groups(self, act: AddGroups):
        await self._runner.add_groups(act.groups)

    async def _remove_cases(self, act: RemoveCases):
        await self._runner.remove_cases(act.cases)

    async def _add_cases(self, act: AddCases):
        await self._runner.add_cases(act.cases)

    async def _add_sinks(self, act: AddDataSinks):
        await self._sink.add_sinks(act.sinks)

    async def _update_sinks(self, act: UpdateDataSinks):
        await self._sink.update_sinks(act.sinks)

    async def _remove_sinks(self, act: RemoveDataSinks):
        await self._sink.remove_sinks(act.sinks)

    async def _add_vpns(self, act: AddVPNs):
        await self._vpn.add_providers(act.vpns)

    async def _update_vpns(self, act: UpdateVPNs):
        await self._vpn.update_providers(act.vpns)

    async def _remove_vpns(self, act: RemoveVPNs):
        await self._vpn.remove_providers(act.vpns)


_ACTION_MAP = {
    Stop.mark: Service._stop,
    Start.mark: Service._start,
    Quit.mark: Service._quit,
    AddGroups.mark: Service._add_groups,
    RemoveGroups.mark: Service._remove_groups,
    AddCases.mark: Service._add_cases,
    RemoveCases.mark: Service._remove_cases,
    AddDataSinks.mark: Service._add_sinks,
    UpdateDataSinks.mark: Service._update_sinks,
    RemoveDataSinks.mark: Service._remove_sinks,
    AddVPNs.mark: Service._add_vpns,
    UpdateVPNs.mark: Service._update_vpns,
    RemoveVPNs.mark: Service._remove_vpns,
}
