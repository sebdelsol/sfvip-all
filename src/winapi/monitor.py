import ctypes
from ctypes.wintypes import BOOL, DWORD, HDC, LPARAM
from typing import Any, NamedTuple

from .rect import _WindowRect

user32 = ctypes.windll.user32

_HMONITOR = ctypes.c_int64


class MonitorArea(NamedTuple):
    area: tuple[int, int, int, int]
    work_area: tuple[int, int, int, int]


_MonitorEnumProc = ctypes.WINFUNCTYPE(BOOL, _HMONITOR, HDC, ctypes.POINTER(_WindowRect), LPARAM)


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("_sizeof", DWORD),
        ("area", _WindowRect),
        ("work_area", _WindowRect),
        ("_flags", DWORD),
    ]


def _get_monitor_area(handle_monitor: _HMONITOR) -> MonitorArea:
    monitor_info = _MonitorInfo(ctypes.sizeof(_MonitorInfo), _WindowRect(), _WindowRect())
    user32.GetMonitorInfoW(handle_monitor, ctypes.byref(monitor_info))
    return MonitorArea(monitor_info.area.get_rect(), monitor_info.work_area.get_rect())


def get_handle_monitors() -> list[_HMONITOR]:
    handle_monitors: list[_HMONITOR] = []

    def monitor_enum(handle_monitor: _HMONITOR, *_: Any) -> bool:
        handle_monitors.append(handle_monitor)
        return True

    monitor_enum_proc = _MonitorEnumProc(monitor_enum)
    user32.EnumDisplayMonitors(0, 0, monitor_enum_proc, 0)
    return handle_monitors


def monitors_areas() -> list[MonitorArea]:
    return [_get_monitor_area(handle_monitor) for handle_monitor in get_handle_monitors()]
