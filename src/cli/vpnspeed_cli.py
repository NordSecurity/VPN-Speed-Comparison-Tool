import aiohttp
import asyncio
import aiofiles
import argparse
import cgi
import yaml
import json
import jsonpickle
import ssl
import os
import sys
from crontab import CronTab, CronSlices
from datetime import date
from io import open
from pathlib import Path
from typing import List


DEFAULT_PATH = "/var/run/vpnspeed/vpnspeed.sock"


class ApiClient:
    _client: aiohttp.ClientSession = None
    _base: str = None
    _ssl_context: ssl.SSLContext = None

    async def connect(self, path: str = None, args=None, **kwargs):
        path = path or DEFAULT_PATH
        self._base = "http://"

        if args and args.tls:
            self._ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH, cafile=args.tlscacert
            )
            self._base = "https://"

        if os.path.exists(path):
            conn = aiohttp.UnixConnector(path=path)
            self._base += "vpnspeed.sock"
        else:
            conn = aiohttp.TCPConnector(ssl=self._ssl_context)
            self._base += path

        self._client = aiohttp.ClientSession(connector=conn)

    async def get_context(self, jsonpath=None) -> dict:
        query = {}
        if jsonpath:
            query["jsonpath"] = jsonpath

        async with self._client.get(self._base + "/context", params=query) as res:
            await self._check_for_error(res)
            return await res.json()

    async def set_context(self, context: dict, update_contex_config: bool = False):
        target: str = "/context"
        if update_contex_config:
            target = "/context_config_update"
        async with self._client.post(
            self._base + target,
            json=context,
        ) as res:
            await self._check_for_error(res)

    async def get_data(self, format_: str = None) -> str:
        query = {}
        if format_:
            query["format"] = format_

        async with self._client.get(self._base + "/data", params=query) as res:
            await self._check_for_error(res)
            return await res.text()

    async def make_report(
        self,
        path=".",
        value: str = None,
        outliers: float = None,
        start: date = None,
        end: date = None,
    ):
        query = {}
        if value:
            query["value"] = value
        if outliers:
            query["outliers"] = outliers
        if start:
            query["start"] = start.isoformat()
        if end:
            query["end"] = end.isoformat()

        # If report making is executed in container set default path to: /opt/vpnspeed/report
        if os.path.isfile("/.dockerenv"):
            path = "/opt/vpnspeed/report"

        async with self._client.post(
            self._base + "/report",
            params=query,
        ) as res:
            await self._check_for_error(res)

            _, params = cgi.parse_header(res.headers["Content-Disposition"])
            with open(os.path.join(path, params["filename"]), "wb") as f:
                f.write(await res.read())

    async def _check_for_error(self, res: aiohttp.ClientResponse, expect_status=200):
        if res.status != expect_status:
            error = await res.json()
            message = "Request failed"
            message += "\nStatus: " + str(res.status)
            report = await res.json()
            message += "\nType: " + report["type"]
            message += "\nMessage: " + report["message"]
            if "trace" in report:
                message += "\n" + report["trace"]

            raise Exception(message)

    async def disconnet(self):
        if not self._client.closed:
            await self._client.close()


def _load_context(file):
    with open(file) as f:
        return yaml.safe_load(f.read())


async def up_command(client: ApiClient, args):
    context = _load_context(args.CONFIG_FILE)
    context["state"] = "run"
    await client.set_context(context, args.update)


async def down_command(client: ApiClient, args):
    context = {"state": "idle"}
    await client.set_context(context)

    cron = CronTab(user="root")
    cron.remove_all(command="vpnspeed up " + (args.CONFIG_FILE or ""))
    cron.write()


async def stop_command(client: ApiClient, args):
    context = {"state": "quit"}
    await client.set_context(context)


async def log_command(client: ApiClient, args):
    try:
        async with aiofiles.open("/var/log/vpnspeed/vpnspeed.log", mode="r") as logFile:
            print(await logFile.read())
    except OSError:
        print("Failed to read vpnspeed log file.")


async def context_command(client: ApiClient, args):
    print(
        jsonpickle.dumps(
            await client.get_context(jsonpath=args.jsonpath), unpicklable=False
        )
    )


async def data_command(client: ApiClient, args):
    print(await client.get_data(format_=args.format))


async def schedule_command(client: ApiClient, args):
    if not Path(args.CONFIG_FILE).is_absolute():
        raise Exception("An absolute path to the config file is required")

    context = _load_context(args.CONFIG_FILE)
    if context["config"]["mode"] != "once":
        raise Exception("The test run mode must be set to `once` for scheduled tests")

    os.system("cron")
    cron = CronTab(user="root")
    job = cron.new(command="/usr/local/bin/vpnspeed up " + args.CONFIG_FILE)

    if args.cron:
        if not CronSlices.is_valid(args.cron):
            raise ValueError("The cron string is invalid")
        job.setall(args.cron)
    else:
        job.every(args.interval).hours()
    cron.write()


async def report_command(client: ApiClient, args):
    await client.make_report(
        args.report_path, args.value, args.outliers, args.start, args.end
    )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="communication path")
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--tlscacert", default="/etc/vpnspeed/certs/ca.pem")
    subparser = parser.add_subparsers(dest="command")

    up_parser = subparser.add_parser("up")
    up_parser.set_defaults(func=up_command)
    up_parser.add_argument(
        "CONFIG_FILE",
        help="path to the configuration file",
        nargs="?",
        default="vpnspeed.yaml",
    )
    up_parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="to update, not replace configuration file.",
    )

    down_parser = subparser.add_parser("down")
    down_parser.set_defaults(func=down_command)
    down_parser.add_argument(
        "CONFIG_FILE", help="path to the configuration file", nargs="?"
    )

    stop_parser = subparser.add_parser("stop")
    stop_parser.set_defaults(func=stop_command)

    context_parser = subparser.add_parser("context")
    context_parser.add_argument("jsonpath", nargs="?", default=None)
    context_parser.set_defaults(func=context_command)

    data_parser = subparser.add_parser("data")
    data_parser.add_argument("-f", "--format", default="csv", choices=["csv", "json"])
    data_parser.set_defaults(func=data_command)

    schedule_parser = subparser.add_parser("schedule")
    schedule_parser.set_defaults(func=schedule_command)
    schedule_parser.add_argument(
        "CONFIG_FILE",
        help="absolute path to the configuration file",
        nargs="?",
        default="/opt/vpnspeed/vpnspeed.yaml",
    )
    times = schedule_parser.add_mutually_exclusive_group(required=True)
    times.add_argument(
        "-i", "--interval", help="test execution interval in hours", type=int
    )
    times.add_argument(
        "-c",
        "--cron",
        help="cron string describing the schedule of the tests",
        type=str,
    )

    report_parser = subparser.add_parser("report")
    report_parser.set_defaults(func=report_command)
    report_parser.add_argument("report_path", nargs="?", default=".")
    report_parser.add_argument("-v", "--value", default=None)
    report_parser.add_argument("-o", "--outliers", type=float, default=None)
    report_parser.add_argument("-s", "--start", type=date.fromisoformat, default=None)
    report_parser.add_argument("-e", "--end", type=date.fromisoformat, default=None)

    logs_parser = subparser.add_parser("logs")
    logs_parser.set_defaults(func=log_command)

    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        client = ApiClient()
        await client.connect(args.path, args=args)
        await args.func(client, args)
    except Exception as e:
        print(e)
        sys.exit(1)
    finally:
        await client.disconnet()


def run():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
