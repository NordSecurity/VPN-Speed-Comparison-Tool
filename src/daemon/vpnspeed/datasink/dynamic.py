import asyncio

from typing import List, Tuple, Dict, Set
from .interfaces import DataSink, DataBackup
from vpnspeed.model import Probe, TestGroup, TestCase, TestRun
from vpnspeed import log


SINKS = {}


def dynamic_sink(cls):
    assert issubclass(cls, DataSink), f"{cls} is not subclass of {DataSink}"
    SINKS[cls.get_name()] = cls
    return cls


BACKUPS = set()


def dynamic_backup(cls):
    cls = dynamic_sink(cls)
    assert issubclass(cls, DataBackup), f"{cls} is not subclass of {DataBackup}"
    BACKUPS.add(cls.get_name())
    return cls


class DynamicDataSink(DataSink):
    _plugin: DataSink

    def __init__(self, name: str):
        if name not in SINKS:
            raise ValueError(
                "`plugin={}` unknown, valid values: [{}]".format(
                    name,
                    ", ".join(SINKS.keys()),
                )
            )
        self._plugin = SINKS[name]()

    @classmethod
    def get_name(cls) -> str:
        return "dynamic"

    @property
    def name(self) -> str:
        return self._plugin.get_name()

    async def start(self, url: str, params: dict = None):
        log.debug("Starting DataSink: %s", self.name)
        try:
            return await self._plugin.start(url, params)
        except BaseException as e:
            log.warning("Start Failed for DataSink: %s\n%s", self.name, e)

    async def stop(self):
        log.debug("Stoping DataSink: %s", self.name)
        try:
            return await self._plugin.stop()
        except BaseException as e:
            log.warning("Stop failed for DataSink: %s\n%s", self.name, e)

    async def send(self, probe: Probe, group: TestGroup, case: TestCase, run: TestRun):
        log.debug("Sending to DataSink: %s", self.name)
        try:
            log.info("Sending to: {}".format(self.name))
            await self._plugin.send(probe, group, case, run)
            log.info("Sent to: {}".format(self.name))
        except BaseException as e:
            log.warning("Send Failed for DataSink: %s\n%s", self.name, e)


class DynamicDataBackup(DynamicDataSink, DataBackup):
    _plugin: DataBackup

    @staticmethod
    def __validate(name: str):
        if name not in BACKUPS:
            raise ValueError(
                "`backup plugin={}` unknown, valid values: [{}]".format(
                    name,
                    ", ".join(BACKUPS),
                )
            )

    def __init__(self, name: str):
        self.__validate(name)
        super().__init__(name)

    async def retrieve(self, **kwargs) -> List[dict]:
        return await self._plugin.retrieve(**kwargs)

    async def retrieve_groups(self) -> Set[TestGroup]:
        return await self._plugin.retrieve_groups()
