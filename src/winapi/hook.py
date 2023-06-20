import ctypes
import threading
from ctypes.wintypes import BOOL, DWORD, HWND, LONG, LPARAM, LPDWORD, MSG
from typing import Callable, NamedTuple, Optional

from .win import is_enabled, is_foreground, is_visible

_user32 = ctypes.windll.user32


_EnumWindows = _user32.EnumWindows
_lpEnumFunc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
_EnumWindows.argtypes = _lpEnumFunc, LPARAM

_GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = HWND, LPDWORD
_GetWindowThreadProcessId.restype = DWORD

_GetWindowText = _user32.GetWindowTextW
_GetWindowTextLength = _user32.GetWindowTextLengthW


class WinIDs(NamedTuple):
    hwnd: HWND
    tid: DWORD
    pid: DWORD
    title: str


def get_winids_from_pid(pid: int) -> Optional[WinIDs]:
    hwnds: list[WinIDs] = []
    process_id = DWORD()

    def callback(hwnd: HWND, _) -> bool:
        if is_visible(hwnd) and is_enabled(hwnd):
            tid = _GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == pid:
                length = _GetWindowTextLength(hwnd)
                text = ctypes.create_unicode_buffer(length + 1)
                _GetWindowText(hwnd, text, length + 1)
                hwnds.append(WinIDs(hwnd, tid, DWORD(pid), text.value))
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


_WINEVENT_OUTOFCONTEXT = 0x0000
_SetWinEventHook = _user32.SetWinEventHook
_HWINEVENTHOOK = ctypes.c_int64
_WinEventProcType = ctypes.WINFUNCTYPE(None, _HWINEVENTHOOK, DWORD, HWND, LONG, LONG, DWORD, DWORD)
_user32.SetWinEventHook.restype = _HWINEVENTHOOK
_UnhookWinEvent = _user32.UnhookWinEvent

_EVENT_OBJECT_LOCATIONCHANGE = 0x800B
_EVENT_SYSTEM_FOREGROUND = 0x0003
_EVENT_OBJECT_REORDER = 0x8004
_EVENT_OBJECT_SHOW = 0x8002
_OBJID_CLIENT = -4


class Hook:
    """
    catch window movement, resize and z order change
    Note: need an event loop to work
    """

    _location_event = _EVENT_OBJECT_LOCATIONCHANGE
    _hooked_events = (
        _location_event,
        _EVENT_SYSTEM_FOREGROUND,
        _EVENT_OBJECT_REORDER,
        _EVENT_OBJECT_SHOW,
    )

    def __init__(self, winids: WinIDs, event_callback: Callable[[HWND], None]) -> None:
        self._hwnd = winids.hwnd
        self._event_callback = event_callback
        self._hooks: list[_HWINEVENTHOOK] = []
        _event_proc = _WinEventProcType(self._handle_event)  # keep a strong reference or crash
        self._hook_args = 0, _event_proc, winids.pid, winids.tid, _WINEVENT_OUTOFCONTEXT

    # pylint: disable=unused-argument, too-many-arguments
    def _handle_event(self, event_hook, event, hwnd, id_object, id_child, event_thread, event_time) -> None:
        # try to reject as mush as we can
        # None hwnd comes from mouse & caret events
        # we are not interested in child windows location changes
        if hwnd and hwnd == self._hwnd or event != Hook._location_event:
            if self._hwnd and is_visible(self._hwnd) and is_enabled(self._hwnd):
                if is_foreground(self._hwnd) or is_foreground(hwnd) or id_object == _OBJID_CLIENT:
                    self._event_callback(self._hwnd)

    def __enter__(self) -> None:
        # several hooks with only one event to reduce uneeded and costly hook trigger
        for event in Hook._hooked_events:
            hook = _SetWinEventHook(event, event, *self._hook_args)
            self._hooks.append(hook)

    def __exit__(self, *_) -> None:
        for hook in self._hooks:
            _UnhookWinEvent(hook)
