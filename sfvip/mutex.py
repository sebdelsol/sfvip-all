import ctypes
from ctypes import wintypes
from typing import Self

_CreateMutex = ctypes.windll.kernel32.CreateMutexW
_CreateMutex.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
_CreateMutex.restype = wintypes.HANDLE

_WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_WaitForSingleObject.restype = wintypes.DWORD

_ReleaseMutex = ctypes.windll.kernel32.ReleaseMutex
_ReleaseMutex.argtypes = [wintypes.HANDLE]
_ReleaseMutex.restype = wintypes.BOOL

_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL

_INFINITE = 0xFFFFFFFF


class NamedMutex:
    """A named, system-wide mutex that can be acquired and released."""

    def __init__(self, name: str) -> None:
        self._acquired = False
        if not (ret := _CreateMutex(None, False, name)):
            raise ctypes.WinError()
        self._handle = ret

    @property
    def aquired(self) -> bool:
        return self._acquired

    def acquire(self, timeout: None | int | float = None) -> bool:
        timeout = _INFINITE if timeout is None else int(round(timeout * 1000))
        ret = _WaitForSingleObject(self._handle, timeout)
        if ret in (0, 0x80):
            self._acquired = True
            return True
        if ret == 0x102:  # Timeout
            self._acquired = False
            return False
        raise ctypes.WinError()

    def release(self) -> None:
        if not _ReleaseMutex(self._handle):
            raise ctypes.WinError()
        self._acquired = False

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
