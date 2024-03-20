import ctypes
import os
from ctypes.wintypes import BOOL, DWORD, HANDLE

HIGH_PRIORITY_CLASS = 0x0080

_kernel32 = ctypes.windll.kernel32
_OpenProcess = _kernel32.OpenProcess
_OpenProcess.argtypes = [DWORD, BOOL, DWORD]
_OpenProcess.restype = HANDLE
_SetPriorityClass = _kernel32.SetPriorityClass
_SetPriorityClass.argtypes = [HANDLE, DWORD]
_SetPriorityClass.restype = BOOL

PROCESS_ALL_ACCESS = 0x000F0000 | 0x00100000 | 0xFFFF


def set_current_process_high_priority() -> bool:
    if handle := _OpenProcess(PROCESS_ALL_ACCESS, True, os.getpid()):
        return _SetPriorityClass(handle, HIGH_PRIORITY_CLASS)
    return False
