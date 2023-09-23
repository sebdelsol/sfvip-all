import threading
from pathlib import Path
from typing import NamedTuple, Self

from ..config import Config
from ..ui import UI
from ..update.libmpv import LibmpvDll


class _Scheduled(NamedTuple):
    cancelled: threading.Event
    after: str


class PlayerLibmpvAutoUpdate:
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
        self._ui.set_libmpv_auto_update(self._config.libmpv_auto_update, self._on_auto_update_changed)
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
        self._config.libmpv_auto_update = auto_update
        self._cancel_scheduled_checks()
        if auto_update:
            self._schedule_check(0)

    def _check(self, cancelled: threading.Event) -> None:
        if not (self._is_checking.locked() or self._is_downloading.locked()):
            with self._is_checking:
                if libmpv := self._libmpv_dll.get_latest_libmpv():
                    if not cancelled.is_set():
                        if self._libmpv_dll.is_new(libmpv):

                            def download() -> None:
                                with self._is_downloading:
                                    self._ui.set_libmpv_downloading()
                                    if self._libmpv_dll.download_in_thread(libmpv):  # type: ignore
                                        self._ui.set_libmpv_version(version)
                                    else:
                                        self._ui.set_libmpv_download(version, download)

                            self._cancel_scheduled_checks()
                            version = libmpv.get_version()
                            self._ui.set_libmpv_download(version, download)
                else:
                    if not cancelled.is_set():
                        self._schedule_check(self._config.libmpv_retry_minutes * 60)
