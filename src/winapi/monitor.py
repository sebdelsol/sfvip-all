import ctypes
from typing import NamedTuple

from .rect import _WindowRect

user32 = ctypes.windll.user32


class MonitorArea(NamedTuple):
    area: tuple[int, int, int, int]
    work_area: tuple[int, int, int, int]


_MonitorEnumProc = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(_WindowRect), ctypes.c_double
)


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("_sizeof", ctypes.c_ulong),
        ("area", _WindowRect),
        ("work_area", _WindowRect),
        ("_flags", ctypes.c_ulong),
    ]


def _get_monitor_area(handle_monitor) -> MonitorArea:
    monitor_info = _MonitorInfo(ctypes.sizeof(_MonitorInfo), _WindowRect(), _WindowRect())
    user32.GetMonitorInfoA(handle_monitor, ctypes.byref(monitor_info))
    return MonitorArea(monitor_info.area.get_rect(), monitor_info.work_area.get_rect())


def get_handle_monitors():
    handle_monitors = []

    def monitor_enum(handle_monitor, _0, _1, _2):
        handle_monitors.append(handle_monitor)
        return True

    monitor_enum_proc = _MonitorEnumProc(monitor_enum)
    user32.EnumDisplayMonitors(0, 0, monitor_enum_proc, 0)
    return handle_monitors


def monitors_areas():
    return [_get_monitor_area(handle_monitor) for handle_monitor in get_handle_monitors()]
