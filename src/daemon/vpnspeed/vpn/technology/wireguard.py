import io
import os
import asyncio
import tempfile
from vpnspeed.constans import DEFAULT_SESSION_NAME
from .interfaces import VPNTechnology
from vpnspeed.container import ContainerEnvironment
from vpnspeed.errors import *

from vpnspeed import log, errors

import time


_NAME = "wireguard"
_CONFIG = "/etc/wireguard/" + DEFAULT_SESSION_NAME + ".conf"


class WireGuard(VPNTechnology):
    @staticmethod
    def get_name() -> str:
        return _NAME

    async def start(self, env: ContainerEnvironment, config: str, params: dict = None):
        log.info("Starting wireguard")
        self._env = env
        await self._env.write_file(_CONFIG, config)
        returncode, stdout = await self._env.exec(
            "wg-quick", ["up", DEFAULT_SESSION_NAME], allow_error=True
        )
        if returncode != 0:
            raise VPNConnectionFailed("Failed to initiate wireguard's.")

    async def stop(self):
        log.info("Stopping wireguard")
