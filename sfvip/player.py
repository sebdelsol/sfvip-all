import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from sfvip_all_config import Player as ConfigPlayer

from .config import Loader
from .exceptions import SfvipError
from .regkey import RegKey
from .ui import UI


class Player:
    """find & run sfvip player"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey = winreg.HKEY_CLASSES_ROOT, r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache"

    def __init__(self, config_loader: Loader, config_player: type[ConfigPlayer], app_name: str) -> None:
        self.app_name = app_name
        self._path = self._get_path(config_loader, config_player, app_name)
        if not self._valid(self._path):
            raise SfvipError("No player found")

    @staticmethod
    def _valid(path: str) -> bool:
        if path:
            path: Path = Path(path)
            return path.is_file() and path.match(Player._pattern)
        return False

    def _get_path(self, config_loader: Loader, config_player: type[ConfigPlayer], app_name: str) -> Optional[str]:
        path = config_player.path
        if not self._valid(path):
            path = self._get_path_from_regkey()
            if not self._valid(path):
                path = self._get_path_from_user(app_name)
            if self._valid(path) and path != config_player.path:
                config_player.path = path
                config_loader.save()
        return path

    @staticmethod
    def _get_path_from_regkey() -> Optional[str]:
        if name := RegKey.name_by_value(*Player._regkey, Player._name):
            return os.path.splitext(name)[0]
        return None

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
