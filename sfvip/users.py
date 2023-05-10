import json
import os
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Self

from sfvip_all_config import Player as ConfigPlayer

from .config import Loader
from .exceptions import SfvipError
from .regkey import RegKey


class Users:
    """handle the users' database to add and remove the proxy setting"""

    _encoding = "utf-8"
    _playlist_ext = ".m3u", ".m3u8"
    _regkey = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _config_dir = str((Path(os.getenv("APPDATA")) / "SFVIP-Player").resolve())

    def __init__(self, config_loader: Loader, config_player: type[ConfigPlayer]) -> None:
        config_dir = config_player.config_dir
        if not self._dir_exists(config_dir):
            config_dir = RegKey.value_by_name(*Users._regkey)
            config_dir = config_dir if config_dir else Users._config_dir
            if self._dir_exists(config_dir) and config_dir != config_player.config_dir:
                config_player.config_dir = config_dir
                config_loader.save()

        if not self._dir_exists(config_dir):
            raise SfvipError("No config dir found")
        self._database = Path(config_dir) / "Database.json"
        if not self._database.is_file():
            raise SfvipError("No users database found")
        self._accessed_time = None

    @staticmethod
    def _dir_exists(path: str) -> bool:
        if path:
            path: Path = Path(path)
            return path.is_dir()
        return False

    @staticmethod
    def _is_playlist(user: dict) -> bool:
        path = Path(user["Address"])
        return path.suffix in Users._playlist_ext or path.is_file()

    def _set_proxy(self, proxy_url: str) -> None:
        with self._database.open("r", encoding=Users._encoding) as f:
            users = json.load(f)
        if users := [user for user in users if not self._is_playlist(user)]:
            for user in users:
                user["HttpProxy"] = proxy_url
            with self._database.open("w", encoding=Users._encoding) as f:
                json.dump(users, f, indent=2, separators=(",", ":"))

    def restore_proxy(self, timeout: int = 5) -> None:
        if self._accessed_time:

            def wait(condition: Callable[[], bool]) -> Callable[[], bool]:
                def loop() -> bool:
                    while time.time() - self._accessed_time <= timeout:
                        if condition():
                            return True
                        time.sleep(0.1)
                    return False

                return loop

            def database_accessed() -> bool:
                return os.path.getatime(self._database) >= self._accessed_time

            def database_closed() -> bool:
                try:
                    os.rename(self._database, self._database)
                    return True
                except OSError:
                    return False

            # wait for the database to be accessed once and closed
            if wait(database_accessed)():
                if wait(database_closed)():
                    self._set_proxy("")

    @contextmanager
    def set_proxy(self, port: int) -> Self:
        self._set_proxy(f"http://127.0.0.1:{port}")
        self._accessed_time = os.path.getatime(self._database) + 0.001
        yield self
        self.restore_proxy()  # better safe than sorry
