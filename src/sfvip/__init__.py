import logging
import os
import sys
from pathlib import Path

from sfvip_all_config import AppConfig

from .accounts import AccountsProxies
from .player import Player, PlayerError
from .proxies import LocalProxies
from .ui import UI, AppInfo

logger = logging.getLogger(__name__)


def remove_old_exe_logs(app_name: str, keep: int) -> None:
    # launched as an exe build by nuitka ?
    if "__compiled__" in globals():
        # logs files are in the exe dir
        path = Path(sys.argv[0]).parent
        log_files = list(path.glob(f"{app_name} - *.log"))
        if len(log_files) > keep:
            logger.info("keep the last %d logs", keep)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for log in log_files[keep:]:
                try:
                    log.unlink(missing_ok=True)
                except PermissionError:
                    pass


def run_app(app_info: AppInfo, splash: Path, logo: Path) -> None:
    app_roaming = Path(os.environ["APPDATA"]) / app_info.name
    config = AppConfig(app_roaming / "Config All.json")
    config.update()
    ui = UI(app_info, splash, logo)

    try:
        player = Player(config.player.path, ui)
        if config.player.path != player.path:
            config.player.path = player.path
            config.save()

        def run() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts_proxies = AccountsProxies(app_roaming, ui)
                with LocalProxies(config.all_category, accounts_proxies.upstreams) as local_proxies:
                    with accounts_proxies.set(local_proxies.by_upstreams) as restore_accounts_proxies:
                        with player.run():
                            restore_accounts_proxies(player.relaunch)
                            ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)

        ui.run_in_thread(PlayerError, run)

    except PlayerError as err:
        ui.showinfo(f"{err}\nPlease launch Sfvip Player at least once !")
        logger.warning(str(err))
