import logging
import threading
import winreg
from abc import abstractmethod
from pathlib import Path
from typing import Any, Callable, Concatenate, NamedTuple, Optional, ParamSpec, Self

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from ..winapi import hook, rect, registry, win
from .ui import Rect, WinState

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
    _CallbackFunc = Callable[Concatenate[float, ANY_PARAMETERS], None]

    func: _CallbackFunc
    args: tuple[Any]

    def __call__(self, last_modified: float) -> None:
        self.func(last_modified, *self.args)


class FileWatcher(StartStopContextManager):
    # _debounce_s = 0.1

    def __init__(self, path: Optional[Path]) -> None:
        self._observer: Optional[BaseObserver] = None
        self._callbacks: set[_CallbackFileWatcher] = set()
        self._path: Optional[Path] = path if path and path.is_file() else None

    def _on_modified(self, event: FileSystemEvent) -> None:
        assert self._path
        if event.src_path == str(self._path):
            logger.info("watched file %s modified", self._path)
            for callback in self._callbacks:
                callback(self._path.stat().st_mtime)

    def add_callback(self, callback: _CallbackFileWatcher._CallbackFunc, *args: Any) -> None:
        self._callbacks.add(_CallbackFileWatcher(callback, args))

    def start(self) -> None:
        if self._path:
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
    _CallbackFunc = Callable[Concatenate[Any, ANY_PARAMETERS], None]

    func: _CallbackFunc
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
    _timeout_ms = 500

    def __init__(self, hkey: int, path: str, name: str) -> None:
        self._key = _Key(hkey, path, name)
        self._thread: Optional[threading.Thread] = None
        self._running: threading.Event = threading.Event()
        self._callbacks: set[_CallbackRegWatcher] = set()

    def add_callback(self, callback: _CallbackRegWatcher._CallbackFunc, *args: Any) -> None:
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
            for change in registry.wait_for_registry_change(key.handle, RegistryWatcher._timeout_ms, self._running):  # type: ignore
                if change:
                    value, _ = winreg.QueryValueEx(key, self._key.name)
                    if value != current_value:
                        current_value = value
                        for callback in self._callbacks:
                            callback(value)


class _CallbackWindowWatcher(NamedTuple):
    _CallbackFunc = Callable[[WinState], None]

    func: _CallbackFunc

    def __call__(self, state: WinState) -> None:
        self.func(state)


class WindowWatcher(StartStopContextManager):
    def __init__(self, pid: int, name: str) -> None:
        self._pid = pid
        self._name = name
        self._init_done = threading.Event()
        self._event_loop = hook.EventLoop()
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[_CallbackWindowWatcher] = None

    def _on_pos_changed(self, hwnd: hook.HWND) -> None:
        if self._callback:
            state = WinState(
                Rect(*rect.get_rect(hwnd), win.is_maximized(hwnd)),
                win.is_minimized(hwnd),
                win.has_no_border(hwnd),
                win.is_topmost(hwnd),
            )
            self._callback(state)

    def _hook(self) -> None:
        with hook.Hook(self._pid, self._on_pos_changed):
            # we're good to go now
            self._init_done.set()
            # we need an event loop to make the hook working
            self._event_loop.start()

    def set_callback(self, callback: _CallbackWindowWatcher._CallbackFunc) -> None:
        self._callback = _CallbackWindowWatcher(callback)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._hook)
        self._init_done.clear()
        self._thread.start()
        self._init_done.wait()
        logger.info("watch started on %s Window", self._name)

    def stop(self) -> None:
        if self._thread:
            self._event_loop.stop()
            self._thread.join()
            logger.info("watch stopped on %s Window", self._name)
            self._callback = None
