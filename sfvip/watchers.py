import logging
import threading
import time
import winreg
from abc import abstractmethod
from pathlib import Path
from typing import Any, Callable, Concatenate, NamedTuple, Optional, ParamSpec, Self

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from winapi import wait_for_registry_change

logger = logging.getLogger(__name__)


class StartStopContextManager:
    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...


ANY_PARAMETERS = ParamSpec("ANY_PARAMETERS")


class _CallbackFileWatcher(NamedTuple):
    _FileWatcherCallbackFunc = Callable[Concatenate[float, ANY_PARAMETERS], None]

    func: _FileWatcherCallbackFunc
    args: tuple[Any]

    def __call__(self, last_modified: float) -> None:
        self.func(last_modified, *self.args)


class FileWatcher(StartStopContextManager):
    _debounce_s = 0.1

    def __init__(self, path: Optional[Path]) -> None:
        self._observer: Optional[BaseObserver] = None
        self._callbacks: set[_CallbackFileWatcher] = set()
        self._path: Optional[Path] = path if path and path.is_file() else None
        self._last_modified: float = float("inf")

    def _on_modified(self, event: FileSystemEvent) -> None:
        assert self._path
        if event.src_path == str(self._path):
            # debounce
            if time.time() > self._last_modified + FileWatcher._debounce_s:
                logger.info("watched file %s modified", self._path)
                for callback in self._callbacks:
                    callback(self._last_modified)
            self._last_modified = self._path.stat().st_mtime

    def add_callback(self, callback: _CallbackFileWatcher._FileWatcherCallbackFunc, *args: Any) -> None:
        self._callbacks.add(_CallbackFileWatcher(callback, args))

    def start(self) -> None:
        if self._path:
            self._last_modified = self._path.stat().st_mtime
            self._observer = Observer()
            event_handler = FileSystemEventHandler()
            event_handler.on_modified = self._on_modified
            self._observer.schedule(event_handler, self._path.parent, recursive=False)
            self._observer.start()
            logger.info("watch started on %s", self._path)

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._callbacks = set()
            logger.info("watch stopped on %s", self._path)


class _CallbackRegWatcher(NamedTuple):
    _RegWatcherCallbackFunc = Callable[Concatenate[Any, ANY_PARAMETERS], None]

    func: _RegWatcherCallbackFunc
    args: tuple[Any]

    def __call__(self, value: Any) -> None:
        self.func(value, *self.args)


_hkey_constant_names = {v: name for name, v in winreg.__dict__.items() if "HKEY_" in name}


class _Key(NamedTuple):
    hkey: int
    path: str
    name: str

    def __repr__(self) -> str:
        return rf"{_hkey_constant_names[self.hkey]}\{self.path}\{self.name}"


class RegistryWatcher(StartStopContextManager):
    _timeout_ms = 100

    def __init__(self, hkey: int, path: str, name: str) -> None:
        self._key = _Key(hkey, path, name)
        self._thread: Optional[threading.Thread] = None
        self._running: threading.Event = threading.Event()
        self._callbacks: set[_CallbackRegWatcher] = set()

    def add_callback(self, callback: _CallbackRegWatcher._RegWatcherCallbackFunc, *args: Any) -> None:
        self._callbacks.add(_CallbackRegWatcher(callback, args))

    def start(self) -> None:
        self._thread = threading.Thread(target=self._wait_for_change)
        self._running.set()
        self._thread.start()
        logger.info("watch started on %s", self._key)

    def stop(self) -> None:
        if self._thread:
            self._running.clear()
            self._thread.join()
            self._thread = None
            self._callbacks = set()
            logger.info("watch stopped on %s", self._key)

    def _wait_for_change(self) -> None:
        with winreg.OpenKey(self._key.hkey, self._key.path) as key:
            current_value, _ = winreg.QueryValueEx(key, self._key.name)
            for change in wait_for_registry_change(key.handle, RegistryWatcher._timeout_ms, self._running):  # type: ignore
                if change:
                    value, _ = winreg.QueryValueEx(key, self._key.name)
                    if value != current_value:
                        current_value = value
                        for callback in self._callbacks:
                            callback(value)
