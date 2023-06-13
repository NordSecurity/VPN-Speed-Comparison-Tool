import asyncio
from aiodocker.docker import Docker, DockerContainer
from aiodocker.exceptions import DockerError
import aiohttp
import string
import time
from vpnspeed import log


class ContainerUtils:
    _docker: Docker
    _mount_list: list
    _container: DockerContainer
    _container_ws: aiohttp.ClientWebSocketResponse
    _error_message: str = None

    def __init__(self):
        self._docker = Docker()
        self._mount_list = []

    def get_error_message(self) -> str:
        return self._error_message

    async def pull_docker_image(self, image: str) -> bool:
        try:
            await self._docker.pull(image)
            return True
        except DockerError:
            return False

    async def image_exist(self, image: str) -> str:
        try:
            await self._docker.images.inspect(image)
            return None
        except DockerError as e:
            if e.status == 404:
                if await self.pull_docker_image(image):
                    return None
            return "Error retrieving {} image.".format(image)

    async def add_mount(self, source: str, target: str):
        mountConfig = {
            "Type": "bind",
            "Source": source,
            "Target": target,
            "Mode": "",
            "RW": True,
            "Propagation": "rprivate",
        }
        self._mount_list.append(mountConfig)

    async def create(
        self,
        image: str = "debian:10",
        container_name: str = "default",
        container_cmd: str = "/bin/bash",
    ):
        self._container = await self.make_container(
            image, container_name, container_cmd
        )
        return self

    async def make_container(
        self, image: str, container_name: str, container_cmd: str
    ) -> DockerContainer:
        status = await self.image_exist(image)
        if status is not None:
            self._error_message = status
            return None
        config = {
            "Cmd": container_cmd,
            "Image": image,
            "AttachStdin": True,
            "AttachStdout": True,
            "AttachStderr": True,
            "Tty": False,
            "OpenStdin": True,
            "StdinOnce": True,
            "Privileged": True,
            "Sysctls": {"net.ipv6.conf.all.disable_ipv6": "0"},
            "Mounts": self._mount_list,
        }
        return await self._docker.containers.create_or_replace(
            config=config, name=container_name
        )

    async def connect(self):
        self._container_ws = await self._container.websocket(
            stdin=True, stdout=True, stderr=True, stream=True
        )
        await self._container.start()
        await asyncio.sleep(0)
        # print("Connection started...")

    async def raw_exec(self, cmd: str, user: str = "root", allow_error: bool = False):
        log.debug("exec cmd:\n {}".format(cmd))
        message_list = list()
        try:
            execute_cmd = await self._container.exec(
                cmd,
                stderr=True,
                stdout=True,
                stdin=False,
                tty=False,
                privileged=True,
                user=user,
            )
        except RuntimeError as e:
            if e.message == "RuntimeError: Session is closed":
                return -1
        result_stream = execute_cmd.start()
        message = await result_stream.read_out()
        while message is not None:
            log.debug("exec message: {}".format(message))
            if "OCI runtime exec failed" in message.data.decode():
                return -1
            if message.stream == 2 and allow_error is False:
                return -1
            message_list.append(message)
            message = await result_stream.read_out()
        return message_list

    async def exec(
        self,
        cmd: str,
        output: bool = False,
        timeout=600,
        allow_error: bool = False,
        user: str = "root",
    ):
        return_list = list()
        try:
            message_list = await asyncio.wait_for(
                self.raw_exec(cmd, user, allow_error), timeout
            )
            if message_list == -1:
                return [-1, None]
            if output:
                if not message_list:
                    return [-1, None]
                for message in message_list:
                    return_list.append(message.data.decode())
                return [0, return_list]
            else:
                return [0, None]
        except asyncio.TimeoutError:
            return [-1, "timeout"]

    async def disconnect(self):
        await self._container_ws.close()
        # print("Connection closed.")

    async def delete(self):
        if self._container is not None:
            await self._container.delete(force=True)
        if self._docker is not None:
            await self._docker.close()
