import ctypes
import threading
from ctypes.wintypes import BOOL, DWORD, HWND, LONG, LPARAM, LPDWORD, MSG
from typing import Callable, Optional

_user32 = ctypes.windll.user32


_EnumWindows = _user32.EnumWindows
_lpEnumFunc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
_EnumWindows.argtypes = _lpEnumFunc, LPARAM

_GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = HWND, LPDWORD
_GetWindowThreadProcessId.restype = DWORD

_IsWindowVisible = _user32.IsWindowVisible
_IsWindowVisible.argtypes = [HWND]
_IsWindowVisible.restype = BOOL

_IsWindowEnabled = _user32.IsWindowEnabled
_IsWindowEnabled.argtypes = [HWND]
_IsWindowEnabled.restype = BOOL


def _get_hwnd_from_pid(pid: int) -> Optional[HWND]:
    hwnds: list[HWND] = []
    lpdw_process_id = ctypes.c_ulong()

    def callback(hwnd: HWND, _) -> bool:
        if _IsWindowVisible(hwnd) and _IsWindowEnabled(hwnd):
            _GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
            if lpdw_process_id.value == pid:
                hwnds.append(hwnd)
                return False  # stop iteration
        return True

    _EnumWindows(_lpEnumFunc(callback), 0)
    return hwnds[0] if hwnds else None


_WM_QUIT = 0x0012


class EventLoop:
    def __init__(self) -> None:
        self._tid: Optional[int] = None

    def start(self) -> None:
        self._tid = threading.get_native_id()
        msg = MSG()
        while _user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            _user32.TranslateMessageW(msg)
            _user32.DispatchMessageW(msg)

    def stop(self) -> None:
        if self._tid:
            _user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)


_WINEVENT_OUTOFCONTEXT = 0x0000
_HWINEVENTHOOK = ctypes.c_int64
_SetWinEventHook = _user32.SetWinEventHook
_WinEventProcType = ctypes.WINFUNCTYPE(None, ctypes.c_int64, DWORD, HWND, LONG, LONG, DWORD, DWORD)
_user32.SetWinEventHook.restype = _HWINEVENTHOOK
_UnhookWinEvent = _user32.UnhookWinEvent

_EVENT_OBJECT_LOCATIONCHANGE = 0x800B
_EVENT_SYSTEM_FOREGROUND = 0x0003
_EVENT_OBJECT_REORDER = 0x8004
_EVENT_OBJECT_SHOW = 0x8002


class Hook:
    """
    catch window movement, resize and change of z order
    Note: need an event loop to work
    """

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
            hwnd  # None hwnd comes from mouse & caret events
            and hwnd == self._main_hwnd
            # we are not interested in child windows location changes
            or event != _EVENT_OBJECT_LOCATIONCHANGE
        ):
            if self._main_hwnd is None:
                self._main_hwnd = _get_hwnd_from_pid(self._pid)
            if self._main_hwnd:
                self._event_callback(self._main_hwnd)

    def _add_hook(self, event: int) -> None:
        """hook for only ONE event"""
        hook = _SetWinEventHook(event, event, 0, self._event_proc, self._pid, 0, _WINEVENT_OUTOFCONTEXT)
        self._hooks.append(hook)

    def __enter__(self) -> None:
        # several hooks with only one event to reduce uneeded and costly hook
        for event in (
            _EVENT_SYSTEM_FOREGROUND,
            _EVENT_OBJECT_LOCATIONCHANGE,
            _EVENT_OBJECT_SHOW,
            _EVENT_OBJECT_REORDER,
        ):
            self._add_hook(event)

    def __exit__(self, *_) -> None:
        for hook in self._hooks:
            _UnhookWinEvent(hook)
