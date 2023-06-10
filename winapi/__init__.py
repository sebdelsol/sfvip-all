from ctypes.wintypes import HWND

from .hook import EventLoop, Hook
from .monitor import monitors_areas
from .mutex import SystemWideMutex
from .rect import get_rect
from .registry import wait_for_registry_change
from .win import (
    has_no_border,
    is_maximized,
    is_minimized,
    is_topmost,
    set_click_through,
)