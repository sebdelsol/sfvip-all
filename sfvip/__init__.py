import os
from pathlib import Path

import sfvip_all_config as Config
from build_config import Build

from .accounts import Accounts
from .config_loader import ConfigLoader
from .local_proxies import LocalProxies
from .mutex import SystemWideMutex
from .player import Player
from .ui import UI


def run():
    config_file = Path(os.getenv("APPDATA")) / Build.name / "Config.json"
    config_loader = ConfigLoader(Config, config_file)
    config_loader.update()

    ui = UI(Build.name, Build.splash)
    player = Player(Config.Player, config_loader, ui)
    ui.splash.show(player.rect)

    init_lock = SystemWideMutex(Build.name, acquire=True)
    accounts = Accounts(player.config_dir)
    with LocalProxies(Config.AllCat, accounts.upstream_proxies) as local_proxies:
        restore = accounts.set_proxies(local_proxies.by_upstreams)
        try:
            with player.run():
                accounts.wait_being_read()
                accounts.set_proxies(restore)
                init_lock.release()
                ui.splash.hide()
        finally:
            with init_lock:
                accounts.set_proxies(restore)
