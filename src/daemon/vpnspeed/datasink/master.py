import asyncio
from typing import List
from vpnspeed.model import *
from .dynamic import DynamicDataSink, DynamicDataBackup, BACKUPS
from .interfaces import DataSink, DataBackup


DEFAULT_BACKUP = "sqlite"
DEFAULT_BACKUP_URL = "/var/run/vpnspeed/vpnspeed.db"


class MasterSink:
    _sinks: Dict[str, DataSink]
    _backup_default: DataBackup
    _backups: Dict[str, DataBackup]
    _probe: Probe

    def __init__(self):
        self._sinks = dict()
        self._backup_default = DynamicDataBackup(DEFAULT_BACKUP)
        asyncio.create_task(self._backup_default.start(DEFAULT_BACKUP_URL))
        self._backups = dict()
        self._probe = None

    @property
    def backup(self) -> DataBackup:
        # Return only first assigned or default.
        return next(iter(self._backups.values()), self._backup_default)

    async def set_probe(self, probe: Probe):
        self._probe = probe

    async def add_sinks(self, sinks: List[DataSink]):
        for sink in sinks:
            if sink.name in BACKUPS:
                if sink.type is not None:
                    plugin = DynamicDataBackup(sink.type)
                else:
                    plugin = DynamicDataBackup(sink.name)
                if sink.as_backup:
                    self._backups[sink.name] = plugin
            else:
                if sink.type is not None:
                    plugin = DynamicDataSink(sink.type)
                else:
                    plugin = DynamicDataBackup(sink.name)

            await plugin.start(sink.url, sink.params)
            self._sinks[sink.name] = plugin

    async def update_sinks(self, sinks: List[DataSink]):
        for sink in sinks:
            plugin = self._sinks[sink.name]
            await plugin.stop()

            if sink.name in self._backups and not sink.as_backup:
                del self._backups[sink.name]
            if sink.name not in self._backups and sink.as_backup:
                self._backups[sink.name] = plugin

            await plugin.start(sink.url, sink.params)

    async def remove_sinks(self, sinks: List[DataSink]):
        for sink in sinks:
            plugin = self._sinks[sink.name]
            await plugin.stop()
            del self._sinks[sink.name]
            if sink.name in self._backups:
                del self._backups[sink.name]

    async def send_data(self, group: TestGroup, case: TestCase, run: TestRun):
        for sink in self._sinks.values():
            asyncio.create_task(sink.send(self._probe, group, case, run))
