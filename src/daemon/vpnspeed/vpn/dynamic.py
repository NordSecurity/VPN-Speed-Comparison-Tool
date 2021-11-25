import asyncio
import io
from typing import List, Dict

from vpnspeed import log, errors
from vpnspeed.model import TestGroup, TestCase, VPN as VPNConfig
from .interfaces import VPNProvider

from vpnspeed.container import ContainerEnvironment

PROVIDERS = {}


def dynamic(cls):
    assert issubclass(cls, VPNProvider), f"{cls} is not subclass of {VPNProvider}"
    PROVIDERS[cls.get_name()] = cls
    return cls


class VPNSession:
    _resolv: str
    _creds: str
    _provider: VPNProvider
    _group: TestGroup
    _case: TestCase

    def __init__(self, env, provider: VPNProvider, group: TestGroup, case: TestCase):
        self._provider = provider
        self._group = group
        self._case = case
        self._env = env

    async def __aenter__(self):
        # Save DNS setting before VPN
        try:
            await self._provider.login(self._env)
        except:
            log.info("Failed to login!")
            raise errors.TechnologyAuthFailed(
                "Failed to login in {} provider!".format(self._provider.get_name())
            )
        try:
            await self._provider.connect(self._env, self._group, self._case)
        except errors.TechnologyNotSupported as eTech:
            if log.getEffectiveLevel() != 20:
                log.exception("Failed provider connect:\n%s", eTech)
            raise errors.ProviderAPIQueryFailed(
                "Technology not supported by this provider"
            )
        except Exception as e:
            raise errors.ProviderAPIQueryFailed(
                "Failed provider connect: {}.".format(e)
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Restore DNS setting after VPN

        log.debug("Session end for: %s", self._provider.get_name())
        try:
            await self._provider.disconnect()
        except Exception as e:
            log.exception("Failed provider disconnect:\n%s", e)


class DynamicVPN:
    _providers: Dict[str, VPNProvider]

    def __init__(self):
        self._providers = dict()

    async def add_providers(self, vpns: List[VPNConfig]):
        for vpn in vpns:
            self._providers[vpn.name] = PROVIDERS[vpn.name](vpn.credentials)

    async def get_cities(self, country: str) -> set:
        cities = set()
        log.info("Get cities for country: {}".format(country))
        log.info("Providers count: {}".format(len(self._providers)))
        for provider in self._providers.values():
            provider_cities = await provider.get_cities(country)
            if not cities:
                cities = provider_cities
            elif not provider_cities:
                continue
            else:
                cities = cities.intersection(provider_cities)
        log.info("Found cities: {}".format(cities))
        return cities

    async def update_providers(self, vpns: List[VPNConfig]):
        await self.add_providers(vpns)

    async def remove_providers(self, vpns: List[VPNConfig]):
        for vpn in vpns:
            del self._providers[vpn.name]

    async def get_providerlist(self):
        return self._providers

    def session(self, env, group: TestGroup, case: TestCase) -> VPNSession:
        return VPNSession(env, self._providers[case.vpn], group, case)
