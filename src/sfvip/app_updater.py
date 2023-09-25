import logging
import os
import shutil
import sys
import tempfile
import threading
from functools import total_ordering
from pathlib import Path
from typing import Any, Callable, NamedTuple, Optional, Self

import requests

from .app_config import Config
from .app_info import AppInfo
from .downloader import download_in_thread, download_to
from .exe_tools import compute_md5, is64_exe
from .scheduler import Scheduler
from .ui import UI
from .ui.progress import ProgressWindow

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
    def __init__(self, app_info: AppInfo, timeout: int, at_last_register: AltLastRegisterT) -> None:
        self._timeout = timeout
        self._app_info = app_info
        self._at_last_register = at_last_register
        self._latest_update = AppLastestUpdate(app_info.update_url.format(bitness=app_info.bitness))

    def is_new(self, update: AppUpdate) -> bool:
        return _Version(update.version) > _Version(self._app_info.version)

    def get_update(self) -> Optional[AppUpdate]:
        logger.info("check lastest %s version", self._app_info.name)
        if update := self._latest_update.get(self._timeout):
            logger.info("%s %s found", self._app_info.name, update.version)
            return update
        logger.warning("check latest %s failed", self._app_info.name)
        return None

    def _download(self, update: AppUpdate, progress: ProgressWindow) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            temp_exe = temp_dir / f"{self._app_info.name} v{update.version} {self._app_info.bitness}"
            if download_to(update.url, temp_exe, self._timeout, progress):
                if is64_exe(temp_exe) == self._app_info.app_64bit:
                    if compute_md5(temp_exe) == update.md5:
                        if not progress.destroyed:
                            logger.info("install %s", temp_exe.name)
                            self._install(temp_exe)
                            return True
            return False

    def _install(self, updated_exe: Path) -> None:
        if "__compiled__" in globals():  # launched by nuitka ?
            # might have been called without its .exe extension
            current_exe = Path(sys.argv[0]).with_suffix(".exe")
        else:  # for debug purpose only
            current_exe = Path(sys.argv[0]).parent / f"{self._app_info.name}.exe"
        if current_exe.exists():
            old = current_exe.with_suffix(f".{self._app_info.version}.{self._app_info.bitness}.old.exe")
            old.unlink(missing_ok=True)
            current_exe.rename(old)
        shutil.copy(updated_exe, current_exe)

        # replace current process with the current exe
        def launch() -> None:
            current_exe_str = f"'{str(current_exe.resolve())}'"
            logger.info("launch %s", current_exe_str)
            os.execl(current_exe, current_exe_str)

        # register to be launched after all the cleanup
        self._at_last_register(launch)

    def download_in_thread(self, update: AppUpdate) -> bool:
        def download(progress: ProgressWindow) -> bool:
            return self._download(update, progress)

        if download_in_thread(f"Update {self._app_info.name}", download, create_mainloop=False):
            return True
        return False


class AppAutoUpdater:
    def __init__(self, app_updater: AppUpdater, config: Config, ui: UI, stop_player: Callable[[], bool]) -> None:
        self._app_updater = app_updater
        self._is_installing = threading.Lock()
        self._is_checking = threading.Lock()
        self._stop_player = stop_player
        self._scheduler = Scheduler(ui)
        self._config = config
        self._ui = ui

    def __enter__(self) -> Self:
        self._ui.set_app_auto_update(self._config.app_auto_update, self._on_auto_update_changed)
        return self

    def __exit__(self, *_) -> None:
        self._scheduler.cancel_all()

    def _on_auto_update_changed(self, auto_update: bool) -> None:
        self._config.app_auto_update = auto_update
        self._scheduler.cancel_all()
        if auto_update:
            self._scheduler.next(self._check, 0)
        else:
            self._ui.set_app_install()

    def _check(self, cancelled: threading.Event) -> None:
        if not (self._is_checking.locked() or self._is_installing.locked()):
            with self._is_checking:
                if update := self._app_updater.get_update():
                    if not cancelled.is_set():
                        if self._app_updater.is_new(update):

                            def install() -> None:
                                with self._is_installing:
                                    assert update
                                    self._ui.set_app_installing()
                                    if self._app_updater.download_in_thread(update):
                                        self._stop_player()
                                    else:
                                        self._ui.set_app_install(update.version, install)

                            self._scheduler.cancel_all()
                            self._ui.set_app_install(update.version, install)
                else:
                    # reschedule only if we can't get an update
                    if not cancelled.is_set():
                        self._scheduler.next(self._check, self._config.app_retry_minutes * 60)
