from sfvip_all_config import DefaultAppConfig

from .accounts import Accounts
from .player import Player
from .proxies import LocalProxies
from .ui import UI


def sfvip(app_config: DefaultAppConfig, app_name: str, app_splash: str) -> None:
    app_config.update()
    ui = UI(app_name, app_splash)
    player = Player(app_config.player.path, ui)
    if app_config.player.path != player.path:
        app_config.player.path = player.path
        app_config.save()

    def _run() -> None:
        ui.splash.show(player.rect)
        accounts = Accounts(player.config_dir)
        with LocalProxies(app_config.all_cat, accounts.upstream_proxies) as local_proxies:
            with accounts.set_proxies(local_proxies.by_upstreams) as restore_proxies:
                with player.run():
                    restore_proxies()
                    ui.splash.hide()

    ui.in_thread(_run)
