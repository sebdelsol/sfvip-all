import ctypes
import threading
from ctypes.wintypes import DWORD, HWND, LONG, MSG
from typing import Callable, Optional

_user32 = ctypes.windll.user32

_WINEVENT_OUTOFCONTEXT = 0x0000
_CHILDID_SELF = 0
_OBJID_WINDOW = 0
_WM_QUIT = 0x0012

_HWINEVENTHOOK = ctypes.c_int64
_SetWinEventHook = _user32.SetWinEventHook
_WinEventProcType = ctypes.WINFUNCTYPE(None, ctypes.c_int64, DWORD, HWND, LONG, LONG, DWORD, DWORD)
_user32.SetWinEventHook.restype = _HWINEVENTHOOK
_UnhookWinEvent = _user32.UnhookWinEvent


class EventLoop:
    def __init__(self) -> None:
        self._tid: Optional[int] = None

    def start(self):
        self._tid = threading.get_native_id()
        msg = MSG()
        while _user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            _user32.TranslateMessageW(msg)
            _user32.DispatchMessageW(msg)

    def stop(self):
        if self._tid:
            _user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)


class Hook:
    def __init__(self, pid: int, event_watched, event_callback: Callable[[HWND], None]) -> None:
        self._hook: Optional[_HWINEVENTHOOK] = None
        self._event_proc = _WinEventProcType(self._handle_event)  # keep a refernce
        self._searched_hwnd: Optional[HWND] = None
        self._event_callback = event_callback
        self._event_watched = event_watched
        self._pid = pid

    # pylint: disable=unused-argument, too-many-arguments
    def _handle_event(self, event_hook, event, hwnd, id_object, id_child, event_thread, event_time) -> None:
        if (
            hwnd  # pylint: disable=too-many-boolean-expressions
            and event_hook == self._hook
            and id_child == _CHILDID_SELF
            and id_object == _OBJID_WINDOW
            and _user32.IsWindowVisible(hwnd)
            and _user32.IsWindowEnabled(hwnd)
        ):
            if self._searched_hwnd is None:
                self._searched_hwnd = hwnd
            if hwnd == self._searched_hwnd:
                self._event_callback(hwnd)

    def __enter__(self) -> None:
        watched = self._event_watched, self._event_watched
        self._hook = _SetWinEventHook(*watched, 0, self._event_proc, self._pid, 0, _WINEVENT_OUTOFCONTEXT)

    def __exit__(self, *_) -> None:
        if self._hook:
            _UnhookWinEvent(self._hook)
