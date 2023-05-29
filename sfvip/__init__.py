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

        def main() -> None:
            while player.do_launch():
                ui.splash.show(player.rect)
                accounts = Accounts(player.logs)
                with LocalProxies(app_config.all_category, accounts.upstreams) as proxies:
                    with accounts.set_proxies(proxies.by_upstreams) as restore_accounts_proxies:
                        with player.run():
                            restore_accounts_proxies(player.stop_and_relaunch)
                            ui.splash.hide()

        ui.run_in_thread(main)

    except PlayerError as err:
        ui.showinfo(f"{err}.\n\nPlease launch Sfvip Player at least once !")
