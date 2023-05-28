import logging
import os
import subprocess
import threading
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional

from ..registry import Registry
from ..ui import UI, Rect
from .config import PlayerConfig
from .exception import PlayerError

logger = logging.getLogger(__name__)

# TODO restore player pos


class _PlayerPosition(PlayerConfig):
    _keys = "Left", "Top", "Width", "Height", "IsMaximized"

    @property
    def rect(self) -> Rect:
        if config := self.load():
            return Rect(*(config[key] for key in _PlayerPosition._keys))
        return Rect()


class _PlayerForceLogging(PlayerConfig):
    """force player logging, watch for change"""

    def __init__(self) -> None:
        super().__init__()
        self._switch_on()

    def _switch_on(self) -> bool:
        with self._lock:
            if config := self.load():
                if config.get("IsLogging") is not True:
                    config["IsLogging"] = True
                    return self.save(config)
        return False

    def _on_modified(self, player_stop_and_relaunch) -> None:
        if self._switch_on():
            logger.info("Player logging had to be switched on after a change")
            player_stop_and_relaunch()

    def watch(self, player_stop_and_relaunch: Callable[[], None]):
        watcher = self.get_watcher()
        watcher.add_callback(self._on_modified, player_stop_and_relaunch)
        return watcher


class PlayerLogs:
    """get player logs"""

    def __init__(self, player_path: str) -> None:
        self._player_dir = Path(player_path).parent

    def get_last_timestamp_and_msg(self) -> Optional[tuple[float, str]]:
        """get before last line in the last log file"""
        logs = [file for file in self._player_dir.iterdir() if file.match("Log-*.txt")]
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
    _registry_search = (
        (
            Registry.name_by_value,
            winreg.HKEY_CLASSES_ROOT,
            r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache",
            lambda found: [os.path.splitext(found)[0]],
        ),
        (
            Registry.search_name_contains,
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store",
            lambda found: found,
        ),
    )

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        if not self._valid_exe(player_path):
            for search_method in self._get_paths_from_registry, self._get_path_from_user:
                if player_path := search_method(ui):
                    break
            else:
                raise PlayerError("Sfvip Player not found")
        self.path: str = player_path  # it's been found # type: ignore
        logger.info("player: %s", self.path)

    @staticmethod
    def _valid_exe(path: Optional[Path | str]) -> bool:
        return bool(path and (_path := Path(path)).is_file() and _path.match(_PlayerPath._pattern))

    def _get_paths_from_registry(self, _) -> Optional[str]:
        for search_method, hkey, key, handle_found in _PlayerPath._registry_search:
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
        self.position = _PlayerPosition()
        self._force_logging = _PlayerForceLogging()
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._launch = True

    def do_launch(self) -> bool:
        launch = self._launch
        self._launch = False  # won't launch next except if explitcitly set
        return launch

    @contextmanager
    def run(self) -> Iterator[None]:
        if not self.path:
            raise PlayerError("No Sfvip Player to launch")

        with self._force_logging.watch(self.stop_and_relaunch):
            with subprocess.Popen([self.path]) as self._process:
                logger.info("player started")
                yield
            with self._process_lock:
                self._process = None
            logger.info("player stopped")

    def stop_and_relaunch(self) -> None:
        time.sleep(1)  # give time to be stopped by the user
        with self._process_lock:
            if self._process:
                if self._process.poll() is None:  # still running ?
                    self._process.terminate()
                    logger.info("restart the player")
                    self._launch = True
