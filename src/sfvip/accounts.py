import json
import logging
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Iterator, Optional

from .player.config import PlayerDatabase
from .retry import retry_if_exception
from .shared import SharedEventTime, SharedProxiesToRestore
from .ui import UI, Info

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


class _Database:
    """load & save accounts' database"""

    class _NotExternallyAccessedYet(Exception):
        pass

    def __init__(self, app_roaming: Path) -> None:
        self._shared_self_modified = SharedEventTime(app_roaming / "DatabaseModified")
        self._database = PlayerDatabase()
        self._accessed_by_me = self._atime
        self.accounts = _AccountList()
        self.lock = self._database._lock
        self.watcher = self._database.get_watcher()
        if self._database.is_file():
            logger.info("accounts file: %s", self._database)
        else:
            logger.warning("no accounts file")

    @property
    def _atime(self) -> float:
        if self._database.is_file():
            return self._database.stat().st_atime
        return float("inf")

    @retry_if_exception(_NotExternallyAccessedYet, timeout=5)
    def wait_being_read(self) -> None:
        if self._database.is_file():
            if self._atime <= self._accessed_by_me:
                raise _Database._NotExternallyAccessedYet("retry")

    def load(self) -> None:
        self._database.open_and_do("r", self.accounts.load)
        self._accessed_by_me = self._atime

    def save(self) -> None:
        self._database.open_and_do("w", self.accounts.dump)
        self._accessed_by_me = self._atime
        self._shared_self_modified.set()

    @property
    def shared_self_modified_time(self):
        return self._shared_self_modified.time


class _UniqueNames(dict):
    def unique(self, name: str) -> str:
        n = self[name] = self.setdefault(name, 0) + 1
        if n > 1:
            return self.unique(f"{name}{n}")
        return name


class Accounts:
    """set & restore accounts proxies"""

    def __init__(self, app_roaming: Path) -> None:
        self._proxies_to_restore = SharedProxiesToRestore(app_roaming)
        self._database = _Database(app_roaming)
        # need to lock the database till the proxies have been restored
        self._database.lock.acquire()

    @property
    def upstreams(self) -> set[str]:
        self._database.load()
        return {account.HttpProxy for account in self._accounts_to_set}

    @property
    def _accounts_to_set(self) -> _AccountList:
        """don't handle m3u playlists"""
        return _AccountList(account for account in self._database.accounts if not account.is_playlist())

    def _set_info(
        self, proxies: dict[str, str], ui: UI, player_relaunch: Optional[Callable[[], None]] = None
    ) -> None:
        self._database.load()
        infos = []
        for account in self._accounts_to_set:
            infos.append(Info(account.Name, proxies.get(account.HttpProxy, ""), account.HttpProxy))
        ui.set_infos(infos, player_relaunch)

    def _set_proxies(self, proxies: dict[str, str], msg: str) -> None:
        names = _UniqueNames()
        with self._database.lock:
            self._database.load()
            for account in self._accounts_to_set:
                account.Name = names.unique(account.Name)
                if account.HttpProxy in proxies:
                    account.HttpProxy = proxies[account.HttpProxy]
                    logger.info("%s %s proxy to '%s'", msg, account.Name, account.HttpProxy)
            self._database.save()

    def _restore_proxies(self) -> None:
        self._set_proxies(self._proxies_to_restore.all, "restore")

    @contextmanager
    def set_proxies(self, proxies: dict[str, str], ui: UI) -> Iterator[Callable[[Callable[[], None]], None]]:
        """set proxies and provide a method to restore the proxies"""
        self._proxies_to_restore.add({v: k for k, v in proxies.items()})
        self._set_info(proxies, ui)
        self._set_proxies(proxies, "set")

        def on_modified(last_modified: float, player_relaunch: Callable[[], None]) -> None:
            # to prevent recursion check it occured after any modification done by any instance
            if last_modified > self._database.shared_self_modified_time:
                logger.info("accounts proxies file has been externaly modified")
                self._restore_proxies()
                self._set_info(proxies, ui, player_relaunch)

        def restore_after_being_read(player_relaunch: Callable[[], None]) -> None:
            self._database.wait_being_read()
            self._restore_proxies()
            # we can now safely release the database and start the watcher
            self._database.lock.release()
            self._database.watcher.add_callback(on_modified, player_relaunch)
            self._database.watcher.start()

        try:
            yield restore_after_being_read
        finally:
            self._database.watcher.stop()
            self._restore_proxies()
            self._proxies_to_restore.clean()
