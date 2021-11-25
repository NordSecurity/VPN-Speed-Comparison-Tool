import asyncio
import aiohttp
import http
import hashlib
import base64
import json
from datetime import datetime

from vpnspeed.model import Probe
from vpnspeed.utils import iso_to_cc
from vpnspeed.container import ContainerEnvironment
from vpnspeed import resources, log, errors

IP_CHECKER = "https://ipapi.co/json/"
COUNTRY_KEY = "country_name"


async def make_probe() -> Probe:
    async with aiohttp.ClientSession() as session:
        for i in range(5):
            try:
                async with session.get(IP_CHECKER) as res:
                    res.raise_for_status()
                    res = await res.json()
                    return Probe(
                        ip=res["ip"],
                        country=res[COUNTRY_KEY],
                        country_code=iso_to_cc(res["country_code"]),
                        city=res["city"],
                        start_time=datetime.now(),
                        provider=IP_CHECKER,
                    )
            except Exception as e:
                log.warning("Failed to fetch probe info:\n%s", e)
            finally:
                await asyncio.sleep(2 ** i)

        raise errors.TestRunError("Failed to get probe info")


async def make_env_probe(env: ContainerEnvironment) -> Probe:
    for i in range(5):
        status, res = await env.exec(
            "curl", ["-s", IP_CHECKER], output=True, timeout=(3 ** i), resp_json=True
        )
        log.info("Probe result: {}".format(res))
        if status == 0 and res:
            if (
                "ip" in res
                and COUNTRY_KEY in res
                and "country_code" in res
                and "city" in res
            ):
                return Probe(
                    ip=res["ip"],
                    country=res[COUNTRY_KEY],
                    country_code=iso_to_cc(res["country_code"]),
                    city=res["city"],
                    start_time=datetime.now(),
                    provider=IP_CHECKER,
                )
        log.warning(
            "Failed to fetch env probe info: {}, result: {}".format(status, res)
        )
        await asyncio.sleep(2 ** i)

    raise errors.TestRunError("Failed to get env probe info")
