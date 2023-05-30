import ctypes
from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCVOID, LPCWSTR
from typing import Optional, Self

_CreateMutex = ctypes.windll.kernel32.CreateMutexW
_CreateMutex.argtypes = [LPCVOID, BOOL, LPCWSTR]
_CreateMutex.restype = HANDLE

_WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [HANDLE, DWORD]
_WaitForSingleObject.restype = DWORD

_ReleaseMutex = ctypes.windll.kernel32.ReleaseMutex
_ReleaseMutex.argtypes = [HANDLE]
_ReleaseMutex.restype = BOOL

_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CloseHandle.argtypes = [HANDLE]
_CloseHandle.restype = BOOL

TIMEOUT_INFINITE = 0xFFFFFFFF


class SystemWideMutex:
    """A system-wide mutex"""

    def __init__(self, name: str) -> None:
        name = name.replace("\\", " ")
        if not (ret := _CreateMutex(None, False, name)):
            raise ctypes.WinError()
        self._handle = ret

    def acquire(self, timeout: Optional[float] = None) -> bool:
        timeout = TIMEOUT_INFINITE if timeout is None else int(round(timeout * 1000))
        ret = _WaitForSingleObject(self._handle, timeout)
        if ret in (0, 0x80):
            return True
        if ret == 0x102:  # Timeout
            return False
        raise ctypes.WinError()

    def release(self) -> None:
        if not _ReleaseMutex(self._handle):
            raise ctypes.WinError()

    def close(self) -> None:
        if self._handle is None:  # Already closed
            return
        if not _CloseHandle(self._handle):
            raise ctypes.WinError()
        self._handle = None

    __del__ = close

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()
