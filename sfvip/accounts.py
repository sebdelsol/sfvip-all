import json
import os
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Optional

from pyparsing import Any

from .mutex import NamedMutex
from .regkey import RegKey


class NotAccessedYet(Exception):
    pass


TFunc = Callable[..., Any]
TExceptions = type[Exception] | tuple[type[Exception]]


def _retry_if_exception(exceptions: TExceptions, timeout: int) -> Callable[[TFunc], TFunc]:
    def decorator(func) -> TFunc:
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            while time.perf_counter() - start <= timeout:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    time.sleep(0.1)
            return None

        return wrapper

    return decorator


def _dir_exists(path: str) -> bool:
    if path:
        path: Path = Path(path)
        return path.is_dir()
    return False


class _Account(SimpleNamespace):
    """a sfvip account"""

    _playlist_ext = ".m3u", ".m3u8"

    def __init__(self, **kwargs: str) -> None:
        # pylint: disable=invalid-name
        self.Address: str
        self.HttpProxy: str
        super().__init__(**kwargs)

    def is_playlist(self) -> bool:
        path = Path(self.Address)
        return path.suffix in _Account._playlist_ext or path.is_file()


class _AccountList(list[_Account]):
    """list of Accounts with json load & dump"""

    class _Encoder(json.JSONEncoder):
        # pylint: disable=arguments-renamed
        def default(self, account: _Account) -> dict:
            return account.__dict__

    def load(self, f: IO) -> None:
        self.clear()
        self.extend(json.load(f, object_hook=lambda account_dict: _Account(**account_dict)))

    def dump(self, f: IO) -> None:
        json.dump(self, f, cls=_AccountList._Encoder, indent=2, separators=(",", ":"))


class _Database:
    """load & save accounts' database"""

    _encoding = "utf-8"
    _regkey_config_dir = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _default_config_dir = Path(os.getenv("APPDATA")) / "SFVIP-Player"

    def __init__(self) -> None:
        self._database: Optional[_Database] = None
        database = self._config_dir() / "Database.json"
        if database.is_file():
            self._database = database
            self._atime = self._database.stat().st_atime
        self.accounts = _AccountList()

    @staticmethod
    def _config_dir() -> Path:
        config_dir = RegKey.value_by_name(*_Database._regkey_config_dir)
        if not _dir_exists(config_dir):
            config_dir = str(_Database._default_config_dir.resolve())
        return Path(config_dir)

    def load(self) -> None:
        if self._database:
            with self._database.open("r", encoding=_Database._encoding) as f:
                self.accounts.load(f)
            self._update_atime()

    @_retry_if_exception(PermissionError, timeout=5)
    def save(self) -> None:
        if self._database:
            with self._database.open("w", encoding=_Database._encoding) as f:
                self.accounts.dump(f)
            self._update_atime()

    def _update_atime(self) -> None:
        self._atime = self._database.stat().st_atime

    def has_been_externally_accessed(self) -> bool:
        if self._database:
            return self._database.stat().st_atime > self._atime
        return True


class Accounts:
    """modify & restore accounts proxies"""

    def __init__(self, app_name: str) -> None:
        self._database = _Database()
        self._database.load()
        self._mutex = NamedMutex(app_name)
        self.upstream_proxies = {account.HttpProxy for account in self._accounts_to_set_proxies}

    @property
    def _accounts_to_set_proxies(self) -> _AccountList:
        """don't handle m3u playlists"""
        return _AccountList(account for account in self._database.accounts if not account.is_playlist())

    def _set_proxies(self, proxies: dict[str, str]) -> None:
        self._database.load()
        for account in self._accounts_to_set_proxies:
            if account.HttpProxy in proxies:
                account.HttpProxy = proxies[account.HttpProxy]
        self._database.save()

    @contextmanager
    def set_proxies(self, proxies_by_upstreams: dict[str, str]) -> Callable[[], None]:
        """
        set accounts proxies & provide a function to restore those
        don't mess with the database till we have restored accounts proxies
        """
        self._mutex.acquire()
        self._set_proxies(proxies_by_upstreams)
        proxies_to_restore = {proxy: upstream for upstream, proxy in proxies_by_upstreams.items()}

        @_retry_if_exception(NotAccessedYet, timeout=5)
        def restore_after_being_accessed() -> None:
            if not self._database.has_been_externally_accessed():
                raise NotAccessedYet("retry")
            self._set_proxies(proxies_to_restore)
            self._mutex.release()

        try:
            yield restore_after_being_accessed
        finally:
            with self._mutex:
                self._set_proxies(proxies_to_restore)
