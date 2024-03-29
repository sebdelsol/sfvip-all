import logging
import queue
import threading
from enum import Enum, auto
from typing import Callable

from shared.job_runner import JobRunner

from ..mitm.cache import CacheProgress, CacheProgressEvent, UpdateCacheProgressT
from .ui import UI

logger = logging.getLogger(__name__)


class WatchdogState(Enum):
    STOPPED = auto()
    ARMED = auto()
    DISARMED = auto()


class TimeoutWatchdog:
    def __init__(self, timeout: float, callback: Callable[[], None]) -> None:
        self._activity: queue.Queue[WatchdogState] = queue.Queue()
        self._thread = threading.Thread(target=self._watch)
        self._callback = callback
        self._timeout = timeout

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._activity.put(WatchdogState.STOPPED)
        self._thread.join()

    def ping(self) -> None:
        self._activity.put(WatchdogState.ARMED)

    def disarm(self) -> None:
        self._activity.put(WatchdogState.DISARMED)

    def _watch(self) -> None:
        state = WatchdogState.DISARMED
        while True:
            try:
                timeout = None if state == WatchdogState.DISARMED else self._timeout
                state = self._activity.get(timeout=timeout)
                if state == WatchdogState.STOPPED:
                    break
            except queue.Empty:  # timeout
                if state == WatchdogState.ARMED:
                    state = WatchdogState.DISARMED
                    self._callback()


class CacheProgressListener:
    _timeout = 4  # seconds without progress

    def __init__(self, ui: UI, stop_all: Callable[[], None]) -> None:
        self._cache_progress_job_runner = JobRunner[CacheProgress](self._on_progress_changed, "Cache progress job")
        self._watchdog = TimeoutWatchdog(self._timeout, self._no_progress_timeout)
        self._stop_all = stop_all
        self._ui = ui

    @property
    def update_progress(self) -> UpdateCacheProgressT:
        return self._cache_progress_job_runner.add_job

    def start(self) -> None:
        self._watchdog.start()
        self._cache_progress_job_runner.start()

    def stop(self) -> None:
        self._watchdog.stop()
        self._cache_progress_job_runner.stop()
        self._ui.progress_bar.hide()

    def _no_progress_timeout(self) -> None:
        logger.info("Cache Progress timeout")
        self._ui.progress_bar.hide()
        self._stop_all()

    def _on_progress_changed(self, cache_progress: CacheProgress) -> None:
        match cache_progress.event:
            case CacheProgressEvent.START:
                # self._watchdog.ping() # TODO ??!
                self._ui.progress_bar.show()
            case CacheProgressEvent.SHOW:
                self._watchdog.ping()
                self._ui.progress_bar.set_progress(cache_progress.progress)
            case CacheProgressEvent.STOP:
                self._watchdog.disarm()
                self._ui.progress_bar.hide()
