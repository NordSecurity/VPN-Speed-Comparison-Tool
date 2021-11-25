import random
import io
import json
import urllib.request
import jinja2 as jinja
import yaml
from typing import Dict

from vpnspeed import resources, log
from vpnspeed.errors import *
from vpnspeed.model import *
from .interfaces import VPNProvider
from .technology import VPNTechnology as Tech, TECHNOLOGIES
from vpnspeed.container import ContainerEnvironment

import dns.resolver as dnsresolver

_TECH_MAP = {
    "openvpn": VPNTechnology("openvpn", ["udp", "tcp"]),
    "openvpn_udp": VPNTechnology("openvpn", ["udp"]),
    "ipsec/ikev2": VPNTechnology("ipsec/ikev2"),
    "wireguard": VPNTechnology("wireguard"),
}


class Templated(VPNProvider):
    CONFIG = yaml.safe_load(resources.resource_stream("static.yaml"))

    _creds: VPNCredentials
    __tech: Dict[str, Tech]
    __current_tech: Tech
    __default_dns: str = "1.1.1.1"

    @classmethod
    def get_technologies(cls):
        return [
            _TECH_MAP[name]
            for name in cls.CONFIG["plugin"]["provider"][cls.get_name()]["supports"]
        ]

    def __init__(self, creds: VPNCredentials):
        self.method = "recommended"
        self.__current_tech = None
        self.__tech = dict()
        for tech in self.get_technologies():
            self.__tech[tech.name] = TECHNOLOGIES[tech.name]()
        self.__countries = self.CONFIG["plugin"]["provider"][self.get_name()]["country"]
        self._creds = creds

    async def login(self, env: ContainerEnvironment, creds: VPNCredentials = None):
        if creds is not None:
            log.info("Updating creds...")
            self._creds = creds

    async def connect(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ):
        try:
            if hasattr(self, "__current_tech") and self.__current_tech is not None:
                await self.__current_tech.stop()
                self.__current_tech = None
        except Exception as e:
            log.exception("Failed to stop previous run - ignoring. Error:\n%s", e)

        log.debug("Connecting... %s", self.get_name())
        if case.technology not in self.__tech:
            raise TechnologyNotSupported()

        try:
            self.__current_tech = self.__tech[case.technology]
            server = await self._get_recommended_server(group)
            config = self._generate_config(
                **vars(self._creds),
                tech=case.technology,
                proto=case.protocol or "udp",
                server=server,
            )
            log.debug("%s config:\n%s", case.technology, config)
        except Exception as e:
            log.exception("Failed provider API query:\n%s", e)
            raise ProviderAPIQueryFailed("Failed provider API query: {}.".format(e))

        await self.__current_tech.start(env, config, vars(self._creds))

    async def disconnect(self):
        if self.__current_tech is None:
            return
        await self.__current_tech.stop()
        self.__current_tech = None

    async def get_cities(self, country: str) -> set:
        return None

    async def _get_recommended_server(self, group: TestGroup) -> str:
        country = (
            group.target_country if group.vpn_country == "auto" else group.vpn_country
        )
        if country not in self.__countries:
            raise ProviderServerNotFound(
                "Cannot find server for country selection: {}.".format(
                    group.vpn_country
                )
            )

        return random.choice(self.__countries[country])

    def _generate_config(self, **kwargs) -> str:
        content = resources.resource_string(
            "templates/" + kwargs["tech"] + "/" + self.get_name() + ".j2"
        ).decode("utf8")
        template = jinja.Template(content)
        return template.render(kwargs)

    async def _verify_dns(self, env: ContainerEnvironment, dns):
        try:
            ret_code, stdout = await env.exec(
                "getent", ["hosts", "nordvpn.com"], output=True
            )
            if ret_code != 0 or stdout is None:
                raise Exception("Failed to resolve dns!")
            return dns
        except Exception as e:
            log.exception("DNS resolve failed: {}".format(e))
            return self.__default_dns
