import io
import os
import tempfile
import asyncio
from asyncio.subprocess import STDOUT
import pexpect
import time
from vpnspeed import resources, log
from vpnspeed.constans import DEFAULT_SESSION_NAME, DEFAULT_SUBPROCESS_TIMEOUT
from vpnspeed.errors import *
from .interfaces import VPNTechnology
from vpnspeed.container import ContainerEnvironment


class ToLog(io.RawIOBase):
    def write(self, b: bytes):
        log.debug(b.decode("utf-8"))


_NAME = "openvpn"


class OpenVPN(VPNTechnology):
    _openvpn: pexpect.spawn
    _config_file: str

    @staticmethod
    def get_name() -> str:
        return _NAME

    async def vpn_init(self, timeout=3):
        timeout = time.time() + (60 * timeout)
        while True:
            if time.time() > timeout:
                return False
            ret_code, stdout = await self._env.read_proc_stdout(self._proc_id)
            if ret_code != 0 or stdout is None:
                raise VPNConnectionFailed("OpenVPN's failed to init openvpn.")
            self._openvpn = stdout
            if self._openvpn.find("Initialization Sequence Complete") != -1:
                return True
            await asyncio.sleep(1)

    async def start(self, env: ContainerEnvironment, config: str, params: dict = None):
        self._env = env
        self._config_file = "/tmp/{}.ovpn".format(DEFAULT_SESSION_NAME)
        login_file = "/tmp/{}.login".format(DEFAULT_SESSION_NAME)
        if params is None or "username" not in params or "password" not in params:
            raise TechnologyAuthFailed("OpenVPN's credentials not supplied.")

        await env.write_file(self._config_file, config)
        await env.write_file(
            login_file, "{}\n{}\n".format(params["username"], params["password"])
        )

        try:
            ret_code, stdout = await self._env.sub_exec(
                "/usr/sbin/openvpn",
                [
                    "--config",
                    self._config_file,
                    "--verb",
                    "4",
                    "--auth-user-pass",
                    login_file,
                    "--script-security",
                    "2",
                    "--up",
                    "/etc/openvpn/update-resolv-conf",
                ],
            )
            if ret_code != 0 or stdout is None:
                raise VPNConnectionFailed("Failed to initiate OpenVPN's.")
            self._proc_id = int(stdout)
            init_completed = await self.vpn_init(5)
            if not init_completed:
                await self.stop()
                raise VPNConnectionFailed("Failed to initiate OpenVPN's.")
        finally:
            await env.delete_file(login_file)

    async def stop(self):
        log.info("Stopping openvpn")
        try:
            if self._proc_id is None:
                return
            await self._env.kill_proc(self._proc_id)
            self._proc_id = None
        finally:
            await self._env.delete_file(self._config_file)
