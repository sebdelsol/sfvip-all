import json
import os
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Optional

from sfvip_all_config import Player as ConfigPlayer

from .config import Loader
from .exceptions import SfvipError
from .regkey import RegKey

FuncNoRet = Callable[..., None]
Exceptions = type[Exception] | tuple[type[Exception]]


class NotAccessedYet(Exception):
    pass


def _retry_if_exception(exceptions: Exceptions, timeout: int) -> Callable[[FuncNoRet], FuncNoRet]:
    def decorator_retry(func) -> FuncNoRet:
        def wrapper_retry(*args, **kwargs) -> None:
            start = time.perf_counter()
            while time.perf_counter() - start <= timeout:
                try:
                    func(*args, **kwargs)
                    break
                except exceptions:
                    time.sleep(0.1)

        return wrapper_retry

    return decorator_retry


def _dir_exists(path: str) -> bool:
    if path:
        path: Path = Path(path)
        return path.is_dir()
    return False


class User(SimpleNamespace):
    """a sfvip user"""

    _playlist_ext = ".m3u", ".m3u8"

    def __init__(self, **kwargs: str) -> None:
        # pylint: disable=invalid-name
        self.Name: str
        self.Address: str
        self.HttpProxy: str
        super().__init__(**kwargs)

    def is_playlist(self) -> bool:
        path = Path(self.Address)
        return path.suffix in User._playlist_ext or path.is_file()


class Users(list[User]):
    """list of Users with json load & dump"""

    class _Encoder(json.JSONEncoder):
        # pylint: disable=arguments-renamed
        def default(self, user: User) -> dict:
            return user.__dict__

    def load(self, f: IO) -> None:
        self.clear()
        self.extend(json.load(f, object_hook=lambda user_dict: User(**user_dict)))

    def dump(self, f: IO) -> None:
        json.dump(self, f, cls=Users._Encoder, indent=2, separators=(",", ":"))


class UsersDatabase:
    """load & save users' database"""

    _encoding = "utf-8"
    _regkey = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _default_config_dir = Path(os.getenv("APPDATA")) / "SFVIP-Player"

    def __init__(self, config_loader: Loader, config_player: type[ConfigPlayer]) -> None:
        self._database = self._config_dir(config_loader, config_player) / "Database.json"
        if not self._database.is_file():
            raise SfvipError("No users database found")
        self.users = Users()

    @staticmethod
    def _config_dir(config_loader: Loader, config_player: type[ConfigPlayer]) -> Path:
        config_dir = config_player.config_dir
        if not _dir_exists(config_dir):
            config_dir = RegKey.value_by_name(*UsersDatabase._regkey)
            if not _dir_exists(config_dir):
                config_dir = str(UsersDatabase._default_config_dir.resolve())
            if _dir_exists(config_dir) and config_dir != config_player.config_dir:
                config_player.config_dir = config_dir
                config_loader.save()
        return Path(config_dir)

    def load(self) -> None:
        with self._database.open("r", encoding=UsersDatabase._encoding) as f:
            self.users.load(f)

    @_retry_if_exception(PermissionError, timeout=5)
    def save(self) -> None:
        with self._database.open("w", encoding=UsersDatabase._encoding) as f:
            self.users.dump(f)

    def atime(self) -> float:
        return self._database.stat().st_atime


class UsersProxies:
    """modify & restore users proxies"""

    def __init__(self, database: UsersDatabase) -> None:
        database.load()
        self._database = database
        self._database_accessed = time.time()
        self._saved = {user.Name: user.HttpProxy for user in self._database.users}
        self.upstream = {user.Address: user.HttpProxy for user in self._database.users if user.HttpProxy}

    def _set(self, proxy: Optional[str] = None) -> None:
        for user in self._database.users:
            if not user.is_playlist():
                user.HttpProxy = proxy if proxy else self._saved[user.Name]
        self._database.save()
        self._database_accessed = self._database.atime()

    @contextmanager
    def set(self, port: int) -> None:
        self._set(f"http://127.0.0.1:{port}")
        try:
            yield None
        finally:
            self._set()  # better safe than sorry

    @_retry_if_exception(NotAccessedYet, timeout=5)
    def restore_after_being_accessed(self) -> None:
        if self._database.atime() <= self._database_accessed:
            raise NotAccessedYet("retry")
        self._set()
