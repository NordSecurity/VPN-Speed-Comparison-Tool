import asyncio
import re
from asyncio.subprocess import Process, PIPE
from .dynamic import dynamic
from .interfaces import VPNProvider
from vpnspeed import log
from vpnspeed.model import *
from vpnspeed.errors import *
from vpnspeed.utils import cc_to_iso
from vpnspeed.container import ContainerEnvironment

_NAME = "purevpn-app"
_APP = "/usr/bin/purevpn-cli"
_USER = "standard"


@dynamic
class PureVpnApp(VPNProvider):
    def __init__(self, creds: VPNCredentials):
        self._creds = creds

    @staticmethod
    def get_name() -> str:
        return _NAME

    @classmethod
    def get_technologies(cls):
        return [
            VPNTechnology("openvpn", ["udp", "tcp"]),
        ]

    async def get_cities(self, country: str) -> set:
        return None

    async def login(self, env):
        returncode, stdout = await env.exec(
            "/usr/bin/purevpn-login",
            [self._creds.username, self._creds.password],
            output=True,
            user=_USER,
        )
        ok = True if returncode == 0 and stdout is not None else False
        log.debug("Login successful: {}, return code: {}".format(ok, returncode))

    async def connect(self, env, group: TestGroup, case: TestCase):
        self._env = env
        if case.technology != "openvpn":
            raise TechnologyNotSupported(
                "{} does not support {} tech.".format(_NAME, case.technology)
            )

        if case.protocol is not None:
            if case.protocol not in ["udp", "tcp"]:
                raise ProtocolNotSupported(
                    "Protocol {} invalid for openvpn".format(case.protocol)
                )
        if group.vpn_country is None:
            raise TestRunError("VPN target country is not set!")
        if group.vpn_country == "auto" and case.protocol != "udp":
            raise ProtocolNotSupported("Autoconnect works only with udp protocol.")
        log.info("Running {} protocol: {} ".format(_APP, case.protocol))
        retcode, stdout = await self._env.exec(
            _APP, ["-p", case.protocol], output=True, user=_USER
        )
        if retcode != 0 or stdout is None:
            raise ProtocolNotSupported(
                "Unable to configure {} protocol for {}.".format(case.protocol, _NAME)
            )

        location = group.vpn_country
        if location == None or location == "auto":
            retcode, stdout = await self._env.exec(
                _APP, "-c", output=True, allow_error=True, user=_USER
            )
        else:
            retcode, stdout = await self._env.exec(
                _APP,
                ["-c", cc_to_iso(group.vpn_country)],
                output=True,
                allow_error=True,
                user=_USER,
            )

        if retcode != 0 or stdout is None:
            raise VPNConnectionFailed("Failed to connect to {} Servers".format(_NAME))

    async def disconnect(self):
        await self._env.exec(_APP, "-d")
        log.info("Disconnected")
