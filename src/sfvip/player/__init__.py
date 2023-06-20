import logging
import os
import subprocess
import threading
import time
import winreg
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional

from ...winapi import mutex
from ..registry import Registry
from ..ui import UI, Rect, WinState, sticky
from ..watchers import RegistryWatcher, WindowWatcher
from .config import PlayerConfig, PlayerConfigDirSettingWatcher
from .exception import PlayerError

logger = logging.getLogger(__name__)


class _PlayerConfigDirSetting(PlayerConfigDirSettingWatcher):
    """watch for a change of the player config dir setting"""

    def _on_modified(self, value: str, player_relaunch: Callable[[], None]) -> None:
        logger.info("Player config dir has changed to %s", value)
        self.has_changed()  # clear the relevant caches
        player_relaunch()

    def watch(self, player_relaunch: Callable[[], None]) -> RegistryWatcher:
        assert self._watcher is not None
        self._watcher.add_callback(self._on_modified, player_relaunch)
        return self._watcher


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


class _PlayerRectLoader(PlayerConfig):
    """load & save the player's window position"""

    _maximized_key = "IsMaximized"
    _keys = "Left", "Top", "Width", "Height", _maximized_key

    @property
    def rect(self) -> Rect:
        if config := self.load():
            return Rect(*(config[key] for key in _PlayerRectLoader._keys))
        return Rect()

    @rect.setter
    def rect(self, rect: Rect) -> None:
        if rect.valid():
            if config := self.load():
                if rect.is_maximized:
                    # do not write the rect coords
                    # since it's only meant for non maximized window
                    config[_PlayerRectLoader._maximized_key] = True
                else:
                    for key, value in zip(_PlayerRectLoader._keys, rect):
                        config[key] = value
                self.save(config)


class _PlayerWindowWatcher:
    def __init__(self) -> None:
        self._watcher: Optional[WindowWatcher] = None

    def start(self, pid: int) -> None:
        self._watcher = WindowWatcher(pid)
        self._watcher.set_callback(sticky.StickyWindows.on_state_changed)
        self._watcher.start()

    def stop(self) -> None:
        if self._watcher:
            sticky.StickyWindows.hide_all()
            self._watcher.stop()

    @property
    def rect(self) -> Optional[Rect]:
        return sticky.StickyWindows.get_rect()


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

    def set_relaunch(self, rect: Optional[Rect]) -> None:
        self._launch = True
        self._rect = rect

    @property
    def rect(self) -> Optional[Rect]:
        if self._rect and self._rect.valid():
            return self._rect
        return None


class Player:
    """run the player"""

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        self.path = _PlayerPath(player_path, ui).path
        self._window_watcher = _PlayerWindowWatcher()
        self._rect_loader: Optional[_PlayerRectLoader] = None
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._launcher = _Launcher()

    def want_to_launch(self) -> bool:
        launch = self._launcher.want_to_launch()
        if launch:
            self._rect_loader = _PlayerRectLoader()
        return launch

    @property
    def rect(self) -> Rect:
        if self._launcher.rect:
            return self._launcher.rect
        assert self._rect_loader is not None
        return self._rect_loader.rect

    @contextmanager
    def run(self) -> Iterator[None]:
        assert self.path is not None
        assert self._rect_loader is not None

        set_rect_lock = None
        if self._launcher.rect:
            # prevent another instance of sfvip to run
            # before the player position has been set
            set_rect_lock = mutex.SystemWideMutex("set player rect lock")
            set_rect_lock.acquire()
            self._rect_loader.rect = self._launcher.rect

        with _PlayerConfigDirSetting().watch(self.relaunch):
            with subprocess.Popen([self.path]) as self._process:
                logger.info("player started")
                self._window_watcher.start(self._process.pid)
                if set_rect_lock:
                    # give time to the player to read its config
                    time.sleep(0.5)
                    set_rect_lock.release()
                yield
            with self._process_lock:
                self._process = None
            logger.info("player stopped")
            self._window_watcher.stop()

    def stop(self) -> bool:
        with self._process_lock:
            if self._process:
                if self._process.poll() is None:  # still running ?
                    self._process.terminate()
                    return True
        return False

    def relaunch(self, sleep_duration_s: float = 1) -> None:
        # give time to the player to stop if it's been initiated by the user
        time.sleep(sleep_duration_s)
        if self.stop():
            self._launcher.set_relaunch(self._window_watcher.rect)
            logger.info("restart the player")
