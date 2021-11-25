from abc import ABC, abstractmethod, abstractstaticmethod
from vpnspeed.container import ContainerEnvironment


class VPNTechnology(ABC):
    @abstractstaticmethod
    def get_name() -> str:
        raise NotImplementedError()

    @abstractmethod
    async def start(self, env: ContainerEnvironment, config: str, params: dict = None):
        raise NotImplementedError()

    @abstractmethod
    async def stop(self):
        raise NotImplementedError()
