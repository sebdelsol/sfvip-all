import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from sfvip_all_config import Player as ConfigPlayer

from .config import Loader
from .regkey import RegKey
from .ui import UI


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

    def __init__(self, config_player: type[ConfigPlayer], config_loader: Loader, app_name: str) -> None:
        self.app_name = app_name
        self._path = self._get_path(config_player, config_loader, app_name)
        if not self._valid(self._path):
            raise SfvipError("No player found")

    @staticmethod
    def _valid(path: str) -> bool:
        if path:
            path: Path = Path(path)
            return path.is_file() and path.match(Player._pattern)
        return False

    def _get_path(self, config_player: type[ConfigPlayer], config_loader: Loader, app_name: str) -> Optional[str]:
        path = config_player.path
        if not self._valid(path):
            for path in self._get_paths_from_regkey():
                if self._valid(path):
                    break
            else:
                path = self._get_path_from_user(app_name)
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

    @staticmethod
    def _get_path_from_user(app_name: str) -> Optional[str]:
        ui = UI(app_name)
        ui.showinfo(f"Please find {Player._name}")
        while True:
            if player := ui.find_file(Player._name, Player._pattern):
                return player
            if not ui.askretry(message=f"{Player._name} not found, try again ?"):
                return None

    def run(self) -> subprocess.Popen:
        return subprocess.Popen([self._path])
