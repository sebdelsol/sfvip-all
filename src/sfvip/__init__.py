import logging
import os
import sys
from pathlib import Path

from .accounts import AccountsProxies
from .config import Config
from .player import Player, PlayerError
from .proxies import LocalProxies, LocalproxyError
from .ui import UI, AppInfo

logger = logging.getLogger(__name__)


class LogFiles:
    def __init__(self, app_name: str) -> None:
        self._app_name = app_name

    @staticmethod
    def _unlink(log: Path) -> bool:
        try:
            log.unlink(missing_ok=True)
            return True
        except PermissionError:
            return False

    def keep_only(self, keep: int) -> None:
        # launched by nuitka ?
        if "__compiled__" in globals():
            # logs files are in the exe dir
            exe_dir = Path(sys.argv[0]).parent
            logs = list(exe_dir.glob(f"{self._app_name} - *.log"))
            # remove empty logs
            for log in logs.copy():
                if log.stat().st_size == 0 and self._unlink(log):
                    logs.remove(log)
            # keep only #keep logs
            if len(logs) > keep:
                logger.info("keep the last %d log files", keep)
                logs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                for log in logs[keep:]:
                    self._unlink(log)


def run_app(app_info: AppInfo, splash: Path, logo: Path, keep_logs: int) -> None:
    ui = UI(app_info, splash, logo)
    try:
        app_roaming = Path(os.environ["APPDATA"]) / app_info.name
        config = Config(app_roaming)
        player = Player(config, ui)

        def run() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts_proxies = AccountsProxies(app_roaming, ui)
                with LocalProxies(config.all_category, accounts_proxies.upstreams) as local_proxies:
                    with accounts_proxies.set(local_proxies.by_upstreams) as restore_accounts_proxies:
                        with player.run():
                            restore_accounts_proxies(player.relaunch)
                            ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)

        ui.run_in_thread(run, PlayerError, LocalproxyError)
        LogFiles(app_info.name).keep_only(keep_logs)

    except PlayerError as err:
        ui.showinfo(f"{err}\nPlease launch Sfvip Player at least once !")
        logger.warning(str(err))
    except LocalproxyError as err:
        ui.showinfo(f"{err}")
        logger.warning(str(err))
