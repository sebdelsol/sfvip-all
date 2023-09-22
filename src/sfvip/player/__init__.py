import logging
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, Optional, Self

from ...winapi import mutex
from ..config import Config
from ..ui import UI, sticky
from ..update import download_player
from ..update.libmpv import LibmpvDll
from ..watchers import RegistryWatcher, WindowWatcher
from .config import PlayerConfig, PlayerConfigDirSettingWatcher
from .exception import PlayerError
from .registry import player_from_registry

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

    def __init__(self, config: Config, ui: UI) -> None:
        player = config.player_path
        if not self._valid_exe(player):
            player = self._find_player(ui)
        assert player
        self.path = config.player_path = player
        logger.info("player is '%s'", self.path)

    def _find_player(self, ui: UI) -> str:
        for find_player_method in (
            self._player_from_registry,
            self._player_from_user,
            self._player_from_download,
        ):
            for player in find_player_method(ui):
                if self._valid_exe(player):
                    return player
        raise PlayerError("Sfvip Player not found")

    @staticmethod
    def _valid_exe(path: Optional[Path | str]) -> bool:
        return bool(path and (_path := Path(path)).is_file() and _path.match(_PlayerPath._pattern))

    @staticmethod
    def _player_from_registry(_) -> Iterator[str]:
        logger.info("try to find the player in the registry")
        for player in player_from_registry(_PlayerPath._name):
            yield player

    # TODO single window for both _player_from_user and _player_from_download
    @staticmethod
    def _player_from_user(ui: UI) -> Iterator[str]:
        ui.showinfo(f"Please find {_PlayerPath._name.capitalize()}")
        while True:
            logger.info("ask the user to find the player")
            if player := ui.find_file(_PlayerPath._name, _PlayerPath._pattern):
                yield player
            if not ui.askretry(message=f"{_PlayerPath._name.capitalize()} not found, try again ?"):
                break

    @staticmethod
    def _player_from_download(ui: UI) -> Iterator[str]:
        if ui.askyesno(message=f"Download {_PlayerPath._name.capitalize()} ?"):
            logger.info("try to download the player")
            if player := download_player(_PlayerPath._name):
                yield player


class _PlayerRectLoader(PlayerConfig):
    """load & save the player's window position"""

    _maximized_key = "IsMaximized"
    _keys = "Left", "Top", "Width", "Height", _maximized_key

    @property
    def rect(self) -> sticky.Rect:
        if config := self.load():
            return sticky.Rect(*(config[key] for key in _PlayerRectLoader._keys))
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
        self._watcher.set_callback(sticky.StickyWindows.on_state_changed)
        self._watcher.start()

    def stop(self) -> None:
        if self._watcher:
            self._watcher.stop()
            sticky.StickyWindows.withdraw_all()

    @property
    def rect(self) -> Optional[sticky.Rect]:
        return sticky.StickyWindows.get_rect()


class _Scheduled(NamedTuple):
    cancelled: threading.Event
    after: str


class _PlayerLibmpvAutoUpdate:
    _reschedule_delay_s = 10 * 60

    def __init__(self, player_path: str, config: Config, ui: UI) -> None:
        self._libmpv_dll = LibmpvDll(Path(player_path))
        self._scheduled: list[_Scheduled] = []
        self._scheduled_lock = threading.Lock()
        self._is_downloading = threading.Lock()
        self._is_checking = threading.Lock()
        self._config = config
        self._ui = ui

    def __enter__(self) -> Self:
        self._ui.set_libmpv_version(self._libmpv_dll.get_version())
        self._ui.set_libmpv_auto_update(self._config.auto_update_libmpv, self._on_auto_update_changed)
        return self

    def __exit__(self, *_) -> None:
        self._cancel_scheduled_checks()

    def _cancel_scheduled_checks(self) -> None:
        with self._scheduled_lock:
            for scheduled in self._scheduled:
                self._ui.after_cancel(scheduled.after)
                scheduled.cancelled.set()
            self._scheduled = []

    def _schedule_check(self, delay_s: int) -> None:
        def check() -> None:
            threading.Thread(target=self._check, args=(cancelled,), daemon=True).start()

        with self._scheduled_lock:
            cancelled = threading.Event()
            after = self._ui.after(delay_s * 1000, check)
            self._scheduled.append(_Scheduled(cancelled, after))

    def _on_auto_update_changed(self, auto_update: bool) -> None:
        self._config.auto_update_libmpv = auto_update
        self._cancel_scheduled_checks()
        if auto_update:
            self._schedule_check(0)

    def _check(self, cancelled: threading.Event) -> None:
        if not (self._is_checking.locked() or self._is_downloading.locked()):
            with self._is_checking:
                if libmpv := self._libmpv_dll.check():
                    if not cancelled.is_set():

                        def download() -> None:
                            with self._is_downloading:
                                self._ui.set_libmpv_downloading()
                                if libmpv:
                                    if self._libmpv_dll.download_in_thread(libmpv):
                                        self._ui.set_libmpv_version(version)
                                    else:
                                        self._ui.set_libmpv_download(version, download)

                        self._cancel_scheduled_checks()
                        version = libmpv.get_version()
                        self._ui.set_libmpv_download(version, download)
                else:
                    if not cancelled.is_set():
                        self._schedule_check(_PlayerLibmpvAutoUpdate._reschedule_delay_s)


class _Launcher:
    """handle player's relaunch"""

    def __init__(self) -> None:
        self._launch = True
        self._rect: Optional[sticky.Rect] = None

    def want_to_launch(self) -> bool:
        launch = self._launch
        # won't launch next time except if explitcitly set
        self._launch = False
        return launch

    def set_relaunch(self, rect: Optional[sticky.Rect]) -> None:
        self._launch = True
        self._rect = rect

    @property
    def rect(self) -> Optional[sticky.Rect]:
        if self._rect and self._rect.valid():
            return self._rect
        return None


class Player:
    """run the player"""

    def __init__(self, config: Config, ui: UI) -> None:
        self.path = _PlayerPath(config, ui).path
        self._libmpv = _PlayerLibmpvAutoUpdate(self.path, config, ui)
        self._window_watcher = _PlayerWindowWatcher()
        self._rect_loader: Optional[_PlayerRectLoader] = None
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._launcher = _Launcher()

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
        assert self.path is not None
        assert self._rect_loader is not None

        set_rect_lock = None
        if self._launcher.rect:
            # prevent another instance of sfvip to run
            # before the player position has been set
            set_rect_lock = mutex.SystemWideMutex("set player rect lock")
            set_rect_lock.acquire()
            self._rect_loader.rect = self._launcher.rect

        with self._libmpv:
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
