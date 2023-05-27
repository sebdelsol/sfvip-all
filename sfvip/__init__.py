import threading
from typing import Any

from sfvip_all_config import DefaultAppConfig

from .accounts import Accounts
from .player import Player, PlayerError
from .proxies import LocalProxies
from .ui import UI


def sfvip(app_config: DefaultAppConfig, app_name: str, app_splash: str) -> None:
    app_config.update()
    ui = UI(app_name, app_splash)
    try:
        player = Player(app_config.player.path, ui)
        if app_config.player.path != player.path:
            app_config.player.path = player.path
            app_config.save()

        def _run() -> None:
            relaunch = threading.Event()
            relaunch.set()
            while relaunch.is_set():
                relaunch.clear()
                ui.splash.show(player.rect)
                accounts = Accounts(player, relaunch)
                with LocalProxies(app_config.all_category, accounts.upstreams) as proxies:
                    with accounts.set_proxies(proxies.by_upstreams) as restore_accounts_proxies:
                        with player.run():
                            restore_accounts_proxies()
                            ui.splash.hide()
                # if relaunch.is_set():
                #     ui.showinfo("need to relaunch to handle new proxies")

        ui.in_thread(_run)

    except PlayerError as err:
        ui.showinfo(f"{err}.\n\nPlease launch Sfvip Player at least once !")
