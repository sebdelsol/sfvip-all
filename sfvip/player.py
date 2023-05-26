import json
import logging
import os
import subprocess
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Callable, Iterator, Optional, Self

from .regkey import RegKey
from .retry import retry_if_exception
from .ui import UI, Rect

logger = logging.getLogger(__name__)


class SfvipError(Exception):
    pass


class PlayerConfigDirFile(type(Path())):
    """any file player in config dir (searched only once)"""

    _regkey = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _default = Path(os.environ["APPDATA"]) / "SFVIP-Player"
    _configdir: Optional[Path] = None

    def __new__(cls, filename: str) -> Self:  # pylint: disable=arguments-differ
        def valid_dir(path: Path | str | None) -> bool:
            return bool(path and Path(path).is_dir())

        # check configdir (found only once and stored as a class attribute)
        if not valid_dir(cls._configdir):
            for path in RegKey.value_by_name(*cls._regkey), cls._default:
                if valid_dir(path):
                    cls._configdir = Path(path)  # type: ignore
                    break
            else:
                raise SfvipError("Player config dir not found")
        return super().__new__(cls, cls._configdir / filename)  # type: ignore

    @retry_if_exception(json.decoder.JSONDecodeError, PermissionError, timeout=1)
    def open_and_do(self, mode: str, do: Callable[[IO[str]], None]) -> Any:
        if self.is_file():
            with self.open(mode, encoding="utf-8") as f:
                return do(f)
        return None


class PlayerConfigFile(PlayerConfigDirFile):
    """player config file, load & save json"""

    _filename = "Config.json"

    def __new__(cls) -> Self:  # pylint: disable=arguments-differ
        return super().__new__(cls, cls._filename)

    def load(self) -> Optional[Any]:
        return self.open_and_do("r", json.load)

    def save(self, config: dict[str, Any]) -> bool:
        def dump(f: IO[str]) -> bool:
            json.dump(config, f, indent=2, separators=(",", ":"))
            return True

        return self.open_and_do("w", dump)


class PlayerLogs:
    """find and get player logs"""

    def __init__(self, player_path: str) -> None:
        self._path = Path(player_path).parent
        config_file = PlayerConfigFile()
        config = config_file.load()
        if config and isinstance(config, dict):
            config["IsLogging"] = True
            if config_file.save(config):
                logger.info("set player loggin on")
                return
        logger.warning("can't set player loggin on")

    def get_last_timestamp_and_msg(self) -> tuple[float, str] | None:
        """get before last line in the last log file"""
        logs = [file for file in self._path.iterdir() if file.match("Log-*.txt")]
        if logs:
            logs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            log = logs[0]
            with log.open("r") as f:
                lines = f.readlines()
            if len(lines) >= 2:
                return log.stat().st_mtime, lines[-2]
        return None


class _PlayerPath:
    """find the player exe"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey_search = (
        (
            RegKey.name_by_value,
            winreg.HKEY_CLASSES_ROOT,
            r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache",
            lambda found: [os.path.splitext(found)[0]],
        ),
        (
            RegKey.search_name_contains,
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store",
            lambda found: found,
        ),
    )

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        if not self._valid_exe(player_path):
            for search_method in self._get_paths_from_regkey, self._get_path_from_user:
                if player_path := search_method(ui):
                    break
            else:
                raise SfvipError("Player not found")
        self.path: str = player_path  # it's been found # type: ignore

    @staticmethod
    def _valid_exe(path: Path | str | None) -> bool:
        return bool(path and (_path := Path(path)).is_file() and _path.match(_PlayerPath._pattern))

    def _get_paths_from_regkey(self, _) -> Optional[str]:
        for search_method, hkey, key, handle_found in _PlayerPath._regkey_search:
            if found := search_method(hkey, key, _PlayerPath._name):
                for path in handle_found(found):
                    if self._valid_exe(path):
                        return path
        return None

    def _get_path_from_user(self, ui: UI) -> Optional[str]:
        ui.showinfo(f"Please find {_PlayerPath._name.capitalize()}")
        while True:
            if player := ui.find_file(_PlayerPath._name, _PlayerPath._pattern):
                if self._valid_exe(player):
                    return player
            if not ui.askretry(message=f"{_PlayerPath._name.capitalize()} not found, try again ?"):
                return None


class Player:
    """run the player"""

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        self.path = _PlayerPath(player_path, ui).path
        self.logs = PlayerLogs(self.path)
        self._proc: subprocess.Popen[bytes] | None = None
        logger.info("player: %s", self.path)

    @property
    def rect(self):
        if config := PlayerConfigFile().load():
            if isinstance(config, dict) and not config.get("IsMaximized"):
                return Rect.from_dict_keys(config, "Left", "Top", "Width", "Height")
        return Rect()

    @contextmanager
    def run(self) -> Iterator[subprocess.Popen[bytes]]:
        if not self.path:
            raise SfvipError("No player")
        with subprocess.Popen([self.path]) as self._proc:
            logger.info("player started")
            yield self._proc
        logger.info("player stopped")
        self._proc = None

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
