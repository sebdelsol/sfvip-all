import threading
from pathlib import Path
from typing import Callable, Self

from ..app_info import AppConfig
from ..localization import LOC
from ..ui import UI
from ..utils.guardian import ThreadGuardian
from ..utils.scheduler import Scheduler
from .libmpv_dll import LibmpvDll

# prevent execution if already in use in another thread
_updating = ThreadGuardian()


class PlayerLibmpvAutoUpdater:
    def __init__(
        self, player_path: str, app_config: AppConfig, ui: UI, relaunch_player: Callable[[int], None]
    ) -> None:
        self._libmpv_dll = LibmpvDll(Path(player_path), app_config.Player.Libmpv.requests_timeout)
        self._relaunch_player = relaunch_player
        self._installed_version = None
        self._scheduler = Scheduler()
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
            self._ui.set_libmpv_update()

    @_updating
    def _check(self, cancelled: threading.Event) -> None:
        libmpv = self._libmpv_dll.get_latest_libmpv()
        if not cancelled.is_set():
            self._scheduler.cancel_all()
            if libmpv:
                version = libmpv.get_version()

                @_updating
                def install() -> None:
                    self._ui.set_libmpv_updating()
                    if self._libmpv_dll.ask_restart():
                        self._installed_version = None
                        self._relaunch_player(0)
                    else:
                        self._installed_version = version
                        self._ui.set_libmpv_update(LOC.Install, install, version)

                @_updating
                def download() -> None:
                    assert libmpv
                    self._ui.set_libmpv_updating()
                    if self._libmpv_dll.download(libmpv):
                        install()
                    else:
                        self._ui.set_libmpv_update(LOC.Download, download, version)

                if self._libmpv_dll.is_new(libmpv):
                    self._ui.set_libmpv_update(LOC.Download, download, version)
                elif self._installed_version == version:
                    self._ui.set_libmpv_update(LOC.Install, install, version)
            else:
                self._scheduler.next(self._check, self._app_config.Player.Libmpv.retry_minutes * 60)
