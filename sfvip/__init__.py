import os
from pathlib import Path

import sfvip_all_config as Config
from build_config import Build

from .accounts import Accounts
from .config_loader import ConfigLoader
from .local_proxies import LocalProxies
from .player import Player
from .ui import UI


def run():
    config_loader = ConfigLoader(Config, Path(os.getenv("APPDATA")) / Build.name / "Config.json")
    config_loader.update()
    ui = UI(Build.name, Build.splash)
    player = Player(Config.Player, config_loader, ui)
    ui.splash.show(player.rect)
    accounts = Accounts(Build.name, player.config_dir)
    with LocalProxies(Config.AllCat, accounts.upstream_proxies) as local_proxies:
        with accounts.set_proxies(local_proxies.by_upstreams) as restore_accounts_proxies:
            with player.run():
                restore_accounts_proxies()
                ui.splash.hide()
