import asyncio
import random
from aiorwlock import RWLock
from typing import List, Set, Dict
from .diff import *
from .select import select
from .model import *
from vpnspeed import log, errors
from vpnspeed.probe import make_probe, make_env_probe
from vpnspeed.datasink import MasterSink
from vpnspeed.vpn import DynamicVPN
from vpnspeed.tester import Tester, SpeedTestCliTester
from vpnspeed.container import ContainerEnvironment


class Runner:

    _clock: RWLock
    _vpn: DynamicVPN
    _tester: Tester
    _sink: MasterSink

    _groups: List[Group]
    _group_index: Dict[TestGroup, Group]
    _case_index: Dict[TestGroup, Dict[TestCase, Case]]

    _test_cases: Set[TestCase]
    _failing_cases: Set[TestCase]

    _interval: int
    _common_cities: bool

    def __init__(self, vpn, tester, sink):
        self._clock = RWLock()
        self._vpn = vpn
        self._tester = tester
        self._sink = sink

        self._groups = list()
        self._group_index = dict()
        self._case_index = dict()
        self._test_cases = set()
        self._failing_cases = set()

        self._interval = 0
        self._common_cities = False

    async def set_context_params(self, interval: int, common_cities: bool):
        self._interval = interval
        self._common_cities = common_cities

    async def remove_groups(self, test_groups: Set[TestGroup]):
        async with self._clock.writer:
            cleaned_groups = []
            for group in self._groups:
                if group.group in test_groups:
                    del self._group_index[group.group]
                    del self._case_index[group.group]
                else:
                    cleaned_groups.append(group)
            self._groups = cleaned_groups

    async def add_groups(self, test_groups: Set[TestGroup]):
        async with self._clock.writer:
            for test_group in test_groups:
                group = Group(group=deepcopy(test_group), cases=[])
                self._case_index[test_group] = dict()
                self._add_cases_for_group(group, self._test_cases)
                self._group_index[test_group] = group
                self._groups.append(group)

    async def remove_cases(self, test_cases: Set[TestCase]):
        async with self._clock.writer:
            self._test_cases.difference_update(test_cases)
            self._failing_cases.difference_update(test_cases)
            for group in self._groups:
                test_cases = []
                for case in group.cases:
                    if case.case in test_cases:
                        del self._case_index[group.group][case.case]
                    else:
                        test_cases.append(case)
                group.cases = test_cases

    async def add_cases(self, test_cases: Set[TestCase]):
        async with self._clock.writer:
            self._test_cases.update(test_cases)
            for group in self._groups:
                self._add_cases_for_group(group, test_cases)

    async def get_groups(self) -> List[Group]:
        async with self._clock.reader:
            return deepcopy(self._groups)

    async def random_city_check(self, country: str) -> list:
        city = await self._vpn.get_cities(country)
        if city is None or len(city) == 0:
            return None
        log.debug("City is: {}".format(city))
        return random.choice(list(city))

    async def run(self, mode: Mode, repeats: int):
        try:
            runs = 0
            group = None
            while True:
                groups = await self.get_groups()
                groups_len = groups and len(groups) or 0
                cases_len = len(next(iter(groups), Group(group=None, cases=[])).cases)
                run_target = groups_len * cases_len
                log.info("Run: {}/{}".format(runs, run_target))
                log.info("group count: {}".format(groups_len))
                if runs >= run_target:
                    log.debug("Ran {} tests, clear all fails".format(runs))

                    if mode == Mode.once:
                        return
                    runs = 0
                    group = None

                new_group, case = select(groups)
                if (
                    not group
                    or group.vpn_country != new_group.vpn_country
                    or group.target_country != new_group.target_country
                ):
                    group = new_group
                    if self._common_cities and group.vpn_country != "auto":
                        group = TestGroup(
                            vpn_country=group.vpn_country,
                            target_country=group.target_country,
                            vpn_city=await self.random_city_check(group.vpn_country),
                        )
                        self._group_index[group] = self._group_index.pop(new_group)
                        self._case_index[group] = self._case_index.pop(new_group)
                        self._group_index[group].group = group
                if not group or not case:
                    log.debug("Nothing found to run, clear all fails")
                    await self._clear_fails()
                    continue

                for _ in range(repeats):
                    await self._run_case(group, case)
                runs += 1

            log.debug("Done running the tests")
        except asyncio.CancelledError:
            log.info("Worker stopped")
        except Exception as e:
            log.exception("Unknown error:\n%s", e)

    def _add_cases_for_group(self, group: Group, test_cases: Set[TestCase]):
        min_runs = min([0, *(c.run_count for c in group.cases)])
        for test_case in test_cases:
            case = Case(
                case=deepcopy(test_case),
                run_count=min_runs,
                fail_count=-1 if test_case in self._failing_cases else 0,
            )
            group.cases.append(case)
            if group.group not in self._case_index:
                self._case_index[group.group] = dict()
            self._case_index[group.group][test_case] = case

    async def _wait_delay_interval(self):
        log.info("Start waiting interval: {}s".format(self._interval))
        await asyncio.sleep(self._interval)
        log.info("Finished waiting")

    async def _add_run(
        self, test_group: TestGroup, test_case: TestCase, test_run: TestRun
    ):
        async with self._clock.writer:
            case_ = self._case_index[test_group][test_case]
            case_.run_count += 1

    async def _add_failing_group(self, test_group: TestGroup):
        async with self._clock.writer:
            for case in self._group_index[test_group].cases:
                case.run_count += 1
                case.fail_count += 1
                failing_index = case.run_count / case.fail_count
                if case.run_count > 3 and failing_index < 1.3:
                    self._group_index[test_group].failing = True

    async def _add_failing_case(self, test_case: TestCase):
        async with self._clock.writer:
            self._failing_cases.add(test_case)
            for cases in self._case_index.values():
                cases[test_case].run_count += 1
                cases[test_case].fail_count = -1

    async def _fail_run(self, group: TestGroup, case: TestCase):
        async with self._clock.writer:
            self._case_index[group][case].run_count += 1
            self._case_index[group][case].fail_count += 1

    async def _run_case(self, group: TestGroup, case: TestCase):
        try:
            log.info(
                "Testing: {} ({}) <-> {} => {} - {} - {}".format(
                    group.vpn_country,
                    group.vpn_city,
                    group.target_country,
                    case.vpn,
                    case.technology,
                    case.protocol,
                )
            )

            async with ContainerEnvironment(case.vpn, case.technology) as env:
                if env.get_error_message() is not None:
                    raise errors.VPNConnectionFailed(
                        "Failed to create {} container with error:\n{}".format(
                            case.technology, env.get_error_message()
                        )
                    )
                await env.exec(
                    "echo",
                    "{}_{} starting...".format(
                        case.vpn, case.technology.replace("/", "-")
                    ),
                )
                log.info(
                    "{}_{} starting...".format(
                        case.vpn, case.technology.replace("/", "-")
                    )
                )
                local_probe = await make_env_probe(env)

                async with self._vpn.session(env, group, case):
                    # Some protocols do not activate instantly, try to verify connection using a back off
                    vpn_probe = None
                    for i in range(8):
                        probe = await make_env_probe(env)
                        if local_probe.ip != probe.ip:
                            vpn_probe = probe
                            break
                        await asyncio.sleep(1 * (2 ** i))
                    if vpn_probe is None:
                        raise errors.VPNConnectionFailed()
                    log.info("Connected from {} to {}".format(local_probe, vpn_probe))

                    if group.vpn_country != "auto":
                        if vpn_probe.country_code != group.vpn_country:
                            raise errors.VPNConnectionFailed(
                                "Connected to {}, instead of {}".format(
                                    vpn_probe.country_code, group.vpn_country
                                )
                            )

                    run: TestRun = await self._tester.test(env, group, case)
                    await self._add_run(group, case, run)

                    log.info(
                        "TestRun to Location({}, {}, {}, {}, {}) successfull.".format(
                            run.server_ip,
                            run.server_name,
                            run.server_country_code,
                            run.server_country,
                            run.server_location,
                        )
                    )

                detailed_group = TestGroup(
                    **{**vars(group), **{"vpn_city": vpn_probe.city}}
                )

            asyncio.create_task(self._sink.send_data(detailed_group, case, run))
            await self._wait_delay_interval()
        except errors.TestGroupError as e:
            log.error("Test group failed: {}\n{}".format(type(e), e))
            await self._add_failing_group(group)

        except errors.TestCaseError as e:
            log.error("Test case failed: {}\n{}".format(type(e), e))
            await self._add_failing_case(case)

        except errors.TestRunError as e:
            log.error("Test run failed: {}\n{}".format(type(e), e))
            await self._fail_run(group, case)
            await self._wait_delay_interval()

    async def _clear_fails(self):
        async with self._clock.writer:
            for group in self._groups:
                group.failing = False
                for case in group.cases:
                    case.fail_count = 0
            self._failing_cases = set()
