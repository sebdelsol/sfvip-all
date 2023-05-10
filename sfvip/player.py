import subprocess
import winreg
from pathlib import Path
from typing import Optional

from sfvip_all_config import Player as ConfigPlayer

from .config import Loader
from .regkey import RegKey
from .ui import UI


class Player:
    """find and check sfvip player"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _regkey = winreg.HKEY_CLASSES_ROOT, r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache"

    def __init__(self, config_loader: Loader, config_player: type[ConfigPlayer], app_name: str) -> None:
        self.app_name = app_name
        self.player_path = config_player.path
        if not self.valid():
            self.player_path = self._path_from_regkey()
            if not self.valid():
                self.player_path = self._path_from_user()
            if self.valid() and self.player_path != config_player.path:
                config_player.path = self.player_path
                config_loader.save()

    @staticmethod
    def _path_from_regkey() -> Optional[str]:
        if name := RegKey.name_by_value(*Player._regkey, Player._name):
            return ".".join(name.split(".")[:-1])
        return None

    def _path_from_user(self) -> Optional[str]:
        ui = UI(self.app_name)
        ui.showinfo(f"Please find {Player._name}")
        while True:
            if player := ui.find_file(Player._name, Player._pattern):
                return player
            if not ui.askretry(message=f"{Player._name} not found, try again ?"):
                return None

    def valid(self) -> bool:
        if self.player_path:
            player: Path = Path(self.player_path)
            return player.exists() and player.is_file() and player.match(Player._pattern)
        return False

    def run(self) -> subprocess.Popen:
        return subprocess.Popen([self.player_path])
