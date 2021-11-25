import asyncio
import logging
import os
import aiohttp
import json
import urllib

from vpnspeed.errors import *
from vpnspeed.model import *

from .dynamic import dynamic
from .templated import Templated

from vpnspeed.utils import trim_new_line
from vpnspeed import resources, log
from datetime import datetime, timedelta
import uuid
import glob


_NAME = "surfshark"
_SURFSHARK_WG_PRIVATE_KEY_DIR = "/var/run/vpnspeed/"


@dynamic
class SurfShark(Templated):

    __username: str = None
    __password: str = None
    __token: str
    __renew_token: str
    __private_key: str = None
    __public_key: str = None
    __server_public_key: str = None
    __wg_private_key_file: str = None

    @staticmethod
    def get_name() -> str:
        return _NAME

    def _get_headers(self, token):
        return {"Authorization": "Bearer " + token}

    async def login(self, env):
        if self.__username is None and self.__password is None:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        self.CONFIG["plugin"]["provider"][self.get_name()]["api_login"],
                        json={
                            "username": self._creds.username,
                            "password": self._creds.password,
                        },
                    ) as res:
                        if res.status != 200:
                            raise VPNBadCredentials(
                                "Unable to login to Surfshark VPN:\n{} - {}".format(
                                    res.status, res.reason
                                )
                            )
                        data = await res.text()
                        data_json = json.loads(data)
                        self.__token = data_json["token"]
                        self.__renew_token = data_json["renewToken"]
                    async with session.get(
                        self.CONFIG["plugin"]["provider"][self.get_name()][
                            "api_credentials"
                        ],
                        headers=self._get_headers(self.__token),
                    ) as res:
                        if res.status != 200:
                            raise VPNBadCredentials(
                                "Failed to fetch Surfshark VPN credentials:\n{} - {}".format(
                                    res.status, res.reason
                                )
                            )
                        data = await res.text()
                        data_json = json.loads(data)
                        log.debug("Surfshark API login OK.")
                        self.__username = data_json["serviceCredentials"]["username"]
                        self.__password = data_json["serviceCredentials"]["password"]
                except:
                    raise TestRunError("Connection Error!")
            return await super().login(
                env,
                VPNCredentials(
                    username=self.__username,
                    password=self.__password,
                ),
            )

    async def _renew_token(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.CONFIG["plugin"]["provider"][self.get_name()][
                        "api_auth_renew"
                    ],
                    headers=self._get_headers(self.__renew_token),
                ) as res:
                    if res.status != 200:
                        raise VPNBadCredentials(
                            "Unable to auth renew of Surfshark VPN:\n{} - {}".format(
                                res.status, res.reason
                            )
                        )
                    data = await res.text()
                    data_json = json.loads(data)
                    self.__token = data_json["token"]
                    log.debug("Surfshark API auth renew OK.")
            except:
                raise TestRunError("Connection Error!")

    async def connect(self, env, group: TestGroup, case: TestCase):

        await self._renew_token()

        url = self.CONFIG["plugin"]["provider"][self.get_name()][
            "api_servers_recommended"
        ]
        if group.vpn_country is None:
            raise TestRunError("VPN target country is not set!")

        if group.vpn_country != "auto":
            log.debug("Target country is {}".format(group.vpn_country))
            url += "/" + group.vpn_country

        async with aiohttp.ClientSession() as session:
            try:
                if case.technology == "wireguard":
                    await self._get_wg_config(
                        env,
                        session,
                        self.CONFIG["plugin"]["provider"][self.get_name()][
                            "api_wg_public_key"
                        ],
                    )
                async with session.get(
                    url, headers=self._get_headers(self.__token)
                ) as res:
                    if res.status != 200:
                        raise TestRunError(
                            "Failed to get recommended servers for Surfshark VPN, Response({}):\n{}".format(
                                res.status, await res.text()
                            )
                        )
                    data = await res.text()
                    self.__recommended = json.loads(data)
            except:
                raise TestRunError("Connection Error!")

        return await super().connect(env, group, case)

    async def _generate_wg_private_key(self, env):
        retcode, private_key = await env.exec("wg", "genkey", output=True)
        if (retcode != 0) or private_key is None:
            raise ProviderAPIQueryFailed("Failed to generate private key!")
        return trim_new_line(private_key)

    async def _generate_wg_public_key(self, env, private_key):
        retcode, public_key = await env.exec("gen_wg_pub_key", private_key, output=True)
        if (retcode != 0) or public_key is None:
            raise ProviderAPIQueryFailed("Failed to generate public key!")
        return trim_new_line(public_key)

    async def _activate_wg_public_key(self, session, api_url, public_key):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.__token,
        }
        payload = {"pubKey": "{}".format(public_key)}
        async with session.post(api_url, headers=headers, json=payload) as resp:
            if resp.status != 201:
                log.debug(
                    "URL req error! rc:{} / {}".format(resp.status, await resp.text())
                )
                raise TestRunError(
                    "Failed to get Wireguard server public key for Surfshark VPN, Response({}):\n{}".format(
                        resp.status, await resp.text()
                    )
                )
            respJson = await resp.json()
            log.info("Activated: {}".format(respJson))
            return str(respJson["expiresAt"])[:10]

    def _load_wg_key_data(self):
        log.debug("Trying to load surshark wg key data...")
        wg_private_key = wg_pub_expires = wg_user = None
        if self.__wg_private_key_file is not None and os.path.exists(
            self.__wg_private_key_file
        ):
            with open(self.__wg_private_key_file) as wg_key_config:
                wg_private_key = trim_new_line(wg_key_config.readline())
                wg_pub_expires = trim_new_line(wg_key_config.readline())
                wg_user = trim_new_line(wg_key_config.readline())
            return (wg_private_key, wg_pub_expires, wg_user)
        log.debug("Success loading wg key!")
        return (None, None, None)

    def _save_wg_key_data(self, private_key, expires_at, username):
        log.debug("Trying to save wg key")
        # Remove old key
        for old_key_data in os.listdir(_SURFSHARK_WG_PRIVATE_KEY_DIR):
            if old_key_data.startswith(_NAME):
                os.remove(os.path.join(_SURFSHARK_WG_PRIVATE_KEY_DIR, old_key_data))
        log.debug("Deleted old key")
        # Generate new
        rand_key_filename = _NAME + "_" + str(uuid.uuid4().hex)
        new_key_data = os.path.join(_SURFSHARK_WG_PRIVATE_KEY_DIR, rand_key_filename)
        with open(new_key_data, "w") as wg_key_config:
            wg_key_config.write(private_key + "\n")
            wg_key_config.write(expires_at + "\n")
            wg_key_config.write(username)
            self.__wg_private_key_file = new_key_data
            log.debug("Success creating wg key!")

    async def _generate_wg_keys(self, env):
        self.__private_key = await self._generate_wg_private_key(env)
        self.__public_key = await self._generate_wg_public_key(env, self.__private_key)

    async def _get_wg_config(self, env, session, api_url):
        wg_private_key = wg_pub_expires = wg_user = None
        wg_pub_expired: bool = False
        await self._renew_token()
        wg_private_key, wg_pub_expires, wg_user = self._load_wg_key_data()
        if (
            wg_pub_expires == ""
            or wg_user != self.__username
            or datetime.strptime(wg_pub_expires.strip(), "%Y-%m-%d").date()
            <= datetime.utcnow().date()
        ):
            wg_pub_expired = True
        if wg_private_key and wg_pub_expired is False:
            log.info("Found public and private wg keys")
            self.__private_key = wg_private_key
            self.__public_key = self._generate_wg_public_key(env, self.__private_key)
        else:
            log.info("Private wg key not found or expired. Generating new...")
            await self._generate_wg_keys(env)
            expires_at = await self._activate_wg_public_key(
                session, api_url, self.__public_key
            )
            self._save_wg_key_data(self.__private_key, expires_at, self.__username)

    async def _get_recommended_server(self, group: TestGroup) -> str:
        self.__server_public_key = self.__recommended[0]["pubKey"]
        return self.__recommended[0]["connectionName"]

    def _generate_config(self, **kwargs) -> str:
        return super()._generate_config(
            private_key=self.__private_key,
            public_key=self.__server_public_key,
            **kwargs,
        )
