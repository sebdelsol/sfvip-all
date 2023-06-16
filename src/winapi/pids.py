import ctypes
from ctypes.wintypes import HANDLE, LPDWORD

_SYNCHRONIZE = 0x00100000
_ERROR_ACCESS_DENIED = 0x00000005


class ExitCodeProcess(ctypes.Structure):
    _fields_ = [("hProcess", HANDLE), ("lpExitCode", LPDWORD)]  # HANDLE  # LPDWORD


def exists(pid):
    """Check whether a process with the given pid exists. Works on Windows only.
    Works even if the process is not owned by the current user."""
    kernel32 = ctypes.windll.kernel32

    process = kernel32.OpenProcess(_SYNCHRONIZE, 0, pid)
    if not process:
        if kernel32.GetLastError() == _ERROR_ACCESS_DENIED:
            # Access is denied. This means the process exists!
            return True
        return False

    ec = ExitCodeProcess()
    out = kernel32.GetExitCodeProcess(process, ctypes.byref(ec))
    if not out:
        if kernel32.GetLastError() == _ERROR_ACCESS_DENIED:
            # Access is denied. This means the process exists!
            kernel32.CloseHandle(process)
            return True
        kernel32.CloseHandle(process)
        return False
    if bool(ec.lpExitCode):
        # There is an exit code, it quit
        kernel32.CloseHandle(process)
        return False
    # No exit code, it's running.
    kernel32.CloseHandle(process)
    return True
