import ctypes
import os
import winreg
from ctypes import wintypes

PATH_ENV_VAR = "PATH"

HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
SendMessageTimeout = ctypes.windll.user32.SendMessageTimeoutW
SendMessageTimeout.restype = None  # wintypes.LRESULT
SendMessageTimeout.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPCWSTR,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(wintypes.DWORD),
]


def broadcast_sys_path_change():
    SendMessageTimeout(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        "Environment",
        SMTO_ABORTIFHUNG,
        5000,
        ctypes.pointer(wintypes.DWORD()),
    )


def sz_expand(value, value_type):
    if value_type == winreg.REG_EXPAND_SZ:
        return winreg.ExpandEnvironmentStrings(value)
    return value


def remove_from_sys_path(pathname):
    pathname = os.path.normcase(os.path.normpath(pathname))
    envkeys = [(winreg.HKEY_CURRENT_USER, r"Environment")]
    for root, keyname in envkeys:
        key = winreg.OpenKey(root, keyname, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        reg_value = None
        try:
            reg_value = winreg.QueryValueEx(key, PATH_ENV_VAR)
        except WindowsError:
            # no PATH variable
            winreg.CloseKey(key)
            continue
        try:
            any_change = False
            results = []
            for v in reg_value[0].split(os.pathsep):
                vexp = sz_expand(v, reg_value[1])
                # Check if the expanded path matches the requested path in a normalized way
                if os.path.normcase(os.path.normpath(vexp)) == pathname:
                    any_change = True
                else:
                    # Append the original unexpanded version to the results
                    results.append(v)

            modified_path = os.pathsep.join(results)
            if any_change:
                winreg.SetValueEx(key, PATH_ENV_VAR, 0, reg_value[1], modified_path)
        except:  # pylint: disable=bare-except
            winreg.CloseKey(key)


def add_to_sys_path(path: str) -> None:
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise RuntimeError(f"Directory {path} does not exist, " "can't add it to path")

    root, keyname = (winreg.HKEY_CURRENT_USER, r"Environment")
    key = winreg.OpenKey(root, keyname, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
    reg_type = None
    reg_value = None
    try:
        try:
            reg_value = winreg.QueryValueEx(key, PATH_ENV_VAR)
        except WindowsError:
            # no PATH variable
            reg_type = winreg.REG_EXPAND_SZ
            final_value = path
        else:
            reg_type = reg_value[1]
            final_value = path + os.pathsep + reg_value[0]
        winreg.SetValueEx(key, PATH_ENV_VAR, 0, reg_type, final_value)
    finally:
        winreg.CloseKey(key)
