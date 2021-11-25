import argparse
import asyncio
import logging
from os import makedirs, path

from vpnspeed.api import ApiServer
from vpnspeed.service import Service, Context
from vpnspeed.datasink import DynamicDataSink
from vpnspeed.tester import SpeedTestCliTester
from logging.handlers import RotatingFileHandler


def _init_logger(args):
    makedirs(path.dirname(args.log_path), exist_ok=True)
    sizeLevelBytes = 1024 * 1024 * 50
    handler = RotatingFileHandler(args.log_path, maxBytes=sizeLevelBytes, backupCount=5)
    logging.basicConfig(
        level=logging._nameToLevel.get(args.log_level.upper()),
        format="%(asctime)s %(name)s %(levelname)s:%(message)s",
        handlers=[handler],
    )


async def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="Communication path", default=None)
    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "notset"],
    )
    parser.add_argument("-f", "--log-path", default="/var/log/vpnspeed/vpnspeed.log")
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--tlscacert", default="/etc/vpnspeed/certs/ca.pem")
    parser.add_argument("--tlscert", default="/etc/vpnspeed/certs/server-cert.pem")
    parser.add_argument("--tlskey", default="/etc/vpnspeed/certs/server-key.pem")

    server = ApiServer(Service(SpeedTestCliTester()))

    args = parser.parse_args()
    _init_logger(args)
    await server.listen(args.path, args=args)


def run():
    asyncio.run(_main())


if __name__ == "__main__":
    run()
