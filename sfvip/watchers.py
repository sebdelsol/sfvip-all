import logging
import threading
import time
import winreg
from pathlib import Path
from typing import Any, Callable, Concatenate, NamedTuple, Optional, ParamSpec, Self

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from winapi import wait_for_registry_change

logger = logging.getLogger(__name__)


FileWatcherCallbackFunc = Callable[..., None]


class _CallbackFileWatcher(NamedTuple):
    func: FileWatcherCallbackFunc
    args: tuple[Any]

    def __call__(self) -> None:
        self.func(*self.args)


class FileWatcher:
    _debounce_ms = 100

    def __init__(self, path: Optional[Path]) -> None:
        self._observer: Optional[BaseObserver] = None
        self._callbacks: set[_CallbackFileWatcher] = set()
        self._path: Optional[Path] = None

        if path and path.is_file():
            self._path = path
            self._event_handler = PatternMatchingEventHandler(patterns=(path.name,))
            self._event_handler.on_modified = self._on_modified  # type: ignore
        self._modified_time: float = float("inf")

    @property
    def modified_time(self) -> float:
        return self._modified_time

    def _on_modified(self, _):
        # debounce and avoid recursion if any callback modify the watched file
        assert self._path
        if time.time() > self._modified_time + FileWatcher._debounce_ms * 0.001:
            logger.info("watched file %s modified", self._path)
            for callback in self._callbacks:
                callback()
            self._modified_time = self._path.stat().st_mtime

    def add_callback(self, callback: FileWatcherCallbackFunc, *args: Any):
        self._callbacks.add(_CallbackFileWatcher(callback, args))

    def start(self) -> None:
        if self._path:
            logger.info("watch started on %s", self._path)
            self._modified_time = time.time()
            self._observer = Observer()
            self._observer.schedule(self._event_handler, self._path.parent, recursive=False)
            self._observer.start()

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._callbacks = set()
            logger.info("watch stopped on %s", self._path)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()


P = ParamSpec("P")
RegWatcherCallbackFunc = Callable[Concatenate[str, P], None]


class _CallbackRegWatcher(NamedTuple):
    func: RegWatcherCallbackFunc
    args: tuple[Any]

    def __call__(self, value: str) -> None:
        self.func(value, *self.args)


class RegistryWatcher:
    _timeout_ms = 100

    def __init__(self, hkey: int, path: str, name: str) -> None:
        self._hkey = hkey
        self._path = path
        self._name = name
        with winreg.OpenKey(hkey, path) as key:
            self._current_value = winreg.QueryValueEx(key, name)
        self._thread: Optional[threading.Thread] = None
        self._running: threading.Event = threading.Event()
        self._callback: Optional[_CallbackRegWatcher] = None

    def set_callback(self, callback: RegWatcherCallbackFunc, *args: Any):
        self._callback = _CallbackRegWatcher(callback, args)

    def start(self):
        logger.info(r"watch started on regkey %s\%s", self._path, self._name)
        self._thread = threading.Thread(target=self._wait_for_change)
        self._running.set()
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            logger.info(r"watch stopped on regkey %s\%s", self._path, self._name)
            self._running.clear()
            self._thread.join()
            self._thread = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    def _wait_for_change(self) -> None:
        with winreg.OpenKey(self._hkey, self._path) as key:
            for change in wait_for_registry_change(key.handle, RegistryWatcher._timeout_ms, self._running):  # type: ignore
                if change:
                    value, _ = winreg.QueryValueEx(key, self._name)
                    if value != self._current_value:
                        self._current_value = value
                        if self._callback:
                            self._callback(value)
