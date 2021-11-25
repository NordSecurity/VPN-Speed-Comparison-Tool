import yaml
from typing import List
from vpnspeed.errors import *
from vpnspeed.model import VPN
from vpnspeed.service.model import Context
from vpnspeed.tester.interfaces import Tester
from vpnspeed import resources
from vpnspeed.vpn.dynamic import PROVIDERS

_SUPPORTED = {
    provider: {tech.name: tech.protocols or [] for tech in builder.get_technologies()}
    for provider, builder in PROVIDERS.items()
}


def _fields_present(values: List[str], fields: List[str], should_exist: bool = True):
    for field in fields:
        if field not in values and should_exist:
            raise VPNSpeedError("Field '{}' not present in the config".format(field))
        elif field in values and not should_exist:
            raise VPNSpeedError(
                "Unavailable field '{}' used in the config".format(field)
            )


def _valid_field_type(field, value, value_type):
    if not isinstance(value, value_type):
        raise VPNSpeedError(
            "Value type '{}' for field '{}' is invalid. Field type should be '{}'".format(
                type(value), field, value_type
            )
        )


def validate_format(config: dict):
    _fields_present(config.keys(), ["config"])
    _fields_present(config["config"].keys(), ["groups", "vpns", "sinks"])
    _fields_present(config.keys(), ["machine", "groups"], False)

    _valid_field_type("interval", config["config"]["interval"], int)
    _valid_field_type("common_cities", config["config"]["common_cities"], bool)


def validate_values(context: Context):
    if not context.config or not context.config.vpns:
        return

    for vpn in context.config.vpns:
        if vpn.name not in _SUPPORTED:
            raise ProviderNotSupported(
                "The VPN provider '{}' is not supported. Available providers are: [{}]".format(
                    vpn.name, ", ".join(_SUPPORTED.keys())
                )
            )
        for tech in vpn.technologies:
            if tech.name not in _SUPPORTED[vpn.name]:
                raise TechnologyNotSupported(
                    "Technology '{}' for provider '{}' is not supported. Available technologies are: [{}]".format(
                        tech.name, vpn.name, ", ".join(_SUPPORTED[vpn.name].keys())
                    )
                )
            if not tech.protocols:
                continue
            for proto in tech.protocols:
                if proto not in _SUPPORTED[vpn.name][tech.name]:
                    raise ProtocolNotSupported(
                        "Protocol '{}' for technology '{}' in provider '{}' is not supported. Available protocols are: [{}]".format(
                            proto,
                            tech.name,
                            vpn.name,
                            ", ".join(_SUPPORTED[vpn.name][tech.name]),
                        )
                    )
