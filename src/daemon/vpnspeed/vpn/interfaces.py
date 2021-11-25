from abc import ABC, abstractmethod, abstractstaticmethod, abstractclassmethod
from vpnspeed.model import *
from vpnspeed.container import ContainerEnvironment


class VPNProvider(ABC):
    @abstractstaticmethod
    def get_name() -> str:
        raise NotImplementedError()

    @abstractclassmethod
    def get_technologies(cls) -> List[VPNTechnology]:
        raise NotImplementedError()

    @abstractmethod
    def __init__(self, creds: VPNCredentials):
        raise NotImplementedError()

    @abstractmethod
    async def login(self, env: ContainerEnvironment, creds: VPNCredentials = None):
        raise NotImplementedError()

    @abstractmethod
    async def connect(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ):
        raise NotImplementedError()

    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError()

    @abstractmethod
    async def get_cities(self, country: str) -> set:
        raise NotImplementedError()
