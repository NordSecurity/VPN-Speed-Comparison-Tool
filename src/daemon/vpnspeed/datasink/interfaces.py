from abc import ABC, abstractmethod, abstractclassmethod
from typing import List, Tuple, Set
from datetime import date
from vpnspeed.model import Probe, TestGroup, TestCase, TestRun


class DataSink(ABC):
    @abstractclassmethod
    def get_name(cls) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def start(self, url: str, params: dict = None):
        raise NotImplementedError()

    @abstractmethod
    async def stop(self):
        raise NotImplementedError()

    @abstractmethod
    async def send(self, probe: Probe, group: TestGroup, case: TestCase, run: TestRun):
        raise NotImplementedError()


class DataBackup(DataSink):
    @abstractmethod
    async def retrieve(
        self, *, group: TestGroup = None, start: date = None, end: date = None
    ) -> List[dict]:
        raise NotImplementedError()

    @abstractmethod
    async def retrieve_groups(self) -> Set[TestGroup]:
        raise NotImplementedError()
