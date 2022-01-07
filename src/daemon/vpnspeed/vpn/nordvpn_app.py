import asyncio
from enum import auto
import re
import yaml
from typing import Set, List
from asyncio.subprocess import Process, PIPE
from .dynamic import dynamic
from .interfaces import VPNProvider
from vpnspeed import resources, log
from vpnspeed.model import *
from vpnspeed.errors import *
from vpnspeed.container import ContainerEnvironment

from vpnspeed.utils import cc_to_iso, iso_to_cc


_NAME = "nordvpn-app"
_APP = "/usr/bin/nordvpn"


@dynamic
class NordvpnApp(VPNProvider):
    CONFIG = yaml.safe_load(resources.resource_stream("static.yaml"))
    _cities = {}

    def __init__(self, creds: VPNCredentials):
        self._creds = creds

    @staticmethod
    def get_name() -> str:
        return _NAME

    @classmethod
    def get_technologies(cls):
        return [
            VPNTechnology("openvpn", ["udp", "tcp"]),
            VPNTechnology("nordlynx"),
        ]

    # Mitigate error when app does not remove dns protection.
    async def clean_resolv_conf(self):
        log.debug("Cleaning immutable flag from /etc/resolv.conf")
        await self._env.exec("/usr/bin/chattr", ["-i", "/etc/resolv.conf"])

    async def check_vpn_running(self, env: ContainerEnvironment):
        returncode, stdout = await env.exec("/entrypoint.sh", allow_error=True)
        if returncode != 0:
            await self.clean_resolv_conf()
            raise VPNConnectionFailed("Failed to start Nordvpn: {}".format(stdout))

    async def get_countries(self, env: ContainerEnvironment):
        await self.check_vpn_running(env)
        returncode, stdout = await env.exec(_APP, ["countries"], output=True)
        if returncode != 0 or stdout is None:
            raise TestCaseError(
                "Unable to get Nordvpn countries, return result {}!".format(stdout)
            )
        country_entries = [entry for entry in stdout.split(", ")]
        if not country_entries:
            raise TestCaseError("Error in parsing country list!")
        log.info("Got countries {}".format(country_entries))
        return country_entries

    def country_to_code(self, country: str) -> str:
        know_country_list = self.CONFIG["plugin"]["provider"][self.get_name()][
            "country"
        ]
        for entry in know_country_list:
            if know_country_list[entry][0] == country:
                return str(entry)
        return None

    async def get_cities(self, country: str) -> set:
        async with ContainerEnvironment(_NAME) as env:
            await self.check_vpn_running(env)
            app_countries = await self.get_countries(env)
            cities = set()
            for app_country in app_countries:
                app_country = app_country.replace("\r", "").replace("-", "").strip()
                country_code = self.country_to_code(app_country)
                if cc_to_iso(country_code) == cc_to_iso(country):
                    returncode, stdout = await env.exec(
                        _APP, ["cities", str(app_country)], output=True
                    )
                    if returncode != 0 or stdout is None:
                        raise TestCaseError(
                            "Unable to get Nordvpn cities for country {}, return result {}!".format(
                                app_country, stdout
                            )
                        )
                    cities_entry = [entry for entry in stdout.split(", ")]
                    if cities_entry:
                        for city in cities_entry:
                            cities.add(city.replace("\r", "").replace("-", "").strip())
                        self._cities[app_country] = cities
            if cities is not None and len(cities) != 0:
                log.debug("City list: {}".format(cities))
                return cities
            return None

    async def get_target(self, env: ContainerEnvironment, group: TestGroup) -> str:
        target = None
        city_not_found = False
        vpn_city = None
        app_countries = await self.get_countries(env)
        if group.vpn_city:
            vpn_city = str(group.vpn_city).lower().replace(" ", "_")
        for app_country in app_countries:
            app_country = app_country.replace("\r", "").replace("-", "").strip()
            if vpn_city:
                target_city = "None"
                if app_country in self._cities:
                    log.debug(
                        "Checking country: {}, with city: {} for city: {}".format(
                            app_country, self._cities[app_country], vpn_city
                        )
                    )
                    target_city = [
                        city
                        for city in self._cities[app_country]
                        if city.lower() == vpn_city
                    ]
                    if target_city:
                        # log.info("geiting index: {}".format(target_city))
                        target_city = str(target_city[0]).lower()
                    # log.info("Target city: {}".format(target_city))
                if vpn_city != target_city:
                    city_not_found = True
                    continue
                else:
                    target = target_city
                    city_not_found = False
                    break
            country_code = self.country_to_code(app_country)
            if country_code is None:
                continue
            if cc_to_iso(country_code) == cc_to_iso(group.vpn_country):
                log.info("Country: {}".format(app_country))
                target = app_country
                break
        if city_not_found:
            raise TestCaseError(
                "Failed to set city {}, not provided in app country list".format(
                    group.vpn_city
                )
            )
        log.debug("Target to set: {}".format(target))
        if target is not None:
            return target
        else:
            raise TestCaseError("Unable to set target to {}!".format(group.vpn_country))

    async def login(self, env: ContainerEnvironment):
        self._env = env
        await self.check_vpn_running(env)
        returncode, stdout = await self._env.exec("/entrypoint.sh", allow_error=True)
        if returncode != 0:
            raise VPNConnectionFailed("Failed to start Nordvpn: {}".format(stdout))
        returncode, stdout = await self._env.exec(
            "/usr/bin/nordvpn-login",
            [self._creds.username, self._creds.password],
            output=True,
        )
        log.debug("Return code: {}, stdout: {}".format(returncode, stdout))
        if returncode != 0:
            raise VPNConnectionFailed("Failed to login Nordvpn: {}".format(stdout))
        log.info("Login successfull!")

    async def connect(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ):
        self._env = env
        if case.technology != "openvpn" and case.technology != "nordlynx":
            raise TechnologyNotSupported(
                "Nordvpn does not support {} tech.".format(case.technology)
            )
        await env.exec(_APP, ["set", "technology", case.technology])
        if case.technology == "openvpn":
            await env.exec(_APP, ["set", "protocol", case.protocol])

        log.info("Running {} technology ".format(case.technology))
        if group.vpn_country is None:
            raise TestRunError("VPN target country is not set!")
        if group.vpn_country != "auto":
            target = await self.get_target(env, group)
            retcode, stdout = await self._env.exec("/usr/bin/nordvpn-connect", target)
            if retcode != 0:
                log.debug("Got error: {}".format(stdout))
                raise VPNConnectionFailed("Failed to connect to Nordvpn Servers")
        else:
            retcode, stdout = await self._env.exec("/usr/bin/nordvpn-connect")
            if retcode != 0:
                log.debug("Got error: {}".format(stdout))
                raise VPNConnectionFailed("Failed to connect to Nordvpn Servers")
        log.debug("Finished connection..")

    async def disconnect(self):
        await self._env.exec(_APP, "disconnect")
        await self._env.exec(_APP, "logout")
        await self.clean_resolv_conf()
