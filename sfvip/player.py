import json
import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from sfvip_all_config import Player as ConfigPlayer

from .config_loader import ConfigLoader
from .regkey import RegKey
from .ui import UI, Rect


class SfvipError(Exception):
    pass


class Player:
    """find & run sfvip player"""

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

    class ConfigDir:
        _regkey = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
        _default = Path(os.getenv("APPDATA")) / "SFVIP-Player"

        def __init__(self) -> None:
            path = RegKey.value_by_name(*Player.ConfigDir._regkey)
            self.path = Path(path) if path and Path(path).is_dir() else Player.ConfigDir._default

    def __init__(self, config_player: type[ConfigPlayer], config_loader: ConfigLoader, ui: UI) -> None:
        self._ui = ui
        self._path = self._get_path(config_player, config_loader)
        if not self._valid(self._path):
            raise SfvipError("No player found")
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
    def _valid(path: str) -> bool:
        if path:
            path: Path = Path(path)
            return path.is_file() and path.match(Player._pattern)
        return False

    def _get_path(self, config_player: type[ConfigPlayer], config_loader: ConfigLoader) -> Optional[str]:
        path = config_player.path
        if not self._valid(path):
            for path in self._get_paths_from_regkey():
                if self._valid(path):
                    break
            else:
                path = self._get_path_from_user()
            if self._valid(path) and path != config_player.path:
                config_player.path = path
                config_loader.save()
        return path

    @staticmethod
    def _get_paths_from_regkey() -> list[str]:
        for search, hkey, key, apply in Player._regkey_search:
            if found := search(hkey, key, Player._name):
                return apply(found)
        return []

    def _get_path_from_user(self) -> Optional[str]:
        self._ui.showinfo(f"Please find {Player._name.capitalize()}")
        while True:
            if player := self._ui.find_file(Player._name, Player._pattern):
                return player
            if not self._ui.askretry(message=f"{Player._name.capitalize()} not found, try again ?"):
                return None

    def run(self) -> subprocess.Popen:
        return subprocess.Popen([self._path])
