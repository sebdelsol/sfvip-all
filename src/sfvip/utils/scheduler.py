import threading
from typing import Callable, NamedTuple


class _Next(NamedTuple):
    cancelled: threading.Event
    timer: threading.Timer


class Scheduler:
    def __init__(self) -> None:
        self._scheduled: list[_Next] = []
        self._scheduled_lock = threading.Lock()

    def cancel_all(self) -> None:
        with self._scheduled_lock:
            for scheduled in self._scheduled:
                scheduled.timer.cancel()
                scheduled.cancelled.set()
            self._scheduled = []

    def next(self, action: Callable[[threading.Event], None], delay_s: int) -> None:
        with self._scheduled_lock:
            cancelled = threading.Event()
            timer = threading.Timer(delay_s, action, args=(cancelled,))
            self._scheduled.append(_Next(cancelled, timer))
            timer.start()
