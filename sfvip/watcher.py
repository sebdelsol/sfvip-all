import logging
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple, Optional, Self

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger(__name__)


class _Callback(NamedTuple):
    _CallbackT = Callable[..., None]
    func: _CallbackT
    args: tuple[Any]

    def __call__(self):
        self.func(*self.args)


class FileWatcher:
    def __init__(self, path: Optional[Path]) -> None:
        self._observer: Optional[BaseObserver] = None
        self._callbacks: set[_Callback] = set()
        self._path: Optional[Path] = None

        if path and path.is_file():
            self._path = path
            self._event_handler = PatternMatchingEventHandler(patterns=(path.name,))
            self._event_handler.on_modified = self._on_modified  # type: ignore
        self._started_time: float = float("inf")

    @property
    def started_time(self) -> float:
        return self._started_time

    def _on_modified(self, _):
        # debounce and avoid recursion if any callback modify the watched file
        if time.time() > self._started_time + 0.1:
            logger.info("watched file %s modified", self._path)
            for callback in self._callbacks:
                callback()
            if self._path:
                self._started_time = self._path.stat().st_atime

    def add_callback(self, callback: _Callback._CallbackT, *args: Any):
        self._callbacks.add(_Callback(callback, args))

    def start(self) -> None:
        if self._path:
            logger.info("watch on %s started", self._path)
            self._started_time = time.time()
            self._observer = Observer()
            self._observer.schedule(self._event_handler, self._path.parent, recursive=False)
            self._observer.start()

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._callbacks = set()
            logger.info("watch on %s stopped", self._path)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
