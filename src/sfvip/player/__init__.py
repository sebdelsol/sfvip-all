import logging
import subprocess
import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

from ...winapi import mutex
from ..app_info import AppInfo
from ..ui import UI, sticky
from ..watchers import RegistryWatcher, WindowWatcher
from .config import PlayerConfig, PlayerConfigDirSettingWatcher
from .find_exe import PlayerCapabilities, PlayerExe
from .libmpv_updater import PlayerLibmpvAutoUpdater
from .updater import PlayerAutoUpdater

logger = logging.getLogger(__name__)


class _PlayerConfigDirSetting(PlayerConfigDirSettingWatcher):
    """watch for a change of the player config dir setting"""

    def _on_modified(self, value: str, player_relaunch: Callable[[], None]) -> None:
        logger.info("Player config dir has changed to %s", value)
        self.has_changed()  # clear the relevant caches
        player_relaunch()

    def watch(self, player_relaunch: Callable[[], None]) -> RegistryWatcher:
        self._watcher.add_callback(self._on_modified, player_relaunch)
        return self._watcher


class PlayerLanguageLoader(PlayerConfig):
    language_key = "Language"

    @property
    def language(self) -> Optional[str]:
        if config := self.load():
            try:
                return config[PlayerLanguageLoader.language_key]
            except KeyError:
                pass
        return None


class _PlayerRectLoader(PlayerConfig):
    """load & save the player's window position"""

    _maximized_key = "IsMaximized"
    _keys = "Left", "Top", "Width", "Height", _maximized_key

    @property
    def rect(self) -> sticky.Rect:
        if config := self.load():
            try:
                return sticky.Rect(*(config[key] for key in _PlayerRectLoader._keys))
            except KeyError:
                return sticky.Rect(0, 0, 0, 0, True)
        return sticky.Rect()

    @rect.setter
    def rect(self, rect: sticky.Rect) -> None:
        if rect.valid():
            if config := self.load():
                if rect.is_maximized:
                    # do not write the rect coords since it's only meant for non maximized window
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
        sticky.sticky_windows.set_followed_pid(pid)
        self._watcher.set_callback(sticky.sticky_windows.on_state_changed)
        self._watcher.start()

    def stop(self) -> None:
        if self._watcher:
            self._watcher.stop()
            sticky.sticky_windows.withdraw_all()

    @property
    def rect(self) -> Optional[sticky.Rect]:
        return sticky.sticky_windows.get_rect()


class _Launcher:
    """handle player's relaunch"""

    def __init__(self) -> None:
        self._launch = True
        self._rect: Optional[sticky.Rect] = None
        self._can_relaunch: Optional[threading.Event] = None

    def want_to_launch(self) -> bool:
        if launch := self._launch:
            if self._can_relaunch is not None:
                self._can_relaunch.wait()
        # won't launch next time except if explitcitly set
        self._launch = False
        self._can_relaunch = None
        return launch

    def set_relaunch(self, rect: Optional[sticky.Rect], can_relaunch: Optional[threading.Event] = None) -> None:
        self._launch = True
        self._can_relaunch = can_relaunch
        self._rect = rect

    @property
    def rect(self) -> Optional[sticky.Rect]:
        if self._rect and self._rect.valid():
            return self._rect
        return None


class Player:
    """run the player"""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, app_info: AppInfo, ui: UI) -> None:
        self._player_exe = PlayerExe(app_info, ui)
        self._libmpv_updater = PlayerLibmpvAutoUpdater(self._player_exe.exe, app_info.config, ui, self.relaunch)
        self._player_updater = PlayerAutoUpdater(self._player_exe, app_info, ui, self.relaunch)
        self._window_watcher = _PlayerWindowWatcher()
        self._rect_loader = _PlayerRectLoader()
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._launcher = _Launcher()

    @property
    def capabilities(self) -> PlayerCapabilities:
        return self._player_exe.capabilities

    def want_to_launch(self) -> bool:
        if self._launcher.want_to_launch():
            self._rect_loader = _PlayerRectLoader()
            return True
        return False

    @property
    def rect(self) -> sticky.Rect:
        if self._launcher.rect:
            return self._launcher.rect
        assert self._rect_loader is not None
        return self._rect_loader.rect

    @contextmanager
    def run(self) -> Iterator[None]:
        assert self._rect_loader is not None

        set_rect_lock = None
        if self._launcher.rect:
            # prevent another instance of sfvip to run
            # before the player position has been set
            set_rect_lock = mutex.SystemWideMutex("set player rect lock")
            set_rect_lock.acquire()
            self._rect_loader.rect = self._launcher.rect

        with self._player_updater:
            with self._libmpv_updater:
                with _PlayerConfigDirSetting().watch(self.relaunch):
                    with subprocess.Popen([self._player_exe.exe]) as self._process:
                        logger.info("Player started")
                        self._window_watcher.start(self._process.pid)
                        if set_rect_lock:
                            # give time to the player to read its config
                            time.sleep(0.5)
                            set_rect_lock.release()
                        yield
                    with self._process_lock:
                        self._process = None
                    logger.info("Player stopped")
                    # at the end since tk might lock because relaunch could be called in the same thread
                    self._window_watcher.stop()

    def stop(self) -> bool:
        with self._process_lock:
            if self._process:
                if self._process.poll() is None:  # still running ?
                    logger.info("Stopping the player")
                    self._process.terminate()
                    return True
        return False

    def relaunch(self, sleep_duration_s: float = 1, can_relaunch: Optional[threading.Event] = None) -> None:
        # give time to the player to stop if it's been initiated by the user
        time.sleep(sleep_duration_s)
        if self.stop():
            self._launcher.set_relaunch(self._window_watcher.rect, can_relaunch)
            logger.info("Restart the player")
            # wait for the player to stop
            while self._process:
                time.sleep(0)
