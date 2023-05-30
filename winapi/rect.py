import ctypes
from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM, LPDWORD, RECT
from typing import Optional

_EnumWindows = ctypes.windll.user32.EnumWindows
_lpEnumFunc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
_EnumWindows.argtypes = _lpEnumFunc, LPARAM

_GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = HWND, LPDWORD
_GetWindowThreadProcessId.restype = DWORD

_IsWindowVisible = ctypes.windll.user32.IsWindowVisible
_IsWindowVisible.argtypes = (HWND,)
_IsWindowVisible.restype = BOOL

_IsWindowEnabled = ctypes.windll.user32.IsWindowEnabled
_IsWindowEnabled.argtypes = (HWND,)
_IsWindowEnabled.restype = BOOL


class Rect(RECT):
    def get_xywh(self) -> tuple[int, int, int, int]:
        x, y = int(self.left), int(self.top)
        w, h = int(self.right) - x, int(self.bottom) - y
        return x, y, w, h


_GetWindowRect = ctypes.windll.user32.GetWindowRect
_GetWindowRect.argtypes = HWND, ctypes.POINTER(Rect)
_GetWindowRect.restype = BOOL


def get_rect_for_pid(pid: int) -> Optional[tuple[int, int, int, int]]:
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
    if hwnds:
        rect = Rect()
        _GetWindowRect(hwnds[0], ctypes.byref(rect))
        return rect.get_xywh()
    return None
