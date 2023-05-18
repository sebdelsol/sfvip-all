import os
from pathlib import Path

import sfvip_all_config

from .accounts import Accounts
from .config import AppConfigLoader
from .mutex import SystemWideMutex
from .player import Player
from .proxies import LocalProxies
from .ui import UI


def run(app_config: sfvip_all_config, app_name: str, ui: UI):
    app_config_file = Path(os.getenv("APPDATA")) / app_name / "Config.json"
    app_config_loader = AppConfigLoader(app_config, app_config_file)
    app_config_loader.update()

    player = Player(app_config.Player.path, ui)
    if app_config.Player.path != player.path:
        app_config.Player.path = player.path
        app_config_loader.save()

    ui.splash.show(player.rect)
    init_lock = SystemWideMutex(app_name, acquire=True)
    accounts = Accounts(player.config_dir)
    with LocalProxies(app_config.AllCat, accounts.upstream_proxies) as local_proxies:
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
