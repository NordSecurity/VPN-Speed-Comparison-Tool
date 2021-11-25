import asyncio
import re
from asyncio.subprocess import Process, PIPE
from .dynamic import dynamic
from .interfaces import VPNProvider
from vpnspeed import log
from vpnspeed.model import *
from vpnspeed.errors import *
from vpnspeed.container import ContainerEnvironment


_NAME = "expressvpn-app"
_APP = "/usr/bin/expressvpn"


@dynamic
class ExpressVpnApp(VPNProvider):

    __city_to_id: dict = None

    def __init__(self, creds: VPNCredentials):
        self._creds = creds

    async def get_cities(self, country: str) -> set:
        async with ContainerEnvironment(_NAME) as env:
            try:
                await self.login(env)
            except:
                log.info("Failed to log in.")
                return None
            returncode, stdout = await env.exec(
                "/usr/bin/expressvpn", ["list", "all"], output=True
            )
            if returncode != 0 or stdout is None:
                return None
            self.__city_to_id = {}
            country_entries = [
                entry for entry in stdout.split("\n") if entry.startswith(country)
            ]
            if not country_entries:
                return None
            regex = r"(^\w*)\s*[\w|\s()]*- (\w*[ ?\w]*)"

            for entry in country_entries:
                matches = re.findall(regex, entry)
                if not matches:
                    log.info("No {} matches found!".format(entry))
                    return None
                city_name = matches[0][1][:-1].strip()
                self.__city_to_id[city_name] = matches[0][0]
            cities = set(self.__city_to_id.keys())
            if cities is not None and len(cities) != 0:
                return cities
            return None

    @staticmethod
    def get_name() -> str:
        return _NAME

    @classmethod
    def get_technologies(cls):
        return [
            VPNTechnology("openvpn", ["udp", "tcp"]),
            VPNTechnology("lightway"),
        ]

    async def login(self, env):
        self._env = env
        returncode, stdout = await self._env.exec(
            "/usr/bin/express-activate", self._creds.password, output=True
        )
        ok = True if returncode == 0 and stdout is not None else False
        log.debug("Activation: {}, return code: {}".format(ok, returncode))
        if not ok:
            raise TestRunError(
                "Failed login proccess with code: {}, and message: '{}'",
                returncode,
                stdout,
            )

    async def connect(self, env, group: TestGroup, case: TestCase):
        self._env = env
        if case.technology != "openvpn" and case.technology != "lightway":
            raise TechnologyNotSupported(
                "ExpressVPN does not support {} tech.".format(case.technology)
            )
        proto = "udp"
        if case.technology == "lightway":
            proto = "lightway_udp"
        elif case.protocol is not None:
            if case.protocol not in ["udp", "tcp"]:
                raise ProtocolNotSupported(
                    "Protocol {} invalid for openvpn".format(case.protocol)
                )
            proto = case.protocol

        log.info("Running {} protocol ".format(_APP))
        retcode, stdout = await self._env.exec(_APP, ["protocol", proto], output=True)
        if retcode != 0 or stdout is None:
            raise ProtocolNotSupported(
                "Unable to configure {} protocol for ExpressVPN.".format(proto)
            )

        location = group.vpn_country
        if location is None:
            raise TestRunError("VPN target country is not set!")
        if location == "auto":
            location = "smart"
        elif group.vpn_city and group.vpn_city in self.__city_to_id:
            location = self.__city_to_id[group.vpn_city]

        retcode, stdout = await self._env.exec(_APP, ["connect", location], output=True)
        if retcode != 0 or stdout is None:
            raise VPNConnectionFailed("Failed to connect to ExpressVPN Servers")

    async def disconnect(self):
        retcode, stdout = await self._env.exec(_APP, "disconnect", output=True)
        disconnected = True if retcode == 0 and stdout is not None else False
        if not disconnected:
            await self._env.exec("service", ["expressvpn", "restart"])
