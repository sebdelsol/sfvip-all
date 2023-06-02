import ctypes
import ctypes.wintypes
import threading
from ctypes.wintypes import BOOL, DWORD, HANDLE, HKEY, LONG, LPCWSTR, LPVOID
from typing import Iterator, Self

_kernel32 = ctypes.windll.kernel32

_RegNotifyChangeKeyValue = ctypes.windll.advapi32.RegNotifyChangeKeyValue
_RegNotifyChangeKeyValue.restype = LONG
_RegNotifyChangeKeyValue.argtypes = [HKEY, BOOL, DWORD, HANDLE, BOOL]

_CreateEvent = _kernel32.CreateEventW
_CreateEvent.restype = BOOL
_CreateEvent.argtypes = [LPVOID, BOOL, BOOL, LPCWSTR]

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.restype = BOOL
_CloseHandle.argtypes = [HANDLE]

_WaitForSingleObject = _kernel32.WaitForSingleObject
_WaitForSingleObject.restype = DWORD
_WaitForSingleObject.argtypes = [HANDLE, DWORD]


_REG_NOTIFY_CHANGE_LAST_SET = 0x00000004
_ERROR_SUCCESS = 0x00000000
_WAIT_OBJECT_0 = 0x00000000


class _Event:
    def __init__(self) -> None:
        self.handle = _CreateEvent(None, False, False, None)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        _CloseHandle(self.handle)

    def wait(self, timeout_ms: int = 0) -> bool:
        wait_result = _WaitForSingleObject(self.handle, timeout_ms)
        if wait_result == _WAIT_OBJECT_0:
            return True
        return False


def _notify_for_change(key_handle: int, event_handle: int) -> bool:
    status = _RegNotifyChangeKeyValue(key_handle, False, _REG_NOTIFY_CHANGE_LAST_SET, event_handle, True)
    return status == _ERROR_SUCCESS


def wait_for_registry_change(key_handle: int, timeout_ms: int, running: threading.Event) -> Iterator[bool]:
    with _Event() as event:
        while running.is_set():
            if not _notify_for_change(key_handle, event.handle):
                break
            if event.wait(timeout_ms):
                yield True
    yield False
