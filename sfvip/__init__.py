import os
import winreg
from pathlib import Path

import sfvip_all_config as Config

from .config import Loader
from .player import Player
from .proxy import Proxy
from .regkey import RegKey
from .users import Users


def run(config: Config, app_name: str):
    config_dir = RegKey.value_by_name(winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir")
    config_dir = Path(config_dir) if config_dir else Path(os.getenv("APPDATA")) / "SFVIP-Player"
    config_loader = Loader(config, config_dir / "Sfvip All.json")
    config_loader.update_from_json()

    sfvip_player = Player(config_loader, config.Player, app_name)
    if sfvip_player.valid():
        with Proxy(config.AllCat) as sfvip_proxy:
            with Users(config_dir).set_proxy(sfvip_proxy.port) as sfvip_users:
                with sfvip_player.run():
                    sfvip_users.restore_proxy()
