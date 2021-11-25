import asyncio
import aiohttp
import json
import jsonpickle
import socket
import os
import traceback
import datetime
import ssl

from aiohttp import web
from datetime import date, timedelta
from typing import List, Tuple, Union

from vpnspeed import log, errors
from vpnspeed.datasink.csv import dict_to_csv
from vpnspeed.errors import VPNSpeedError
from vpnspeed.model import Probe, TestGroup, TestCase, TestRun
from vpnspeed.reporting import ReportFilter
from vpnspeed.utils import system_exec
from vpnspeed.service import Service, Context

from . import codex
from .jsonpath import filter as jp_filter


DEFAULT_REPORT_PATH = "/var/run/vpnspeed"
DEFAULT_ACCESS_GROUP = "vpnspeed"
DEFAULT_PATH = "/var/run/vpnspeed/vpnspeed.sock"


class ApiServer:
    _app: web.Application = None
    _service: Service = None
    _ssl_context: ssl.SSLContext = None

    def __init__(self, service: Service):
        self._service = service

    async def listen(self, path: str = None, args=None, **kwargs):
        await self._service.start()

        self._app = web.Application()
        self._app.router.add_get("/context", self._get_context)
        self._app.router.add_post("/context", self._set_context)
        self._app.router.add_post(
            "/context_config_update", self._set_context_update_config
        )
        self._app.router.add_get("/data", self._get_data)
        self._app.router.add_post("/report", self._make_report)

        if args and args.tls:
            self._ssl_context = ssl.create_default_context(
                ssl.Purpose.CLIENT_AUTH, cafile=args.tlscacert
            )
            self._ssl_context.verify_mode = ssl.CERT_REQUIRED
            self._ssl_context.load_cert_chain(args.tlscert, args.tlskey)

        path = path or DEFAULT_PATH
        try:
            host = path.split(":")
            port = 80
            if len(host) > 1:
                port = host[1]
            host = host[0]
            socket.inet_aton(host[0])
            # path is valid ip address, try to establish tcp socket
            server = await asyncio.get_event_loop().create_server(
                self._app.make_handler(), host, port, ssl=self._ssl_context
            )
        except socket.error:
            # try to establish unix socket
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # asyncio.create_task(self._ensure_group_access(DEFAULT_ACCESS_GROUP, path))
            server = await asyncio.get_event_loop().create_unix_server(
                self._app.make_handler(), path, ssl=self._ssl_context
            )

        await server.serve_forever()

    async def _get_context(self, request: web.Request) -> web.Response:
        jsonpath_str = request.query.get("jsonpath", "$")
        context = codex.encode(await self._service.get_context())

        try:
            result = jp_filter(context, jsonpath_str)
        except Exception as e:
            return web.json_response(
                {
                    "type": "Bad Request",
                    "message": "Invalid jsonpath '{}'. {}.".format(
                        jsonpath_str, str(e)
                    ),
                },
                status=400,
            )

        return web.json_response(result)

    async def _set_context(self, request: web.Request) -> web.Response:
        context_json = await request.json()
        try:
            await self._service.update(codex.decode(context_json))
        except Exception as e:
            return web.json_response(
                {
                    "type": str(type(e)),
                    "message": str(e),
                    "trace": traceback.format_exc(),
                },
                status=400 if isinstance(e, VPNSpeedError) else 500,
            )
        return web.Response()

    async def _set_context_update_config(self, request: web.Request) -> web.Response:
        context_json = await request.json()
        try:
            await self._service.update(codex.decode(context_json), True)
        except Exception as e:
            return web.json_response(
                {
                    "type": str(type(e)),
                    "message": str(e),
                    "trace": traceback.format_exc(),
                },
                status=400 if isinstance(e, VPNSpeedError) else 500,
            )
        return web.Response()

    async def _get_data(self, request: web.Request) -> web.Response:
        data = await self._service.get_data()

        f = "csv"
        if "format" in request.query:
            f = request.query["format"]
        if f == "csv":
            return web.Response(
                body=dict_to_csv(data), headers={"Content-Type": "text/csv"}
            )
        elif f == "json":
            return web.json_response(data)
        else:
            return web.json_response(
                {
                    "type": "Bad Request",
                    "message": f"Invalid format query '{f}', valid values: csv, json",
                }
            )

    async def _make_report(self, request: web.Request) -> web.Response:
        path = None
        filter_ = ReportFilter.default()
        query = request.query
        try:
            if "start" in query:
                filter_.start = date.fromisoformat(query["start"])
                if "end" not in query:
                    filter_.end = filter_.start + timedelta(days=7)

            if "end" in query:
                filter_.end = date.fromisoformat(query["end"])
                if "start" not in query:
                    filter_.start = filter_.end - timedelta(days=7)

            if "outliers" in query:
                filter_.outliers = float(query["outliers"])

            if "value" in query:
                filter_.value = query["value"]

            filter_.validate()
            path = await self._service.make_report(DEFAULT_REPORT_PATH, filter_)

            def _clean(_):
                try:
                    os.remove(path)
                except OSError:
                    pass

            request.task.add_done_callback(_clean)
            return web.FileResponse(
                path,
                headers={
                    "Content-Disposition": 'attachmen; filename="{}"'.format(
                        os.path.basename(path)
                    )
                },
            )

        except errors.APIError as e:
            return web.json_response(
                {
                    "type": "Bad Api Usage",
                    "message": str(e),
                },
                status=400,
            )

        except Exception as e:
            return web.json_response(
                {
                    "type": str(type(e)),
                    "message": "Failed to generate report. {}".format(e),
                    "trace": traceback.format_exc(),
                },
                status=400,
            )

    async def _ensure_group_access(self, group, path):
        await system_exec("groupadd", group)
        backoff = 0.25
        while not os.path.exists(path):
            await asyncio.sleep(backoff)
            backoff = max(backoff * 2, 64)
        await system_exec("setfacl", "-m", "g:{}:rwx".format(group), path)
