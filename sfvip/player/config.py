import json
import logging
import os
import winreg
from functools import cache
from pathlib import Path
from typing import IO, Any, Callable, Optional, Self

from mutex import SystemWideMutex

from ..registry import Registry
from ..retry import retry_if_exception
from ..watcher import FileWatcher
from .exception import PlayerError

logger = logging.getLogger(__name__)


class _PlayerConfigDir:
    """cached player config dir, provide system wide locks and watchers for its files"""

    _from_registry = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _default = Path(os.environ["APPDATA"]) / "SFVIP-Player"

    @classmethod
    @cache
    def path(cls) -> Path:
        for path in Registry.value_by_name(*cls._from_registry), cls._default:
            if path and (path := Path(path)).is_dir():
                logger.info("player config dir: %s", path)
                return path
        raise PlayerError("Sfvip Player configuration directory not found")

    @classmethod
    @cache
    def lock_for(cls, filename: str) -> SystemWideMutex:
        return SystemWideMutex(f"file lock for {_PlayerConfigDir.path() / filename}")

    @classmethod
    @cache
    def watcher_for(cls, filename: str) -> FileWatcher:
        return FileWatcher(_PlayerConfigDir.path() / filename)


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

    @retry_if_exception(json.decoder.JSONDecodeError, PermissionError, timeout=1)
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

    def save(self, config: dict) -> bool:
        def dump(f: IO[str]) -> bool:
            json.dump(config, f, indent=2, separators=(",", ":"))
            return True

        return self.open_and_do("w", dump)


class PlayerDatabase(PlayerConfigDirFile):
    _filename = "Database.json"
