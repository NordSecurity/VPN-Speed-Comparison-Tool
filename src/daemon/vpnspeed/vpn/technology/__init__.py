from .interfaces import VPNTechnology
from .openvpn import OpenVPN
from .ipsec import IPSec
from .wireguard import WireGuard


TECHNOLOGIES = {
    tech.get_name(): tech
    for tech in [
        OpenVPN,
        IPSec,
        WireGuard,
    ]
}
