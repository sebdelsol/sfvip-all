import json
import logging
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Iterator

from .player import PlayerLogs
from .player.config import PlayerDatabase
from .retry import retry_if_exception

logger = logging.getLogger(__name__)


class _Account(SimpleNamespace):
    """a sfvip account"""

    _playlist_ext = ".m3u", ".m3u8"

    def __init__(self, **kwargs: str) -> None:
        # pylint: disable=invalid-name
        self.Name: str
        self.Address: str
        self.HttpProxy: str
        super().__init__(**kwargs)

    def is_playlist(self) -> bool:
        path = Path(self.Address)
        return path.suffix in _Account._playlist_ext or path.is_file()


class _AccountList(list[_Account]):
    """list of Accounts with json load & dump"""

    class _Encoder(json.JSONEncoder):
        def default(self, o: _Account) -> dict[str, str]:
            return o.__dict__

    def load(self, f: IO[str]) -> None:
        self.clear()
        self.extend(json.load(f, object_hook=lambda dct: _Account(**dct)))

    def dump(self, f: IO[str]) -> None:
        json.dump(self, f, cls=_AccountList._Encoder, indent=2, separators=(",", ":"))


class NotExternallyAccessedYet(Exception):
    pass


class _Database:
    """load & save accounts' database"""

    def __init__(self) -> None:
        self._database = PlayerDatabase()
        self._accessed_by_me = self.atime
        self.accounts = _AccountList()
        self.lock = self._database._lock
        self.watcher = self._database.get_watcher()
        if self._database.is_file():
            logger.info("accounts file: %s", self._database)
        else:
            logger.warning("no accounts file")

    @property
    def atime(self) -> float:
        if self._database.is_file():
            return self._database.stat().st_atime
        return float("inf")

    @retry_if_exception(NotExternallyAccessedYet, timeout=5)
    def wait_being_read(self) -> None:
        if self._database.is_file():
            if self.atime <= self._accessed_by_me:
                raise NotExternallyAccessedYet("retry")

    def load(self) -> None:
        self._database.open_and_do("r", self.accounts.load)
        self._accessed_by_me = self.atime

    def save(self) -> None:
        self._database.open_and_do("w", self.accounts.dump)
        self._accessed_by_me = self.atime


class Accounts:
    """modify & restore accounts proxies"""

    def __init__(self, player_logs: PlayerLogs) -> None:
        self._database = _Database()
        self._player_logs = player_logs
        # need to lock the database till the proxies have been restored
        self._database.lock.acquire()

    @property
    def upstreams(self) -> set[str]:
        self._database.load()
        return {account.HttpProxy for account in self._accounts_to_set_proxies}

    @property
    def _accounts_to_set_proxies(self) -> _AccountList:
        """don't handle m3u playlists"""
        return _AccountList(account for account in self._database.accounts if not account.is_playlist())

    def _set_proxies(self, proxies: dict[str, str], msg: str) -> None:
        with self._database.lock:
            self._database.load()
            for account in self._accounts_to_set_proxies:
                if account.HttpProxy in proxies:
                    proxy = proxies[account.HttpProxy]
                    logger.info("%s '%s' proxy: %s", msg, account.Name, f"'{account.HttpProxy}' -> '{proxy}'")
                    account.HttpProxy = proxy
            self._database.save()

    @contextmanager
    def set_proxies(self, proxies: dict[str, str]) -> Iterator[Callable[[Callable[[], None]], None]]:
        """set proxies and provide a method to restore the proxies"""
        self._set_proxies(proxies, "set")
        restore = {v: k for k, v in proxies.items()}
        known_proxies = sum(proxies.items(), ())

        def on_modified(player_stop_and_relaunch: Callable[[], None]) -> None:
            if log := self._player_logs.get_last_timestamp_and_msg():
                timestamp, msg = log
                # an account has been changed by the user after the watcher has started ?
                if "Edit User Account" in msg and timestamp > self._database.watcher.modified_time:
                    logger.info("accounts proxies have been externally modified")
                    upstreams = self.upstreams  # saved for checking new proxies
                    self._set_proxies(restore, "restore")
                    if not upstreams.issubset(known_proxies):  # new proxies ?
                        player_stop_and_relaunch()

        def restore_after_being_read(player_stop_and_relaunch: Callable[[], None]) -> None:
            self._database.wait_being_read()
            self._set_proxies(restore, "restore")
            # we can now safely release the database ans start the watcher
            self._database.lock.release()
            self._database.watcher.add_callback(on_modified, player_stop_and_relaunch)
            self._database.watcher.start()

        try:
            yield restore_after_being_read
        finally:
            self._database.watcher.stop()
            self._set_proxies(restore, "restore")
