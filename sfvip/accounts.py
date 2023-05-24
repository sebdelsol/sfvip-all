import json
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Iterator

from mutex import SystemWideMutex

from .player import Player, PlayerConfigDirFile
from .retry import retry_if_exception
from .watch import WatchFile

logger = logging.getLogger(__name__)


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
        self._database = PlayerConfigDirFile("Database.json")
        self._accessed_by_me = self.atime
        self.accounts = _AccountList()
        self.lock = SystemWideMutex(f"file lock for {self._database}")
        self.watch = WatchFile(self._database)
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

    def __init__(self, player: Player, relaunch: threading.Event) -> None:
        self._player = player
        self._database = _Database()
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

    def _set_proxies(self, proxies: dict[str, str], msg: str) -> None:
        with self._database.lock:
            self._database.load()
            for account in self._accounts_to_set_proxies:
                if account.HttpProxy in proxies:
                    logger.info(
                        "%s proxy: %s",
                        msg,
                        f"'{account.HttpProxy}' -> '{proxies[account.HttpProxy]}'",
                    )
                    account.HttpProxy = proxies[account.HttpProxy]
            self._database.save()

    @contextmanager
    def set_proxies(self, proxies: dict[str, str]) -> Iterator[Callable[[], None]]:
        """set proxies and provide a method to restore the proxies"""
        self._set_proxies(proxies, "set")
        restore = {v: k for k, v in proxies.items()}

        def on_modified() -> None:
            if log := self._player_logs.get_last_timestamp_and_msg():
                timestamp, msg = log
                # account changed by sfvip player after the watch has started
                if "Edit User Account" in msg and timestamp > self._database.watch.started_time:
                    with self._database.lock:
                        # save before restoring
                        upstreams = self.upstreams
                        logger.info("accounts proxies have been externally modified")
                        self._set_proxies(restore, "restore")
                        # to avoid recursion
                        self._database.watch.started_time = self._database.atime
                    # check there're no new proxies
                    if not upstreams.issubset(restore.keys()):
                        logger.info("need to restart the player")
                        # debounce
                        self._database.watch.set_callback(None)
                        self._relaunch.set()
                        # needs to be at the very end to finish before entering the finally below
                        self._player.stop()

        def restore_after_being_read() -> None:
            self._database.wait_being_read()
            self._set_proxies(restore, "restore")
            # we can now safely release the databse
            self._database.lock.release()
            # and start the watch
            self._database.watch.set_callback(on_modified)
            self._database.watch.start()

        try:
            yield restore_after_being_read
        finally:
            self._database.watch.stop()
            self._set_proxies(restore, "restore")
