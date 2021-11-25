import asyncio
import re
import yaml
from asyncio.subprocess import Process, PIPE
from .dynamic import dynamic
from .interfaces import VPNProvider
from vpnspeed import resources, log
from vpnspeed.model import *
from vpnspeed.errors import *
from vpnspeed.container import ContainerEnvironment

from vpnspeed.utils import cc_to_iso, iso_to_cc


_NAME = "pia-app"
_APP = "/usr/local/bin/piactl"


@dynamic
class PiaApp(VPNProvider):
    CONFIG = yaml.safe_load(resources.resource_stream("static.yaml"))

    def __init__(self, creds: VPNCredentials):
        self._creds = creds

    @staticmethod
    def get_name() -> str:
        return _NAME

    @classmethod
    def get_technologies(cls):
        return [
            VPNTechnology("openvpn", ["udp"]),
            VPNTechnology("wireguard"),
        ]

    async def get_countries(self, env: ContainerEnvironment):
        returncode, stdout = await self._env.exec(_APP, ["get", "regions"], output=True)
        if returncode != 0 or stdout is None:
            raise TestCaseError(
                "Unable to get pia regions, return result {}!".format(stdout)
            )
        country_entries = [entry for entry in stdout.split("\n")]
        if not country_entries:
            raise TestCaseError("Error in parsing country list!")
        return country_entries

    def country_to_code(self, country: str) -> str:
        if "-" in country and len(country.split("-", 1)[0]) == 2:
            return country.split("-", 1)[0]
        know_country_list = self.CONFIG["plugin"]["provider"][self.get_name()][
            "country"
        ]
        for entry in know_country_list:
            if know_country_list[entry][0] == country:
                return str(entry)
        return None

    async def get_cities(self, country: str) -> set:
        async with ContainerEnvironment(_NAME) as env:
            try:
                await self.login(env)
            except:
                log.info("Failed to login!")
                return None
            app_countries = await self.get_countries(env)
            cities = set()
            for app_country in app_countries:
                country_code = self.country_to_code(app_country)
                if cc_to_iso(country_code) == cc_to_iso(country):
                    city = str(app_country).replace(str(country_code) + "-", "")
                    city = city.replace("-", " ")
                    city = str(city).title()
                    city = str(city).replace("Dc", "DC")
                    cities.add(city)
            if cities is not None and len(cities) != 0:
                log.debug("City list: {}".format(cities))
                return cities
            return None

    async def set_region(self, env: ContainerEnvironment, group: TestGroup):
        set_country = None
        city_not_found = False
        vpn_city = None
        app_countries = await self.get_countries(env)
        if group.vpn_city:
            vpn_city = str(group.vpn_city).lower().replace(" ", "-")
        log.debug("Available countries:\n {}".format(app_countries))
        for app_country in app_countries:
            if vpn_city:
                if str(app_country).lower().find(vpn_city) == -1:
                    city_not_found = True
                    continue
                else:
                    set_country = app_country
                    city_not_found = False
                    break
            country_code = self.country_to_code(app_country)
            if country_code is None:
                continue
            if cc_to_iso(country_code) == cc_to_iso(group.vpn_country):
                log.info("Country: {}".format(app_country))
                set_country = app_country
                break
        if city_not_found:
            raise TestCaseError(
                "Failed to set city {}, not provided in app country list".format(
                    group.vpn_city
                )
            )
        log.debug("Region to set: {}".format(set_country))
        if set_country is not None:
            returncode, stdout = await self._env.exec(
                _APP, ["set", "region", set_country]
            )
            if returncode != 0:
                raise TestCaseError(
                    "Unable to set pia region {}, set result {}.".format(
                        set_country, stdout
                    )
                )
        else:
            raise TestCaseError("Unable to set region to {}!".format(group.vpn_country))
        returncode, stdout = await self._env.exec(_APP, ["get", "region"], output=True)
        if returncode != 0 or stdout is None:
            raise TestCaseError(
                "Unable to get pia country, return result {}.".format(stdout)
            )
        log.info("pia country is set to {}".format(stdout.strip("\n")))
        if set_country is None or set_country not in stdout:
            raise TestCaseError(
                "Failed to set pia country to {}, found country {}, return app result {}.".format(
                    group.vpn_country, set_country, stdout
                )
            )

    async def login(self, env: ContainerEnvironment):
        self._env = env
        await self._env.write_file(
            "login_creds", "{}\n{}".format(self._creds.username, self._creds.password)
        )
        returncode, stdout = await self._env.exec(_APP, ["login", "login_creds"])
        ok = True if returncode == 0 else False
        if not ok:
            log.info("Failed to login...")
            log.info("Trying to logout...")
            await self._env.exec(_APP, "logout")
            returncode, stdout = await self._env.exec(_APP, ["login", "login_creds"])
            if returncode != 0:
                raise VPNConnectionFailed("Failed to login pia: {}".format(stdout))
        log.info("Login successfull: {}, return code: {}".format(ok, returncode))

    async def connect(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ):
        self._env = env
        if case.technology != "openvpn" and case.technology != "wireguard":
            raise TechnologyNotSupported(
                "Pia does not support {} tech.".format(case.technology)
            )
        await env.exec(_APP, ["set", "protocol", case.technology])
        retcode, stdout = await self._env.exec(_APP, ["get", "protocol"], output=True)
        if retcode != 0 or stdout is None or case.technology not in stdout:
            raise ProtocolNotSupported(
                "Unable to configure {}, current {} technology pia.".format(
                    case.technology, stdout.strip("\n")
                )
            )

        log.info("Running {} technology ".format(case.technology))
        if group.vpn_country is None:
            raise TestRunError("VPN target country is not set!")
        if group.vpn_country != "auto":
            await self.set_region(env, group)

        retcode, stdout = await self._env.exec(_APP, "connect")
        if retcode != 0:
            raise VPNConnectionFailed("Failed to connect to Pia Servers")
        log.debug("Finished connections..")

    async def disconnect(self):
        await self._env.exec(_APP, "disconnect")
