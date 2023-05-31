import logging
import os
import subprocess
import threading
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional

from winapi import SystemWideMutex, get_rect_for_pid

from ..registry import Registry
from ..ui import UI, Rect
from ..watchers import FileWatcher, RegistryWatcher
from .config import PlayerConfig, PlayerConfigDirSettingWatcher
from .exception import PlayerError

logger = logging.getLogger(__name__)


class PlayerLogs:
    """get player last log"""

    class Log(NamedTuple):
        timestamp: float
        msg: str

    def __init__(self, player_path: str) -> None:
        self._player_dir = Path(player_path).parent

    def get_last(self) -> Optional["PlayerLogs.Log"]:
        """get before last line in the last log file"""
        logs = [file for file in self._player_dir.iterdir() if file.match("Log-*.txt")]
        if logs:
            logs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            log = logs[0]
            with log.open("r") as f:
                lines = f.readlines()
            if len(lines) >= 2:
                return PlayerLogs.Log(log.stat().st_mtime, lines[-2])
        return None


class _PlayerLogSetting(PlayerConfig):
    """force player logging, watch for a change"""

    _key = "IsLogging"

    def __init__(self) -> None:
        super().__init__()
        with self._lock:
            if config := self.load():
                if config.get(_PlayerLogSetting._key) is False:
                    logger.info("Force player logging setting to on")
                    config[_PlayerLogSetting._key] = True
                    self.save(config)

    def _is_off(self) -> bool:
        with self._lock:
            if config := self.load():
                return config.get(_PlayerLogSetting._key) is False
        return False

    def _on_modified(self, _, player_stop_and_relaunch: Callable[[], None]) -> None:
        # do not modify the config file
        # to avoid other sfvip instance to miss the change
        if self._is_off():
            logger.info("Player logging setting has been switched off")
            player_stop_and_relaunch()

    def watch(self, player_stop_and_relaunch: Callable[[], None]) -> FileWatcher:
        watcher = self.get_watcher()
        watcher.add_callback(self._on_modified, player_stop_and_relaunch)
        return watcher


class _PlayerConfigDirSetting(PlayerConfigDirSettingWatcher):
    """watch for a change of the player config dir setting"""

    def _on_modified(self, value: str, player_stop_and_relaunch: Callable[[], None]) -> None:
        logger.info("Player config dir has changed to %s", value)
        self.has_changed()  # clear the relevant caches
        player_stop_and_relaunch()

    def watch(self, player_stop_and_relaunch: Callable[[], None]) -> RegistryWatcher:
        assert self._watcher is not None
        self._watcher.add_callback(self._on_modified, player_stop_and_relaunch)
        return self._watcher


class _PlayerRect(PlayerConfig):
    """load & save the player's window position"""

    _keys = "Left", "Top", "Width", "Height", "IsMaximized"

    @property
    def rect(self) -> Rect:
        if config := self.load():
            return Rect(*(config[key] for key in _PlayerRect._keys))
        return Rect()

    def set(self, rect: Rect) -> None:
        if rect.valid():
            if config := self.load():
                for key, value in zip(_PlayerRect._keys, rect):
                    config[key] = value
                self.save(config)


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
        for search_method, hkey, path, handle_found in _PlayerPath._registry_search:
            if found := search_method(hkey, path, _PlayerPath._name):
                for player in handle_found(found):
                    if self._valid_exe(player):
                        return player
        return None

    def _get_path_from_user(self, ui: UI) -> Optional[str]:
        ui.showinfo(f"Please find {_PlayerPath._name.capitalize()}")
        while True:
            if player := ui.find_file(_PlayerPath._name, _PlayerPath._pattern):
                if self._valid_exe(player):
                    return player
            if not ui.askretry(message=f"{_PlayerPath._name.capitalize()} not found, try again ?"):
                return None


class _Launcher:
    """handle player's relaunch"""

    def __init__(self) -> None:
        self._launch = True
        self._rect: Optional[Rect] = None

    def want_to_launch(self) -> bool:
        launch = self._launch
        # won't launch next time except if explitcitly set
        self._launch = False
        return launch

    def set_relaunch(self, rect: Optional[tuple[int, int, int, int]]) -> None:
        self._launch = True
        self._rect = Rect(*rect) if rect else None

    @property
    def rect(self) -> Optional[Rect]:
        if self._rect and self._rect.valid():
            return self._rect
        return None


class Player:
    """run the player"""

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        self.path = _PlayerPath(player_path, ui).path
        self.logs = PlayerLogs(self.path)
        self._rect: Optional[_PlayerRect] = None
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._launcher = _Launcher()

    def want_to_launch(self) -> bool:
        launch = self._launcher.want_to_launch()
        if launch:
            self._rect = _PlayerRect()
        return launch

    @property
    def rect(self) -> Rect:
        if self._launcher.rect:
            return self._launcher.rect
        assert self._rect is not None
        return self._rect.rect

    @contextmanager
    def run(self) -> Iterator[None]:
        assert self.path is not None
        assert self._rect is not None

        set_rect_lock = None
        if self._rect and self._launcher.rect:
            # prevent another instance of sfvip to run
            # before the player position has been set
            set_rect_lock = SystemWideMutex("set player rect lock")
            set_rect_lock.acquire()
            self._rect.set(self._launcher.rect)

        with _PlayerLogSetting().watch(self.stop_and_relaunch):
            with _PlayerConfigDirSetting().watch(self.stop_and_relaunch):
                with subprocess.Popen([self.path]) as self._process:
                    logger.info("player started")
                    if set_rect_lock:
                        # give time to the player to read its config
                        time.sleep(0.5)
                        set_rect_lock.release()
                    yield
                with self._process_lock:
                    self._process = None
                logger.info("player stopped")

    def stop_and_relaunch(self) -> None:
        # give time to the player to stop if it's been initiated by the user
        time.sleep(1)
        with self._process_lock:
            if self._process:
                if self._process.poll() is None:  # still running ?
                    rect = get_rect_for_pid(self._process.pid)
                    self._process.terminate()
                    self._launcher.set_relaunch(rect)
                    logger.info("restart the player")
