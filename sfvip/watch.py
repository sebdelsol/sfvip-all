import logging
import time
from pathlib import Path
from typing import Callable

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

CallbackT = Callable[[], None]


class WatchFile:
    def __init__(self, path: Path | None) -> None:
        self._observer = None
        self._callback: CallbackT | None
        if path:
            event_handler = PatternMatchingEventHandler(patterns=(path.name,))
            event_handler.on_modified = self._on_modified  # type: ignore
            self._observer = Observer()
            self._observer.schedule(event_handler, path.parent, recursive=False)
            logger.info("watch file: %s", path)
        self.started_time: float = float("inf")

    def _on_modified(self, _):
        if self._callback:
            self._callback()

    def set_callback(self, callback: CallbackT | None):
        self._callback = callback

    def start(self) -> None:
        if self._observer:
            self.started_time = time.time()
            self._observer.start()

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
