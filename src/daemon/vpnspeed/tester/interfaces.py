import asyncio
from abc import ABC, abstractmethod
from vpnspeed.model import *
from typing import List
from datetime import datetime
from vpnspeed import log
from vpnspeed.container import ContainerEnvironment


class Tester(ABC):
    @abstractmethod
    async def resolve(self, env: ContainerEnvironment, cgroup: TestGroup) -> TestGroup:
        raise NotImplementedError()

    @abstractmethod
    async def test(self, group: TestGroup, case: TestCase) -> TestRun:
        raise NotImplementedError()


class DummyTester(Tester):
    async def resolve(self, env: ContainerEnvironment, cgroup: TestGroup) -> TestGroup:
        return TestGroup(
            **vars(cgroup), target_server=cgroup.target_country + "-fake-server"
        )

    async def test(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ) -> TestRun:
        log.debug(
            "Testing: {} {} {} => {} {} {}".format(
                group.vpn_country,
                group.target_country,
                group.target_server,
                case.vpn,
                case.technology,
                case.protocol,
            )
        )
        # await asyncio.sleep(10)
        return TestRun(
            timestamp=str(datetime.now()),
            download="100",
            upload="10",
        )
