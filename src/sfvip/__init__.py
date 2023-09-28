import logging
import sys
from pathlib import Path

from .accounts import AccountsProxies
from .app_config import Config
from .app_info import AppInfo
from .app_updater import AltLastRegisterT, AppAutoUpdater, AppUpdater
from .player import Player
from .player.exception import PlayerError
from .proxies import LocalProxies, LocalproxyError
from .ui import UI

logger = logging.getLogger(__name__)


class CleanFilesIn:
    def __init__(self, path: Path) -> None:
        self._path = path

    @staticmethod
    def _unlink(file: Path) -> bool:
        try:
            file.unlink(missing_ok=True)
            return True
        except PermissionError:
            return False

    def keep(self, keep: int, pattern: str) -> None:
        # remove empty files
        files = self._path.glob(pattern)
        files = [file for file in files if not (file.stat().st_size == 0 and self._unlink(file))]
        # keep only #keep files
        if len(files) > keep:
            logger.info("keep the last %d '%s' files", keep, pattern)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for file in files[keep:]:
                self._unlink(file)


def run_app(
    at_last_register: AltLastRegisterT, app_info: AppInfo, splash: Path, logo: Path, keep_logs: int
) -> None:
    logger.info("run %s %s %s", app_info.name, app_info.version, app_info.bitness)
    ui = UI(app_info, splash, logo)
    try:
        exe_dir = Path(sys.argv[0]).parent
        clean_files = CleanFilesIn(exe_dir)
        clean_files.keep(1, f"{app_info.name}*.old.exe")
        config = Config(app_info.roaming)
        player = Player(config, ui)
        app_updater = AppUpdater(app_info, config.app_requests_timeout, at_last_register)
        app_auto_updater = AppAutoUpdater(app_updater, config, ui, player.stop)

        def run() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts_proxies = AccountsProxies(app_info.roaming, ui)
                with LocalProxies(config.all_category, accounts_proxies.upstreams) as local_proxies:
                    with accounts_proxies.set(local_proxies.by_upstreams) as restore_accounts_proxies:
                        with app_auto_updater:
                            with player.run():
                                restore_accounts_proxies(player.relaunch)
                                ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)
            ui.quit()

        ui.run_in_thread(run, PlayerError, LocalproxyError)
        clean_files.keep(keep_logs, f"{app_info.name} - *.log")

    except PlayerError as err:
        ui.showinfo(f"{err}\nPlease launch Sfvip Player at least once !")
        logger.warning(str(err))
    except LocalproxyError as err:
        ui.showinfo(f"{err}")
        logger.warning(str(err))
