"""
This file models vpnspeed testing data

Contfig - Per machine configuration + User configurable test parameters
    `- VPN - UserConfigurable VPNProvider (vpn), Technologies and Protocols to be compared
    `- TestSetup - User configurable test grouping parameters
        `- TestGroup - At service runtime generated test grouping [machine x vpn_country x target_country x target_server]
            `- TestCase - At service runtime generated test leaf, comparable in same TestGroup [machine x vpn_country x target_country x target_server x vpn x technology x proto]
                `- TestRun - Multiple runs of same TestCase

For upload to remote DB, this data would be normalized to TestRun with all parent information...

"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Set, Dict, Union
from datetime import datetime


# Config Data


class Mode(Enum):
    continuous = "continuous"
    once = "once"


@dataclass(frozen=True)
class VPNCredentials:
    username: str = None
    password: str = None


@dataclass
class VPNTechnology:
    name: str
    protocols: List[str] = None


@dataclass
class VPN:
    name: str
    credentials: VPNCredentials = None
    technologies: List[VPNTechnology] = None


@dataclass
class DataSink:
    name: str
    url: str
    type: str = None
    params: dict = None
    as_backup: bool = False


@dataclass(frozen=True)
class TestGroup:
    vpn_country: str = None
    target_country: str = None
    vpn_city: str = None
    target_server: str = None
    target_server_id: str = None


@dataclass
class Config:
    interval: int = None
    mode: Mode = None
    repeats: int = None
    common_cities: bool = False
    vpns: List[VPN] = None
    groups: Set[TestGroup] = None
    sinks: List[DataSink] = None


# Runtime Data
@dataclass(frozen=True)
class Probe:
    ip: str
    country: str
    country_code: str
    city: str
    provider: str = None
    start_time: datetime = None

    def __str__(self):
        return "Location({}, {}, {}, {})".format(
            self.country_code, self.country, self.city, self.ip
        )


@dataclass(frozen=True)
class TestCase:
    vpn: str = None
    technology: str = None
    protocol: str = None


@dataclass(frozen=True)
class TestRun:
    timestamp: datetime
    ping_latency: float
    ping_jitter: float
    download_bandwidth: int
    download_bytes: int
    download_elapsed: int
    upload_bandwidth: int
    upload_bytes: int
    upload_elapsed: int
    isp: str
    server_ip: str
    server_country: str
    server_country_code: str
    server_location: str
    interface_name: str = None
    interface_internal_ip: str = None
    interface_external_ip: str = None
    server_id: str = None
    server_name: str = None
    server_host: str = None
    packet_loss: int = None
