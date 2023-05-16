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


class NamedMutex:
    """A named, system-wide mutex that can be acquired and released."""

    def __init__(self, name: str, acquired: bool = False) -> None:
        self.name = name
        self.acquired = acquired
        ret = _CreateMutex(None, False, name)
        if not ret:
            raise ctypes.WinError()
        self.handle = ret
        if acquired:
            self.acquire()

    def acquire(self, timeout: None | int | float = None) -> bool:
        if timeout is None:
            timeout = 0xFFFFFFFF  # Wait forever (INFINITE)
        else:
            timeout = int(round(timeout * 1000))
        ret = _WaitForSingleObject(self.handle, timeout)
        if ret in (0, 0x80):
            self.acquired = True
            return True
        if ret == 0x102:  # Timeout
            self.acquired = False
            return False
        raise ctypes.WinError()

    def release(self) -> None:
        ret = _ReleaseMutex(self.handle)
        if not ret:
            raise ctypes.WinError()
        self.acquired = False

    def close(self) -> None:
        if self.handle is None:  # Already closed
            return
        ret = _CloseHandle(self.handle)
        if not ret:
            raise ctypes.WinError()
        self.handle = None

    __del__ = close

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r}, acquired={self.acquired})"

    __str__ = __repr__

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()
