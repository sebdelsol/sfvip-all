import threading
from typing import Callable, NamedTuple

from ..ui import UI


class _Next(NamedTuple):
    cancelled: threading.Event
    after: str


class Scheduler:
    def __init__(self, ui: UI) -> None:
        self._scheduled: list[_Next] = []
        self._scheduled_lock = threading.Lock()
        self._ui = ui

    def cancel_all(self) -> None:
        with self._scheduled_lock:
            for scheduled in self._scheduled:
                self._ui.after_cancel(scheduled.after)
                scheduled.cancelled.set()
            self._scheduled = []

    def next(self, func: Callable[[threading.Event], None], delay_s: int) -> None:
        def check() -> None:
            threading.Thread(target=func, args=(cancelled,), daemon=True).start()

        with self._scheduled_lock:
            cancelled = threading.Event()
            after = self._ui.after(delay_s * 1000, check)
            self._scheduled.append(_Next(cancelled, after))
