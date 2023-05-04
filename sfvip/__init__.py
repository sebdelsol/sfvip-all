import http.client
import json
import os
import re
import subprocess
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Callable, Iterator, Optional
from urllib.request import urlopen

import proxy
from proxy.http.methods import httpMethods
from proxy.http.parser import HttpParser
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.responses import okResponse

import build_config as BUILD_CONFIG
import sfvip_all_config as CONFIG

from .loader import ConfigLoader
from .regkey import RegKey
from .ui import UI

CONFIG_DIR = RegKey.value_by_name(winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir")
CONFIG_DIR = Path(CONFIG_DIR) if CONFIG_DIR else Path(os.getenv("APPDATA")) / "SFVIP-Player"
CONFIG_LOADER = ConfigLoader(CONFIG, CONFIG_DIR / "Sfvip All.json")
CONFIG_LOADER.update_from_json()


# can't use a local class declared @runtime : it can't be pickled by multiprocessing
class Plugin(HttpProxyBasePlugin):
    """proxy.py plugin that injects the all category"""

    _api_query = b"player_api.php?"
    _query_attr = {httpMethods.POST: "body", httpMethods.GET: "path"}
    _all_category_query = f"&category_id={CONFIG.AllCat.id}".encode()
    _all_category_json = dict(category_id=str(CONFIG.AllCat.id), category_name=CONFIG.AllCat.name, parent_id=0)
    _is_categories_query = re.compile(f"get_({'|'.join(CONFIG.AllCat.inject)})_categories".encode()).search

    def handle_client_request(self, request: HttpParser) -> Optional[HttpParser]:
        if request.path and Plugin._api_query in request.path:
            query_attr = Plugin._query_attr[request.method]
            query: bytes = getattr(request, query_attr)
            if Plugin._all_category_query in query:
                # turn an all category query into a whole catalog query
                setattr(request, query_attr, query.replace(Plugin._all_category_query, b""))
            elif Plugin._is_categories_query(query):
                # send a response with the all category injected
                # pylint: disable=protected-access
                with urlopen(str(request._url), request.body, timeout=CONFIG.Proxy.timeout) as resp:
                    resp: http.client.HTTPResponse
                    if resp.status == 200:
                        resp_json = [Plugin._all_category_json] + json.loads(resp.read())
                        self.client.queue(
                            okResponse(
                                headers={b"Content-Type": b"application/json"},
                                content=json.dumps(resp_json).encode(),
                            )
                        )
        return request


class Proxy(proxy.Proxy):
    """multiprocess proxy, automatically find an available port"""

    _buf_size = str(CONFIG.Proxy.buf_size_in_MB * 1024**2)
    # fmt: off
    _proxy_opts = (
        "--timeout", str(CONFIG.Proxy.timeout),
        "--log-level", CONFIG.Proxy.log_level,
        "--client-recvbuf-size", _buf_size,
        "--server-recvbuf-size", _buf_size,
        "--max-sendbuf-size", _buf_size,
        "--num-acceptors", "1",  # prevent shutdown lock
    )  # fmt: on

    def __init__(self) -> None:
        super().__init__(Proxy._proxy_opts, port=0, plugins=[Plugin])


class Users:
    """handle the users' database to add and remove the proxy setting"""

    _playlist_ext = ".m3u", ".m3u8"
    _database = Path(CONFIG_DIR) / "Database.json"

    @staticmethod
    def _is_playlist(user: dict) -> bool:
        path = Path(user["Address"])
        return path.suffix in Users._playlist_ext or path.exists()

    @staticmethod
    def _open(mode: str) -> IO:
        return Users._database.open(mode=mode, encoding="utf-8")

    def _set_proxy(self, proxy_url: str) -> None:
        if Users._database.exists():
            with self._open("r") as f:
                users = json.load(f)
            if users := [user for user in users if not self._is_playlist(user)]:
                for user in users:
                    user["HttpProxy"] = proxy_url
                with self._open("w") as f:
                    json.dump(users, f, indent=2, separators=(",", ":"))

    @contextmanager
    def set_proxy(self, port: int) -> Iterator[Callable[[], None]]:
        self._set_proxy(f"http://127.0.0.1:{port}")
        accessed_time = os.path.getatime(Users._database) + 0.001
        timeout = 5

        def wait(condition: Callable[[], bool]) -> Callable[[], bool]:
            def loop() -> bool:
                while time.time() - accessed_time <= timeout:
                    if condition():
                        return True
                    time.sleep(0.1)
                return False

            return loop

        def database_accessed() -> bool:
            return os.path.getatime(Users._database) >= accessed_time

        def database_closed() -> bool:
            try:
                os.rename(Users._database, Users._database)
                return True
            except OSError:
                return False

        def restore_proxy() -> None:
            if wait(database_accessed)():
                if wait(database_closed)():
                    self._set_proxy("")

        yield restore_proxy
        self._set_proxy("")  # better safe than sorry


class Player:
    """find and check sfvip player"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey = winreg.HKEY_CLASSES_ROOT, r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache"

    def __init__(self) -> None:
        self.player_path = CONFIG.Player.path
        if not self.valid():
            self.player_path = self._get_from_regkey()
            if not self.valid():
                self.player_path = self._get_from_user()
            if self.valid() and self.player_path != CONFIG.Player.path:
                CONFIG.Player.path = self.player_path
                CONFIG_LOADER.save()

    @staticmethod
    def _get_from_regkey() -> Optional[str]:
        if name := RegKey.name_by_value(*Player._regkey, Player._name):
            return ".".join(name.split(".")[:-1])
        return None

    @staticmethod
    def _get_from_user() -> Optional[str]:
        ui = UI(f"{BUILD_CONFIG.name} v{BUILD_CONFIG.version}")
        ui.showinfo(f"Please find {Player._name}")
        while True:
            if player := ui.find_file(Player._name, Player._pattern):
                return player
            if not ui.askretry(message=f"{Player._name} not found, try again ?"):
                return None

    def valid(self) -> bool:
        if self.player_path:
            player: Path = Path(self.player_path)
            return player.exists() and player.is_file() and player.match(Player._pattern)
        return False

    def open(self) -> subprocess.Popen:
        return subprocess.Popen([self.player_path])


def run():
    sfvip_player = Player()
    if sfvip_player.valid():
        with Proxy() as sfvip_proxy:
            with Users().set_proxy(sfvip_proxy.flags.port) as restore_proxy:
                with sfvip_player.open():
                    restore_proxy()
