import ctypes
import queue
import sys
import threading
from ctypes.wintypes import BOOL, DWORD, HWND, LONG, LPARAM, LPDWORD, MSG
from typing import Callable, NamedTuple, Optional

from .win import is_enabled, is_visible

_user32 = ctypes.windll.user32


_EnumWindows = _user32.EnumWindows
_lpEnumFunc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
_EnumWindows.argtypes = _lpEnumFunc, LPARAM

_GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = HWND, LPDWORD
_GetWindowThreadProcessId.restype = DWORD

_GetWindowText = _user32.GetWindowTextW
_GetWindowTextLength = _user32.GetWindowTextLengthW
_GetWindowThreadProcessId = _user32.GetWindowThreadProcessId


class WindowExe(NamedTuple):
    hwnd: HWND
    tid: DWORD
    pid: DWORD
    title: str


def get_window_from_pid(pid: int) -> Optional[WindowExe]:
    hwnds: list[WindowExe] = []
    process_id = DWORD()

    def callback(hwnd: HWND, _: LPARAM) -> bool:
        if is_visible(hwnd) and is_enabled(hwnd):
            tid = _GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == pid:
                length = _GetWindowTextLength(hwnd)
                text = ctypes.create_unicode_buffer(length + 1)
                _GetWindowText(hwnd, text, length + 1)
                hwnds.append(WindowExe(hwnd, tid, DWORD(pid), text.value))
                return False  # stop iteration
        return True

    _EnumWindows(_lpEnumFunc(callback), 0)
    return hwnds[0] if hwnds else None


_WM_QUIT = 0x0012


class EventLoop:
    def __init__(self) -> None:
        self._tid: Optional[int] = None

    def run(self) -> None:
        if self._tid is None:
            self._tid = threading.get_native_id()
            msg = MSG()
            while _user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                _user32.TranslateMessageW(msg)
                _user32.DispatchMessageW(msg)

    def stop(self) -> None:
        if self._tid is not None:
            _user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)
            self._tid = None


APP_64 = sys.maxsize == (2**63) - 1
_HWINEVENTHOOK = ctypes.c_int64 if APP_64 else ctypes.c_int32

_WinEventProcType = ctypes.WINFUNCTYPE(None, _HWINEVENTHOOK, DWORD, HWND, LONG, LONG, DWORD, DWORD)
_SetWinEventHook = _user32.SetWinEventHook
_SetWinEventHook.restype = _HWINEVENTHOOK
_UnhookWinEvent = _user32.UnhookWinEvent
_WINEVENT_OUTOFCONTEXT = 0x0000
_WINEVENT_SKIPOWNTHREAD = 0x0001
_EVENT_OBJECT_LOCATIONCHANGE = 0x800B
_EVENT_SYSTEM_FOREGROUND = 0x0003
_EVENT_OBJECT_REORDER = 0x8004
_EVENT_OBJECT_SHOW = 0x8002


class Hook:
    """
    catch window movement, resize and z order change
    Note: need an event loop to work
    """

    _hooked_events = (
        _EVENT_OBJECT_LOCATIONCHANGE,
        _EVENT_SYSTEM_FOREGROUND,
        _EVENT_OBJECT_REORDER,
        _EVENT_OBJECT_SHOW,
    )

    def __init__(self, window: WindowExe, event_callback: Callable[[HWND], None]) -> None:
        self._lock = threading.Lock()
        self._hwnd = window.hwnd
        self._hooks: list[ctypes.c_int64 | ctypes.c_int32] = []
        self._events = _Events(window.hwnd, event_callback)
        _event_proc = _WinEventProcType(self._handle_event)  # keep a strong reference or crash
        self._hook_args = 0, _event_proc, window.pid, window.tid, _WINEVENT_OUTOFCONTEXT | _WINEVENT_SKIPOWNTHREAD

    # pylint: disable=unused-argument, too-many-arguments
    def _handle_event(self, event_hook, event, hwnd, id_object, id_child, event_thread, event_time) -> None:
        # try to reject as much as we can
        # None hwnd come from mouse & caret events
        # we are not interested in child windows location changes
        if hwnd and hwnd == self._hwnd or event != _EVENT_OBJECT_LOCATIONCHANGE:
            with self._lock:  # prevent reentry
                self._events.trigger()

    def __enter__(self) -> None:
        # several hooks with only one event to reduce unneeded costly hook trigger
        self._events.start()
        for event in Hook._hooked_events:
            hook = _SetWinEventHook(event, event, *self._hook_args)
            self._hooks.append(hook)

    def __exit__(self, *_) -> None:
        for hook in self._hooks:
            _UnhookWinEvent(hook)
        self._events.stop()


class _Events:
    """uncouple trigger event from event callback so that a triggering is as fast as possible"""

    def __init__(self, hwnd: HWND, event_callback: Callable[[HWND], None]) -> None:
        self._hwnd = hwnd
        self._event_callback = event_callback
        self._listenning = True
        self._event_count = 0
        self._events: "queue.LifoQueue[int|None]" = queue.LifoQueue()  # last event is the first handeld
        self._event_count_lock = threading.Lock()
        self._listen_thread = threading.Thread(target=self._listen_event)

    def _listen_event(self) -> None:
        """listen and call only the most recent event"""
        last_event_count = 0
        while self._listenning:
            event_count = self._events.get()
            if event_count and event_count > last_event_count:
                last_event_count = event_count
                self._event_callback(self._hwnd)

    def trigger(self) -> None:
        with self._event_count_lock:
            self._event_count += 1  # safe for years with 1000 events / second ^^
        self._events.put_nowait(self._event_count)

    def start(self) -> None:
        self._listen_thread.start()

    def stop(self) -> None:
        self._listenning = False
        self._events.put(None)  # unblock events queue
        self._listen_thread.join()
