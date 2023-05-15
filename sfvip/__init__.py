import os
from pathlib import Path

import sfvip_all_config as Config

from .accounts import Accounts
from .config import Loader
from .player import Player
from .proxies import Proxies


def run(config: Config, app_name: str):
    config_json = Path(os.getenv("APPDATA")) / app_name / "Config.json"
    config_loader = Loader(config, config_json)
    config_loader.update()

    accounts = Accounts(app_name)
    player = Player(config.Player, config_loader, app_name)
    with Proxies(config.AllCat, accounts.upstream_proxies) as proxies_by_upstreams:
        with accounts.set_proxies(proxies_by_upstreams) as restore_proxies:
            with player.run():
                restore_proxies()
