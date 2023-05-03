import os
import winreg
from pathlib import Path

from sfvip.tools import Loader, RegKey, Serializer

# find the svfip config directory in the registry or the env vars
_CONFIG_DIR = RegKey.value_by_name(winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir")
_CONFIG_DIR = Path(_CONFIG_DIR) if _CONFIG_DIR else Path(os.getenv("APPDATA")) / "SFVIP-Player"


class CONFIG(Loader, path=_CONFIG_DIR / "Proxy.json"):
    title = "svfip all"
    player = "sfvip player.exe"
    config_dir = str(_CONFIG_DIR.resolve())

    class Proxy(Serializer):
        buf_size_in_MB = 16
        log_level = "ERROR"
        timeout = 30

    class AllCat(Serializer):
        inject = ("series", "vod")
        name = "All"
        id = 0


CONFIG.update_from_json()
