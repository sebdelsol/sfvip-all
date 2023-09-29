import threading
from pathlib import Path
from typing import Self

from ..app_info import AppConfig
from ..tools.scheduler import Scheduler
from ..ui import UI
from .libmpv_dll import LibmpvDll


class PlayerLibmpvAutoUpdater:
    def __init__(self, player_path: str, app_config: AppConfig, ui: UI) -> None:
        self._libmpv_dll = LibmpvDll(Path(player_path), app_config.Player.Libmpv.requests_timeout)
        self._is_installing = threading.Lock()
        self._is_checking = threading.Lock()
        self._scheduler = Scheduler(ui)
        self._app_config = app_config
        self._ui = ui

    def __enter__(self) -> Self:
        self._ui.set_libmpv_version(self._libmpv_dll.get_version())
        self._ui.set_libmpv_auto_update(self._app_config.Player.Libmpv.auto_update, self._on_auto_update_changed)
        return self

    def __exit__(self, *_) -> None:
        self._scheduler.cancel_all()

    def _on_auto_update_changed(self, auto_update: bool) -> None:
        self._app_config.Player.Libmpv.auto_update = auto_update
        self._scheduler.cancel_all()
        if auto_update:
            self._scheduler.next(self._check, 0)
        else:
            self._ui.set_libmpv_install()

    def _check(self, cancelled: threading.Event) -> None:
        if not (self._is_checking.locked() or self._is_installing.locked()):
            with self._is_checking:
                if libmpv := self._libmpv_dll.get_latest_libmpv():
                    if not cancelled.is_set():
                        if self._libmpv_dll.is_new(libmpv):

                            def install() -> None:
                                with self._is_installing:
                                    self._ui.set_libmpv_installing()
                                    if self._libmpv_dll.download_in_thread(libmpv):  # type: ignore
                                        self._ui.set_libmpv_version(version)
                                    else:
                                        self._ui.set_libmpv_install(version, install)

                            self._scheduler.cancel_all()
                            version = libmpv.get_version()
                            self._ui.set_libmpv_install(version, install)
                else:
                    if not cancelled.is_set():
                        self._scheduler.next(self._check, self._app_config.Player.Libmpv.retry_minutes * 60)
