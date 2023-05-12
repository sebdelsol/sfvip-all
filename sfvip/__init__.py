import os
from pathlib import Path

import sfvip_all_config as Config

from .config import Loader
from .player import Player
from .proxy import Proxy
from .users import UsersDatabase, UsersProxies

# TODO proxy fowarding (upstream mode)
# TODO test standalone


def run(config: Config, app_name: str):
    config_json = Path(os.getenv("APPDATA")) / app_name / "Config.json"
    config_loader = Loader(config, config_json)
    config_loader.update()

    player = Player(config_loader, config.Player, app_name)
    users_database = UsersDatabase(config_loader, config.Player)
    users_proxies = UsersProxies(users_database)
    with Proxy(config.AllCat, users_proxies.upstream) as proxy:
        with users_proxies.set(proxy.port):
            with player.run():
                users_proxies.restore_after_being_accessed()
