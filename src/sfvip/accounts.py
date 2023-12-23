import json
import logging
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Callable, Iterator, Optional, Sequence

from .player.config import PlayerDatabase
from .shared import SharedEventTime, SharedProxiesToRestore
from .ui import UI, Info
from .utils.retry import RetryIfException

logger = logging.getLogger(__name__)


class _JsonTrailingCommas:
    _object = re.compile(r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    _array = re.compile(r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')

    @staticmethod
    def remove(json_str: str) -> str:
        json_str = _JsonTrailingCommas._object.sub("}", json_str)
        return _JsonTrailingCommas._array.sub("]", json_str)


class _UniqueNames(dict[str, int]):
    def unique(self, name: str) -> str:
        n = self[name] = self.setdefault(name, 0) + 1
        if n > 1:
            return self.unique(f"{name}{n}")
        return name


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


class _Accounts(list[_Account]):
    """list of Accounts with json load & dump"""

    class _Encoder(json.JSONEncoder):
        def default(self, o: _Account) -> dict[str, str]:
            return o.__dict__

    def load(self, f: IO[str]) -> None:
        self.clear()
        json_str = _JsonTrailingCommas.remove(f.read())
        self.extend(json.loads(json_str, object_hook=lambda dct: _Account(**dct)))

    def dump(self, f: IO[str]) -> None:
        json.dump(self, f, cls=_Accounts._Encoder, indent=2, separators=(",", ":"))


class _Database:
    """load & save accounts' database"""

    class _NotExternallyAccessedYet(Exception):
        pass

    def __init__(self, app_roaming: Path) -> None:
        self._shared_self_modified = SharedEventTime(app_roaming / "DatabaseModified", "database modified")
        self._database = PlayerDatabase()
        self._accessed_by_me = self._atime
        self.accounts = _Accounts()
        self.lock = self._database.lock
        self.watcher = self._database.get_watcher()
        if self._database.is_file():
            logger.info("Accounts file is '%s'", self._database)
        else:
            logger.warning("No accounts file")

    @property
    def _atime(self) -> float:
        if self._database.is_file():
            return self._database.stat().st_atime
        return float("inf")

    @RetryIfException(_NotExternallyAccessedYet, timeout=5)
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
        # time when any instance have internally modified the database
        return self._shared_self_modified.time


class AccountsProxies:
    """set & restore accounts proxies"""

    def __init__(self, app_roaming: Path, ui: UI) -> None:
        self._ui = ui
        self._app_roaming = app_roaming
        self._database = _Database(app_roaming)
        # need to lock the database till the proxies have been restored
        self._database.lock.acquire()

    @property
    def upstreams(self) -> set[str]:
        self._database.load()
        return {account.HttpProxy for account in self._accounts_to_set}

    @property
    def _accounts_to_set(self) -> _Accounts:
        """don't handle m3u playlists"""
        return _Accounts(account for account in self._database.accounts if not account.is_playlist())

    def _set_proxies(self, proxies: dict[str, str], msg: str) -> None:
        names = _UniqueNames()
        with self._database.lock:
            self._database.load()
            for account in self._accounts_to_set:
                account.Name = names.unique(account.Name)
                if account.HttpProxy in proxies:
                    account.HttpProxy = proxies[account.HttpProxy]
                    logger.info("%s user %s proxy to '%s'", msg.capitalize(), account.Name, account.HttpProxy)
            self._database.save()

    def _infos(self, proxies: dict[str, str]) -> Sequence[Info]:
        self._database.load()
        return tuple(
            Info(account.Name, proxies.get(account.HttpProxy, ""), account.HttpProxy)
            for account in self._accounts_to_set
        )

    @contextmanager
    def set(self, proxies: dict[str, str]) -> Iterator[Callable[[Callable[[int], None]], None]]:
        """set proxies, infos and provide a method to restore the proxies"""

        def set_infos(player_relaunch: Optional[Callable[[int], None]] = None) -> None:
            infos = self._infos(proxies)
            self._ui.set_infos(infos, player_relaunch)

        def set_proxies() -> None:
            proxies_to_restore.add({v: k for k, v in proxies.items()})
            self._set_proxies(proxies, "set")

        def restore_proxies() -> None:
            self._set_proxies(proxies_to_restore.all, "restore")

        def restore_after_being_read(player_relaunch: Callable[[int], None]) -> None:
            def on_modified(last_modified: float) -> None:
                # to prevent recursion check it occured after any modification done by any instance
                if last_modified > self._database.shared_self_modified_time:
                    logger.info("Accounts proxies file has been externaly modified")
                    restore_proxies()
                    set_infos(player_relaunch)

            self._database.wait_being_read()
            restore_proxies()
            # we can now safely release the database and start the watcher
            self._database.lock.release()
            self._database.watcher.add_callback(on_modified)
            self._database.watcher.start()

        proxies_to_restore = SharedProxiesToRestore(self._app_roaming)
        set_infos()
        set_proxies()
        try:
            yield restore_after_being_read
        finally:
            self._database.watcher.stop()
            restore_proxies()
            proxies_to_restore.clean()
