import json
import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from .regkey import RegKey
from .ui import UI, Rect


class SfvipError(Exception):
    pass


class Player:
    """find & run sfvip player"""

    class ConfigDir:
        _regkey = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
        _default = Path(os.environ["APPDATA"]) / "SFVIP-Player"

        def __init__(self) -> None:
            path = RegKey.value_by_name(*Player.ConfigDir._regkey)
            self.path = Path(path) if path and Path(path).is_dir() else Player.ConfigDir._default

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey_search = (
        (
            RegKey.name_by_value,
            winreg.HKEY_CLASSES_ROOT,
            r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache",
            lambda found: [os.path.splitext(found)[0]],
        ),
        (
            RegKey.search_name_contains,
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store",
            lambda found: found,
        ),
    )

    def __init__(self, player_path: Optional[str], ui: UI) -> None:
        if not self._valid(player_path):
            for path in self._get_paths_from_regkey():
                if self._valid(path):
                    player_path = path
                    break
            else:
                player_path = self._get_path_from_user(ui)
            if not self._valid(player_path):
                raise SfvipError("Player not found")

        self.path = player_path
        self.config_dir = Player.ConfigDir().path

    @property
    def rect(self):
        player_config = self.config_dir / "Config.json"
        if player_config.is_file():
            with player_config.open("r") as f:
                config: dict = json.load(f)
            if not config.get("IsMaximized"):
                return Rect.from_dict_keys(config, "Left", "Top", "Width", "Height")
        return Rect()

    @staticmethod
    def _valid(path: Optional[str]) -> bool:
        if path:
            _path: Path = Path(path)
            return _path.is_file() and _path.match(Player._pattern)
        return False

    @staticmethod
    def _get_paths_from_regkey() -> list[str]:
        for search, hkey, key, apply in Player._regkey_search:
            if found := search(hkey, key, Player._name):
                return apply(found)
        return []

    @staticmethod
    def _get_path_from_user(ui: UI) -> Optional[str]:
        ui.showinfo(f"Please find {Player._name.capitalize()}")
        while True:
            if player := ui.find_file(Player._name, Player._pattern):
                return player
            if not ui.askretry(message=f"{Player._name.capitalize()} not found, try again ?"):
                return None

    def run(self) -> subprocess.Popen[bytes]:
        if self.path:
            return subprocess.Popen([self.path])
        raise SfvipError("No player")
