import os
from pathlib import Path

import sfvip_all_config as Config

from .accounts import Accounts
from .config import Loader
from .player import Player
from .proxies import Proxies

# TODO test standalone
# TODO handle m3u playlist ?


def run(config: Config, app_name: str):
    config_json = Path(os.getenv("APPDATA")) / app_name / "Config.json"
    config_loader = Loader(config, config_json)
    config_loader.update()

    player = Player(config_loader, config.Player, app_name)
    accounts = Accounts(config_loader, config.Player, app_name)
    with Proxies(config.AllCat, accounts.upstream_proxies) as proxies_by_upstreams:
        with accounts.set_proxies(proxies_by_upstreams) as restore_proxies:
            with player.run():
                restore_proxies()
