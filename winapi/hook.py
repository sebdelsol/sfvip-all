import ctypes
import threading
from ctypes.wintypes import DWORD, HWND, LONG, MSG
from typing import Callable, Optional

_user32 = ctypes.windll.user32

_WINEVENT_OUTOFCONTEXT = 0x0000
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


EVENT_OBJECT_LOCATIONCHANGE = 0x800B
EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_SHOW = 0x8002

# TODO filter when no border


class Hook:
    def __init__(self, pid: int, event_callback: Callable[[HWND], None]) -> None:
        self._hooks: list[_HWINEVENTHOOK] = []
        self._event_proc = _WinEventProcType(self._handle_event)  # keep a refernce
        self._main_hwnd: Optional[HWND] = None
        self._event_callback = event_callback
        self._pid = pid

    # pylint: disable=unused-argument, too-many-arguments
    def _handle_event(self, event_hook, event, hwnd, id_object, id_child, event_thread, event_time) -> None:
        # try to reject as mush as we can
        if (
            hwnd
            and hwnd == self._main_hwnd
            # we are not interessted in child windows location changes
            or event != EVENT_OBJECT_LOCATIONCHANGE
        ):
            print(event_time)
            if self._main_hwnd is None:
                # we know the first event we catch contains the main window hwnd
                self._main_hwnd = hwnd
            self._event_callback(self._main_hwnd)

    def _add_hook(self, event: int) -> None:
        """hook for one event"""
        hook = _SetWinEventHook(event, event, 0, self._event_proc, self._pid, 0, _WINEVENT_OUTOFCONTEXT)
        self._hooks.append(hook)

    def __enter__(self) -> None:
        # several hooks with only one event to reduce call to _handle_event
        for event in EVENT_SYSTEM_FOREGROUND, EVENT_OBJECT_LOCATIONCHANGE, EVENT_OBJECT_SHOW:
            self._add_hook(event)

    def __exit__(self, *_) -> None:
        for hook in self._hooks:
            _UnhookWinEvent(hook)
