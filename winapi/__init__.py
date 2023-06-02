from ctypes.wintypes import HWND

from .hook import EventLoop, Hook
from .mutex import SystemWideMutex
from .rect import get_rect
from .registry import wait_for_registry_change
from .style import has_no_border, is_minimized, set_click_through

EVENT_OBJECT_LOCATIONCHANGE = 0x800B
