import os
from pathlib import Path

import sfvip_all_config as Config

from .config import Loader
from .player import Player
from .proxy import Proxy
from .users import Users

# TODO proxy fowarding
# TODO test standalone


def run(config: Config, app_name: str):
    config_json = Path(os.getenv("APPDATA")) / app_name / "Config.json"
    config_loader = Loader(config, config_json)
    config_loader.update()

    sfvip_player = Player(config_loader, config.Player, app_name)
    with Proxy(config.AllCat) as sfvip_proxy:
        with Users(config_loader, config.Player).set_proxy(sfvip_proxy.port) as sfvip_users:
            with sfvip_player.run():
                sfvip_users: Users
                sfvip_users.restore_proxy()
