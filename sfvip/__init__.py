from pathlib import Path

from sfvip_all_config import DefaultAppConfig

from .accounts import Accounts
from .player import Player, PlayerError
from .proxies import LocalProxies
from .ui import UI


def sfvip(config: DefaultAppConfig, name: str, version: str, splash: Path, logo: Path) -> None:
    config.update()
    ui = UI(name, version, splash, logo)

    try:
        player = Player(config.player.path, ui)
        if config.player.path != player.path:
            config.player.path = player.path
            config.save()

        def main() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts = Accounts(player.logs)
                with LocalProxies(config.all_category, accounts.upstreams) as proxies:
                    with accounts.set_proxies(proxies.by_upstreams, ui) as restore_accounts_proxies:
                        with player.run():
                            restore_accounts_proxies(player.relaunch)
                            ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)

        ui.run_in_thread(PlayerError, main)

    except PlayerError as err:
        ui.showinfo(f"{err}.\nPlease launch Sfvip Player at least once !")
