import sys
import asyncio
import json
import time
import socket
import aiohttp
from socket import gaierror
from asyncio.subprocess import Process, PIPE
from vpnspeed import log
from typing import List, Tuple
from .constans import DEFAULT_SUBPROCESS_TIMEOUT


TERMINATE_TIMEOUT = 2
GEO_IP_CHECKER = "https://ipapi.co/{}/json/"


async def system_exec(cmd, *args, env=None) -> bool:
    """
    Execute subprocess asynchronously and terminate.

    Returns True if proccess compleated successfully, False otherwise
    """
    proc: Process = await asyncio.create_subprocess_exec(
        cmd,
        *args,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
    )

    async def drain(tag: str, rx: asyncio.StreamReader):
        while not rx.at_eof():
            line = await rx.readline()
            log.debug("%s[%s]: %s", cmd, tag, line.decode().strip("\n "))

    try:
        await asyncio.wait_for(
            asyncio.gather(
                drain("stdout", proc.stdout),
                drain("stderr", proc.stderr),
            ),
            DEFAULT_SUBPROCESS_TIMEOUT,
        )

    except asyncio.CancelledError:
        pass
    except asyncio.TimeoutError:
        pass
    finally:
        try:
            proc.terminate()
            await asyncio.sleep(TERMINATE_TIMEOUT)
            proc.kill()
        except ProcessLookupError:
            pass

    log.debug("{} exit({})".format(cmd, proc.returncode))
    return proc.returncode == 0


def clean_dict(dict_: dict) -> dict:
    return {
        key: value for key, value in dict_.items() if value is not None and value != ""
    }


def cc_to_iso(country: str):
    """Map internal country code to iso country code."""
    if country is None:
        return None
    return country.upper().replace("UK", "GB")


def iso_to_cc(country: str):
    """Map iso country code to internal country code"""
    if country is None:
        return None
    return country.lower().replace("uk", "gb")


def try_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return None
    return json_object


async def measure_hosts_connection_time_task(hosts: list, port: int, id):
    host_connection_time = 0
    id = (id % len(hosts)) if id >= len(hosts) else id
    try:
        ip_list = socket.gethostbyname_ex(hosts[id])[2]
    except gaierror:
        return None
    for ip in ip_list or []:
        time_start = time.time()
        try:
            with socket.socket() as sock:
                sock.connect((ip, port))
        except socket.error:
            continue
        end_time = time.time() - time_start
        host_connection_time = (
            end_time
            if end_time < host_connection_time or host_connection_time == 0
            else host_connection_time
        )
    if host_connection_time == 0:
        return None
    return (hosts[id], round(host_connection_time, 10))


async def nearest_host_from_list(hosts: list, port: int, retry: int = 5):
    hist = dict()
    taskCount = retry * len(hosts)
    multiple_tasks = [
        measure_hosts_connection_time_task(hosts, port, task_id)
        for task_id in range(taskCount)
    ]
    for task_future in asyncio.as_completed(multiple_tasks):
        ret_tuple = await task_future
        if ret_tuple is None:
            continue
        (host, time) = ret_tuple
        if host not in hist:
            hist[host] = 0
        hist[host] += time
    if hist:
        log.info("Hosts with connection time: {}".format(hist))
        return min(hist, key=hist.get)
    return None


def trim_new_line(value: str) -> str:
    return value[:-1] if value.endswith("\n") else value


async def ip_to_coordinates(ip: str) -> Tuple[str, str]:
    ip_geocache_checker = GEO_IP_CHECKER.format(ip)
    log.debug("Checking geo locationa by {}".format(ip_geocache_checker))
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(ip_geocache_checker) as response:
                if response.status == 200:
                    req_json = try_json(await response.text())
                    if req_json is None:
                        return (None, None)
                    longtitude = req_json["longitude"]
                    latitude = req_json["latitude"]
                    if longtitude and latitude:
                        return (longtitude, latitude)
                return (None, None)
        except:
            return (None, None)
