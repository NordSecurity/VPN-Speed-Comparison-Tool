import asyncio
from typing import List
from aiodocker.docker import Docker, DockerContainer
from aiodocker.exceptions import DockerError
import aiohttp
import string
import time
from vpnspeed import log, resources
from vpnspeed.container import ContainerUtils
from vpnspeed.utils import try_json
from vpnspeed.errors import *
import yaml


class ContainerEnvironment:
    _CONFIG = yaml.safe_load(resources.resource_stream("static.yaml"))
    _dockerContainer: ContainerUtils
    _vpn: str
    _technology: str
    _error_message: str = None

    def get_error_message(self) -> str:
        return self._error_message

    def __init__(self, vpn: str, technology: str = "none"):
        self._dockerContainer = ContainerUtils()
        self._vpn = vpn
        self._technology = technology

    async def exec(
        self,
        cmd: str,
        args=None,
        output: bool = False,
        timeout: int = 600,
        resp_json: bool = False,
        allow_error: bool = False,
        user: str = "root",
    ) -> list:
        stdout = None
        cmd_list = [cmd]
        if args is not None:
            if type(args) is list:
                cmd_list = cmd_list + args
            else:
                cmd_list.append(args)
        log.debug("Starting cmd: {}".format(cmd_list))
        ret_code, stdout = await self._dockerContainer.exec(
            cmd_list, output, timeout, allow_error, user
        )
        if ret_code != 0:
            return [-1, stdout]
        if output and stdout is None:
            return [-1, None]
        if resp_json:
            for result in stdout:
                json = try_json(result)
                if json is not None:
                    return [0, json]
            return [-2, stdout]
        stdout = "".join(stdout) if type(stdout) is list else stdout
        return [0, stdout]

    async def read_file(self, name: str) -> str:
        retcode, stdout = await self.exec("cat", "{}".format(name), output=True)
        await asyncio.sleep(0)
        return stdout

    async def write_file(self, name: str, data: str):
        await self.exec("write_to_file", [data, name])
        await asyncio.sleep(0)

    async def delete_file(self, name: str):
        await self.exec("rm", "{}".format(name))
        await asyncio.sleep(0)

    async def sub_exec(self, cmd: str, args=None) -> int:
        if (args is not None) and (type(args) is not list):
            args = args.split()
        args = list(args or [])
        return await self.exec("run_sub_proc", ["{}".format(cmd)] + args, output=True)

    async def read_proc_stdout(self, procId: int) -> str:
        retcode, stdout = await self.exec(
            "cat", "/proc/{}/fd/1".format(procId), output=True
        )
        if retcode != 0 or stdout is None:
            ret2, stderr = await self.exec("cat", "/var/log/nohup.out", output=True)
            return [-1, stderr]
        return [retcode, stdout]

    async def kill_proc(self, procId: int) -> int:
        returncode, stdout = await self.exec("kill", str(procId))
        return returncode

    def get_image(self, vpn: str, technology: str) -> str:
        imageDictionary = self._CONFIG["plugin"]["images"]
        if vpn in imageDictionary:
            return "vpnspeed/{}".format(imageDictionary[vpn])
        if technology in imageDictionary:
            return "vpnspeed/{}".format(imageDictionary[technology])
        return None

    async def __aenter__(self):
        await self._dockerContainer.add_mount("/dev/net/tun", "/dev/net/tun")
        image_name = self.get_image(self._vpn, self._technology)
        if image_name is None:
            return None
        container_name = "{}_{}".format(self._vpn, self._technology.replace("/", "-"))
        container_cmd = "/entrypoint.sh"
        log.info("Container cmd: {}".format(container_cmd))
        await self._dockerContainer.create(image_name, container_name, container_cmd)
        self._error_message = self._dockerContainer.get_error_message()
        if self._error_message is not None:
            raise VPNSpeedError("Unable to create env '{}'".format(self._error_message))
        await self._dockerContainer.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._dockerContainer.delete()
