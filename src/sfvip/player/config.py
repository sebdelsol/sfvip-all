import json
import logging
import winreg
from functools import cache
from pathlib import Path
from typing import IO, Any, Callable, Optional, Self

from ...winapi import mutex
from ..localization import LOC
from ..tools.retry import RetryIfException
from ..watchers import FileWatcher, RegistryWatcher
from .exception import PlayerConfigError
from .registry import Registry

logger = logging.getLogger(__name__)


class _PlayerConfigDir:
    """cached player config dir, provide system wide locks and watchers for its files"""

    _from_registry = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"

    @classmethod
    @cache
    def path(cls) -> Path:
        path = Registry.value_by_name(*cls._from_registry)
        if path and (path := Path(path)).is_dir():
            logger.info("player config dir is '%s'", path)
            return path
        raise PlayerConfigError(LOC.PlayerConfigNotFound)
        # TODO fallback to app roaming Path(os.environ["APPDATA"]) / "SFVIP-Player"

    @classmethod
    @cache
    def lock_for(cls, filename: str) -> mutex.SystemWideMutex:
        return mutex.SystemWideMutex(f"file lock for {_PlayerConfigDir.path() / filename}")

    @classmethod
    @cache
    def watcher_for(cls, filename: str) -> FileWatcher:
        return FileWatcher(_PlayerConfigDir.path() / filename)

    @classmethod
    def clear_all_caches(cls) -> None:
        # pylint: disable=no-member
        cls.path.cache_clear()
        cls.lock_for.cache_clear()
        cls.watcher_for.cache_clear()


class PlayerConfigDirSettingWatcher:
    """registry watcher of the player config dir"""

    _watcher_sigleton: Optional[RegistryWatcher] = None

    def __init__(self) -> None:
        if PlayerConfigDirSettingWatcher._watcher_sigleton is None:
            try:
                PlayerConfigDirSettingWatcher._watcher_sigleton = RegistryWatcher(*_PlayerConfigDir._from_registry)
            except FileNotFoundError as err:
                raise PlayerConfigError(LOC.PlayerConfigNotFound) from err
        self._watcher = self._watcher_sigleton

    @staticmethod
    def has_changed() -> None:
        _PlayerConfigDir.clear_all_caches()


class PlayerConfigDirFile(type(Path())):
    """a player config file, opened with a system wide lock, watcher available"""

    _filename = None

    def __new__(cls) -> Self:  # pylint: disable=arguments-differ
        assert cls._filename is not None
        return super().__new__(cls, _PlayerConfigDir.path() / cls._filename)

    def __init__(self) -> None:
        self._lock = _PlayerConfigDir.lock_for(self._filename)
        super().__init__()

    def get_watcher(self) -> FileWatcher:
        return _PlayerConfigDir.watcher_for(self._filename)

    @RetryIfException(json.JSONDecodeError, PermissionError, timeout=1)
    def open_and_do(self, mode: str, do: Callable[[IO[str]], None]) -> Any:
        if self.is_file():
            with self._lock:
                with self.open(mode, encoding="utf-8") as f:
                    return do(f)
        return None


class PlayerConfig(PlayerConfigDirFile):
    """the player config file, load & save"""

    _filename = "Config.json"

    def load(self) -> Optional[dict]:
        if config := self.open_and_do("r", json.load):
            if isinstance(config, dict):
                return config
        return None

    def save(self, config: dict) -> None:
        def dump(f: IO[str]) -> None:
            json.dump(config, f, indent=2, separators=(",", ":"))

        self.open_and_do("w", dump)


class PlayerDatabase(PlayerConfigDirFile):
    _filename = "Database.json"
