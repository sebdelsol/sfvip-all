import ctypes
from ctypes.wintypes import HWND
from typing import cast

_user32 = ctypes.windll.user32

_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x80000
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_WINDOWEDGE = 0x00000100
_WS_EX_TOPMOST = 0x00000008


def _get_window_exstyle(hwnd: HWND) -> int:
    return _user32.GetWindowLongPtrW(hwnd, _GWL_EXSTYLE)


def _set_window_exstyle(hwnd: HWND, exstyle: int) -> None:
    _user32.SetWindowLongPtrW(hwnd, _GWL_EXSTYLE, exstyle)


def is_minimized(hwnd: HWND) -> bool:
    return _user32.IsIconic(hwnd) == 1


def is_maximized(hwnd: HWND) -> bool:
    return _user32.IsZoomed(hwnd) == 1


def has_no_border(hwnd: HWND) -> bool:
    exstyle = _get_window_exstyle(hwnd)
    return exstyle & _WS_EX_WINDOWEDGE == 0


def is_topmost(hwnd: HWND) -> bool:
    exstyle = _get_window_exstyle(hwnd)
    return exstyle & _WS_EX_TOPMOST == _WS_EX_TOPMOST


def set_click_through(hwnd: int) -> None:
    _hwnd: HWND = cast(HWND, hwnd)
    exstyle = _get_window_exstyle(_hwnd)
    _set_window_exstyle(_hwnd, exstyle | _WS_EX_LAYERED | _WS_EX_TRANSPARENT)
    _user32.SetLayeredWindowAttributes(_hwnd, 0, 255, 0x00000001)
