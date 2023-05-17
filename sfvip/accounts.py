import json
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Optional

from pyparsing import Any

from .mutex import NamedMutex


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

    def __init__(self, config_dir: Path) -> None:
        self._database: Optional[Path] = None
        database = config_dir / "Database.json"
        if database.is_file():
            self._database = database
            self._own_atime = self._atime
        self.accounts = _AccountList()

    @property
    def _atime(self) -> float:
        return self._database.stat().st_atime

    def has_been_externally_accessed(self) -> bool:
        if self._database:
            return self._atime > self._own_atime
        return True

    def _open(self, mode: str, op_on_file: Callable[[IO], None]) -> None:
        if self._database:
            with self._database.open(mode, encoding="utf-8") as f:
                op_on_file(f)
            self._own_atime = self._atime

    def load(self) -> None:
        self._open("r", self.accounts.load)

    @_retry_if_exception(PermissionError, timeout=5)
    def save(self) -> None:
        self._open("w", self.accounts.dump)


class Accounts:
    """modify & restore accounts proxies"""

    def __init__(self, app_name: str, config_dir: Path) -> None:
        self._database = _Database(config_dir)
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
            account.HttpProxy = proxies.get(account.HttpProxy, account.HttpProxy)
        self._database.save()

    @contextmanager
    def set_proxies(self, local_proxies_by_upstreams: dict[str, str]) -> Callable[[], None]:
        """
        set accounts proxies & provide a function to restore those
        don't mess with the database till we have restored accounts proxies
        """
        self._mutex.acquire()
        self._set_proxies(local_proxies_by_upstreams)
        undo = {v: k for k, v in local_proxies_by_upstreams.items()}

        @_retry_if_exception(NotAccessedYet, timeout=5)
        def restore_after_being_accessed() -> None:
            if not self._database.has_been_externally_accessed():
                raise NotAccessedYet("retry")
            self._set_proxies(undo)
            self._mutex.release()

        try:
            yield restore_after_being_accessed
        finally:
            with self._mutex:
                self._set_proxies(undo)
