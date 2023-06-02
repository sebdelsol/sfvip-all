import ctypes
from ctypes.wintypes import BOOL, HWND, RECT

_user32 = ctypes.windll.user32


class _WindowRect(RECT):
    def get_rect(self) -> tuple[int, int, int, int]:
        x, y = int(self.left), int(self.top)
        w, h = int(self.right) - x, int(self.bottom) - y
        return x, y, w, h


_GetWindowRect = _user32.GetWindowRect
_GetWindowRect.argtypes = HWND, ctypes.POINTER(_WindowRect)
_GetWindowRect.restype = BOOL


def get_rect(hwnd: HWND) -> tuple[int, int, int, int]:
    rect = _WindowRect()
    _GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.get_rect()
