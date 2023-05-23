import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Any, Callable, Iterator, Optional

from config_loader.mutex import SystemWideMutex

from .player import Player
from .watch import WatchFile


class NotAccessedYet(Exception):
    pass


TFuncNone = Callable[..., None]
TFuncBool = Callable[..., bool]
TExceptions = type[Exception] | tuple[type[Exception]]


def _retry_if_exception(exceptions: TExceptions, timeout: int) -> Callable[[TFuncNone], TFuncBool]:
    def decorator(func: TFuncNone) -> TFuncBool:
        def wrapper(*args: Any, **kwargs: Any) -> bool:
            start = time.perf_counter()
            while time.perf_counter() - start <= timeout:
                try:
                    func(*args, **kwargs)
                    return True
                except exceptions:
                    time.sleep(0.1)
            return False

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
        def default(self, o: _Account) -> dict[str, str]:
            return o.__dict__

    def load(self, f: IO[str]) -> None:
        self.clear()
        self.extend(json.load(f, object_hook=lambda dct: _Account(**dct)))

    def dump(self, f: IO[str]) -> None:
        json.dump(self, f, cls=_AccountList._Encoder, indent=2, separators=(",", ":"))


class _Database:
    """load & save accounts' database"""

    def __init__(self, config_dir: Path) -> None:
        self._database: Optional[Path] = None
        database = config_dir / "Database.json"
        if database.is_file():
            self._database = database
            self._own_atime = self.atime
        self.accounts = _AccountList()
        self.lock = SystemWideMutex(f"file lock for {self._database}")
        self.watch = WatchFile(self._database)

    @property
    def atime(self) -> float:
        if self._database:
            return self._database.stat().st_atime
        return float("inf")

    def has_been_externally_accessed(self) -> bool:
        if self._database:
            return self.atime > self._own_atime
        return True

    def _open(self, mode: str, op_on_file: Callable[[IO[str]], None]) -> None:
        if self._database:
            with self._database.open(mode, encoding="utf-8") as f:
                op_on_file(f)
            self._own_atime = self.atime

    @_retry_if_exception(json.decoder.JSONDecodeError, timeout=1)
    def load(self) -> None:
        self._open("r", self.accounts.load)

    @_retry_if_exception(PermissionError, timeout=5)
    def save(self) -> None:
        self._open("w", self.accounts.dump)


class Accounts:
    """modify & restore accounts proxies"""

    def __init__(self, player: Player, relaunch: threading.Event) -> None:
        self._player = player
        self._database = _Database(player.config_dir)
        self._player_logs = player.logs
        # need to lock the database till the proxies have been restored
        self._database.lock.acquire()
        self._relaunch = relaunch

    @property
    def upstreams(self) -> set[str]:
        self._database.load()
        return {account.HttpProxy for account in self._accounts_to_set_proxies}

    @property
    def _accounts_to_set_proxies(self) -> _AccountList:
        """don't handle m3u playlists"""
        return _AccountList(account for account in self._database.accounts if not account.is_playlist())

    def _set_proxies(self, proxies: dict[str, str]) -> None:
        self._database.load()
        for account in self._accounts_to_set_proxies:
            account.HttpProxy = proxies.get(account.HttpProxy, account.HttpProxy)
        self._database.save()

    @_retry_if_exception(NotAccessedYet, timeout=5)
    def _wait_being_read(self) -> None:
        if not self._database.has_been_externally_accessed():
            raise NotAccessedYet("retry")

    @contextmanager
    def set_proxies(self, proxies: dict[str, str]) -> Iterator[Callable[[], None]]:
        """set proxies and provide a method to restore the proxies"""
        self._set_proxies(proxies)
        restore = {v: k for k, v in proxies.items()}

        def on_modified() -> None:
            if log := self._player_logs.get_last_time_msg():
                timestamp, msg = log
                # account changed by sfvip player after the watch has started
                if "Edit User Account" in msg and timestamp > self._database.watch.started_time:
                    with self._database.lock:
                        # save before restoring
                        upstreams = self.upstreams
                        self._set_proxies(restore)
                        # to avoid recursion
                        self._database.watch.started_time = self._database.atime
                    # check there's no new proxies
                    if not upstreams.issubset(restore.keys()):
                        # debounce
                        self._database.watch.set_callback(None)
                        self._relaunch.set()
                        # needs to be at the very end to finish before entering the finally below
                        self._player.stop()

        def restore_after_being_read() -> None:
            self._wait_being_read()
            self._set_proxies(restore)
            self._database.lock.release()
            self._database.watch.set_callback(on_modified)
            self._database.watch.start()

        try:
            yield restore_after_being_read
        finally:
            self._database.watch.stop()
            with self._database.lock:
                self._set_proxies(restore)
