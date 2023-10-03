import logging
import os
import shutil
import sys
import threading
from functools import total_ordering
from pathlib import Path
from typing import Any, Callable, NamedTuple, Optional, Self

import requests

from .app_info import AppConfig, AppInfo
from .localization import LOC
from .tools.downloader import download_to, exceptions
from .tools.exe import compute_md5, is64_exe
from .tools.guardian import ThreadGuardian
from .tools.scheduler import Scheduler
from .ui import UI
from .ui.window import AskWindow, ProgressWindow

logger = logging.getLogger(__name__)


@total_ordering
class _Version:
    def __init__(self, version_str: Optional[str]) -> None:
        self._version = version_str or "0"
        try:
            self._tuple = tuple(map(int, (self._version.split("."))))
        except (TypeError, ValueError):
            self._tuple = (0,)

    def _to_len(self, n) -> tuple[int, ...]:
        return self._tuple + (0,) * (n - len(self._tuple))

    def __repr__(self) -> str:
        return self._version

    def __eq__(self, other: "_Version") -> bool:
        n = max(len(self._tuple), len(other._tuple))
        return self._to_len(n) == other._to_len(n)

    def __gt__(self, other: "_Version") -> bool:
        n = max(len(self._tuple), len(other._tuple))
        return self._to_len(n) > other._to_len(n)


class AppUpdate(NamedTuple):
    url: str
    md5: str
    version: str

    @classmethod
    def from_json(cls, json: Optional[Any]) -> Optional[Self]:
        try:
            if json:
                update = cls(**json)
                if all(isinstance(field, str) for field in update._fields):
                    return update
        except TypeError:
            pass
        return None


class AppLastestUpdate:
    def __init__(self, url: str) -> None:
        self._url = url

    def get(self, timeout: int) -> Optional[AppUpdate]:
        try:
            with requests.get(self._url, timeout=timeout) as response:
                response.raise_for_status()
                if update := AppUpdate.from_json(response.json()):
                    return update
        except requests.RequestException:
            pass
        return None


AltLastRegisterT = Callable[[Callable[[], None]], None]


class AppUpdater:
    old_exe = "old.exe"
    update_exe = "update.exe"

    def __init__(self, app_info: AppInfo, at_last_register: AltLastRegisterT) -> None:
        self._timeout = app_info.config.App.requests_timeout
        self._app_info = app_info
        self._at_last_register = at_last_register
        self._latest_update = AppLastestUpdate(app_info.update_url.format(bitness=app_info.bitness))

    def is_new(self, update: AppUpdate) -> bool:
        return _Version(update.version) > _Version(self._app_info.version)

    def get_update(self) -> Optional[AppUpdate]:
        logger.info("check lastest %s version", self._app_info.name)
        if update := self._latest_update.get(self._timeout):
            logger.info("found update %s %s %s", self._app_info.name, update.version, self._app_info.bitness)
            return update
        logger.warning("check latest %s failed", self._app_info.name)
        return None

    def _get_current_exe(self) -> Path:
        if "__compiled__" in globals():  # launched by nuitka ?
            # might have been called without its .exe extension
            return Path(sys.argv[0]).with_suffix(".exe")
        # for debug purpose only
        return Path(sys.argv[0]).parent / f"{self._app_info.name}.exe"

    def _is_a_valid_update(self, exe: Path, update: AppUpdate) -> bool:
        return exe.exists() and is64_exe(exe) == self._app_info.app_64bit and compute_md5(exe) == update.md5

    def _update_exe(self, update: AppUpdate) -> Path:
        update_suffix = f".{update.version}.{self._app_info.bitness}.{AppUpdater.update_exe}"
        return self._get_current_exe().with_suffix(update_suffix)

    def _install(self, update_exe: Path) -> None:
        current_exe = self._get_current_exe()
        if current_exe.exists():
            old_suffix = f".{self._app_info.version}.{self._app_info.bitness}.{AppUpdater.old_exe}"
            old_exe = current_exe.with_suffix(old_suffix)
            old_exe.unlink(missing_ok=True)
            current_exe.rename(old_exe)
        shutil.copy(update_exe, current_exe)

        # replace current process with the current exe
        def launch() -> None:
            current_exe_str = f"'{str(current_exe.resolve())}'"
            logger.info("launch %s", current_exe_str)
            os.execl(current_exe, current_exe_str)

        # register to be launched after all the cleanup
        self._at_last_register(launch)

    def download_available(self, update: AppUpdate) -> bool:
        update_exe = self._update_exe(update)
        return self._is_a_valid_update(update_exe, update)

    def download(self, update: AppUpdate) -> bool:
        def _download() -> bool:
            if download_to(update.url, update_exe, self._timeout, progress):
                if self._is_a_valid_update(update_exe, update):
                    return True
            return False

        update_exe = self._update_exe(update)
        update_exe.unlink(missing_ok=True)
        progress = ProgressWindow(f"{LOC.Download} {self._app_info.name}")
        if progress.run_in_thread(_download, *exceptions):
            return True
        update_exe.unlink(missing_ok=True)
        return False

    def install(self, update: AppUpdate) -> bool:
        def ask_and_install() -> bool:
            ask_win.wait_window()
            if ask_win.ok:
                logger.info("install %s", update_exe.name)
                self._install(update_exe)
            return bool(ask_win.ok)

        update_exe = self._update_exe(update)
        title = f"{LOC.Install} {self._app_info.name}"
        ask_win = AskWindow(title, LOC.RestartInstall % f"v{update.version}", LOC.Restart, LOC.Cancel)
        return bool(ask_win.run_in_thread(ask_and_install, *exceptions))


# prevent execution if already in use in another thread
_updating = ThreadGuardian()


class AppAutoUpdater:
    def __init__(
        self, app_updater: AppUpdater, config: AppConfig, ui: UI, stop_player: Callable[[], bool]
    ) -> None:
        self._app_updater = app_updater
        self._stop_player = stop_player
        self._scheduler = Scheduler()
        self._config = config
        self._ui = ui

    def __enter__(self) -> Self:
        self._ui.set_app_auto_update(self._config.App.auto_update, self._on_auto_update_changed)
        return self

    def __exit__(self, *_) -> None:
        self._scheduler.cancel_all()

    def _on_auto_update_changed(self, auto_update: bool) -> None:
        self._config.App.auto_update = auto_update
        self._scheduler.cancel_all()
        if auto_update:
            self._scheduler.next(self._check, 0)
        else:
            self._ui.set_app_update()

    @_updating
    def _check(self, cancelled: threading.Event) -> None:
        update = self._app_updater.get_update()
        if not cancelled.is_set():
            self._scheduler.cancel_all()
            if update:
                if self._app_updater.is_new(update):

                    @_updating
                    def install() -> None:
                        assert update
                        self._ui.set_app_updating()
                        if self._app_updater.download_available(update):
                            if self._app_updater.install(update):
                                self._stop_player()
                            else:
                                self._ui.set_app_update(LOC.Install, install, update.version)
                        else:
                            download()

                    @_updating
                    def download() -> None:
                        assert update
                        self._ui.set_app_updating()
                        if self._app_updater.download(update):
                            install()
                        else:
                            self._ui.set_app_update(LOC.Download, download, update.version)

                    if self._app_updater.download_available(update):
                        self._ui.set_app_update(LOC.Install, install, update.version)
                    else:
                        self._ui.set_app_update(LOC.Download, download, update.version)
            else:
                # reschedule only if we can't get an update
                if not cancelled.is_set():
                    self._scheduler.next(self._check, self._config.App.retry_minutes * 60)
