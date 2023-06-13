import yaml
import json
import asyncio

from datetime import datetime
from vpnspeed import resources, log
from pycountry import countries

from vpnspeed.utils import cc_to_iso, iso_to_cc, try_json
from vpnspeed.errors import *
from vpnspeed.model import *
from vpnspeed.constans import DEFAULT_SUBPROCESS_TIMEOUT
from vpnspeed.probe import make_env_probe
from .interfaces import Tester
from vpnspeed.container import ContainerEnvironment


class SpeedTestCliTester(Tester):
    async def validateTestServer(
        self, env: ContainerEnvironment, server: str, port: str
    ) -> bool:
        log.debug("Request: http://{}:{}/hi".format(server, port))
        status, res = await env.exec(
            "curl",
            ["-s", "--fail", "http://{}:{}/hi".format(server, port)],
            output=True,
            timeout=10,
        )
        if status != 0:
            log.debug(
                "Request failed with status: {} and message: {}".format(status, res)
            )
            return False
        log.debug("Request succesfull")
        return True

    async def resolve(self, env: ContainerEnvironment, cgroup: TestGroup) -> TestGroup:
        log.debug("Speedtest-cli fetching server list...")
        args = ["--accept-license", "--accept-gdpr", "-L", "-f", "json"]
        returncode, stdout = await env.exec(
            "/usr/bin/speedtest", args, output=True, resp_json=True
        )
        if stdout is None:
            raise TestRunError("Speedtest cli timeout.")

        if returncode != 0:
            raise TestRunError("Exited with: {}\n".format(returncode))

        log.debug("Speedtest-cli server list fetched.")
        servers = stdout
        if servers is None:
            raise TesterServersNotFound()

        target = None
        target_country = cgroup.target_country and countries.get(
            alpha_2=cc_to_iso(cgroup.target_country)
        )
        probe_city = (await make_env_probe(env)).city
        target_city = probe_city if probe_city != "Unknown" else cgroup.vpn_city
        for server in servers["servers"]:
            if target_country is not None and server["country"] == target_country.name:
                validServer = await self.validateTestServer(
                    env, server["host"], server["port"]
                )
                if not validServer:
                    log.info(
                        "Country: {}, server: {}:{} is not valid!".format(
                            server["country"], server["host"], server["port"]
                        )
                    )
                    continue
                if target_city is None or target_city in server["location"]:
                    target = server
                    break
                if target is None:
                    target = server

        if target is None:
            log_target = cgroup.target_country
            if target_city is not None:
                log_target = "country: {}, city {}".format(
                    cgroup.target_country, target_city
                )
            log.debug("Server list: {}".format(servers["servers"]))
            raise TesterServersNotFound(
                "No servers found for {} in the server list".format(log_target)
            )

        return TestGroup(
            vpn_country=cgroup.vpn_country,
            target_country=cgroup.target_country,
            target_server=target["host"],
            target_server_id=target["id"],
        )

    async def test(
        self, env: ContainerEnvironment, group: TestGroup, case: TestCase
    ) -> TestRun:
        log.debug(
            "Testing: {} {} {} => {} {} {}".format(
                group.vpn_country,
                group.target_country,
                group.target_server,
                case.vpn,
                case.technology,
                case.protocol,
            )
        )

        if group.target_country != "auto":
            group = await self.resolve(env, group)

        args = [
            "--accept-license",
            "--accept-gdpr",
            "-f",
            "json",
        ]
        if group.target_server:
            args.extend(["-s", str(group.target_server_id)])

        log.debug("Running speedtest-cli... %s", repr(args))
        log.info("Starting sppedtest-cli...")
        returncode, json_stdout = await env.exec(
            "/usr/bin/speedtest", args, output=True, resp_json=True, allow_error=True
        )
        if json_stdout is None:
            raise TestCaseError("Speedtest-cli subprocess timeout.")

        if returncode != 0:
            raise TestCaseError("Exited with: {}\n".format(returncode))

        if "error" in json_stdout:
            raise TestCaseError(
                "Speedtest-cli result was an error: {}".format(json_stdout["error"])
            )

        log.info("speedtest-cli completed.")
        speedtest_result = json_stdout
        try:
            country = countries.get(name=speedtest_result["server"]["country"])
            result = TestRun(
                timestamp=datetime.fromisoformat(speedtest_result["timestamp"][:-1]),
                ping_latency=speedtest_result["ping"]["latency"],
                ping_jitter=speedtest_result["ping"]["jitter"],
                download_bandwidth=speedtest_result["download"]["bandwidth"],
                download_bytes=speedtest_result["download"]["bytes"],
                download_elapsed=speedtest_result["download"]["elapsed"],
                upload_bandwidth=speedtest_result["upload"]["bandwidth"],
                upload_bytes=speedtest_result["upload"]["bytes"],
                upload_elapsed=speedtest_result["upload"]["elapsed"],
                isp=speedtest_result["isp"],
                interface_name=speedtest_result["interface"]["name"],
                interface_internal_ip=speedtest_result["interface"]["internalIp"],
                interface_external_ip=speedtest_result["interface"]["externalIp"],
                server_id=speedtest_result["server"]["id"],
                server_name=speedtest_result["server"]["name"],
                server_host=speedtest_result["server"]["host"],
                server_ip=speedtest_result["server"]["ip"],
                server_location=speedtest_result["server"]["location"],
                server_country=speedtest_result["server"]["country"],
                server_country_code=country and iso_to_cc(country.alpha_2),
                packet_loss=speedtest_result.get("packetLoss"),
            )
        except KeyError as e:
            raise TestCaseError("Incomplete speedtestcli data: " + str(e))

        log.debug("Test passed:\n\t{}".format(result))
        return result
