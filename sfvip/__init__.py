import http.client
import json
import re
import subprocess
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Optional
from urllib.request import urlopen

import proxy
from proxy.http.methods import httpMethods
from proxy.http.parser import HttpParser
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.responses import okResponse

from .config import CONFIG
from .tools import RegKey
from .ui import UI


# need CONFIG @ declaration time since a local HttpProxyBasePlugin class can't be pickled @ runtime by multiprocessing
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

    def __init__(self, config: type[CONFIG]) -> None:
        buf_size = str(config.Proxy.buf_size_in_MB * 1024**2)

        # fmt: off
        proxy_opts = (
            "--timeout", str(config.Proxy.timeout),
            "--log-level", config.Proxy.log_level,
            "--client-recvbuf-size", buf_size,
            "--server-recvbuf-size", buf_size,
            "--max-sendbuf-size", buf_size,
            "--num-acceptors", "1",  # prevent shutdown lock
        )  # fmt: on
        super().__init__(proxy_opts, port=0, plugins=[Plugin])


class Users:
    """handle the users' database to add and remove the proxy setting"""

    _playlist_ext = ".m3u", ".m3u8"
    _database = "Database.json"

    def __init__(self, config: type[CONFIG]) -> None:
        self._database = Path(config.config_dir) / Users._database

    @staticmethod
    def _is_playlist(user: dict) -> bool:
        path = Path(user["Address"])
        return path.suffix in Users._playlist_ext or path.exists()

    def _open(self, mode: str) -> IO:
        return self._database.open(mode=mode, encoding="utf-8")

    def _set_proxy(self, proxy_url: str) -> None:
        if self._database.exists():
            with self._open("r") as f:
                users = json.load(f)
            if users := [user for user in users if not self._is_playlist(user)]:
                for user in users:
                    user["HttpProxy"] = proxy_url
                with self._open("w") as f:
                    json.dump(users, f, indent=2, separators=(",", ":"))

    @contextmanager
    def set_proxy(self, port: int) -> None:
        self._set_proxy(f"http://127.0.0.1:{port}")
        yield
        self._set_proxy("")


class Player:
    """find and check sfvip player"""

    name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey = winreg.HKEY_CLASSES_ROOT, r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache", name

    def __init__(self, config: type[CONFIG]) -> None:
        self.player = config.player
        if not self.valid():
            self.player = self._get_from_regkey()
            if not self.valid():
                self.player = self._get_from_user(config)
            if self.valid() and self.player != config.player:
                config.player = self.player
                config.save()

    @staticmethod
    def _get_from_regkey() -> Optional[str]:
        if name := RegKey.name_by_value(*Player._regkey):
            return ".".join(name.split(".")[:-1])
        return None

    @staticmethod
    def _get_from_user(config: type[CONFIG]) -> Optional[str]:
        ui = UI(config.title)
        ui.showinfo(f"PLease find {Player.name}")
        while True:
            if player := ui.find_file(Player.name, Player._pattern):
                return player
            if not ui.askretry(message=f"{Player.name} not found, try again ?"):
                return None

    def valid(self) -> bool:
        if self.player:
            player: Path = Path(self.player)
            return player.exists() and player.is_file() and player.match(Player._pattern)
        return False

    def open(self) -> subprocess.Popen:
        return subprocess.Popen([self.player])


def run():
    sfvip_player = Player(CONFIG)
    if sfvip_player.valid():
        with Proxy(CONFIG) as sfvip_proxy:
            with Users(CONFIG).set_proxy(sfvip_proxy.flags.port):
                with sfvip_player.open():
                    pass
