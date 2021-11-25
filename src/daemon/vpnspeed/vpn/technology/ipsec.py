import io
import os
import asyncio
from vpnspeed.constans import DEFAULT_SESSION_NAME
from vpnspeed.errors import *
from .interfaces import VPNTechnology
from vpnspeed.container import ContainerEnvironment
from vpnspeed import log


_NAME = "ipsec/ikev2"
_CONFIG = "/etc/ipsec.d/" + DEFAULT_SESSION_NAME + ".conf"
_SECRETS = "/etc/ipsec.secrets"


class IPSec(VPNTechnology):
    @staticmethod
    def get_name() -> str:
        return _NAME

    async def start(self, env: ContainerEnvironment, config: str, params: dict = None):
        self._env = env
        if params is None or "username" not in params or "password" not in params:
            raise TechnologyAuthFailed("IPSec/IKEv2's credentials not supplied.")

        await self._env.write_file(_CONFIG, config)
        await self._env.write_file(
            _SECRETS, "{} : EAP {}".format(params["username"], params["password"])
        )
        await self._env.exec("/usr/sbin/ipsec", "restart", allow_error=True)
        await asyncio.sleep(1)
        await self._env.exec("/usr/sbin/ipsec", ["up", DEFAULT_SESSION_NAME])

    async def stop(self):
        log.info("Stopping ipsec")
        await self._env.exec("/usr/sbin/ipsec", ["down", DEFAULT_SESSION_NAME])
        await self._env.exec("/usr/sbin/ipsec", "stop")
