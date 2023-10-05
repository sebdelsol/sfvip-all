import logging
import sys
from pathlib import Path

from .accounts import AccountsProxies
from .app_info import AppInfo
from .app_updater import AltLastRegisterT, AppAutoUpdater, AppUpdater
from .localization import LOC
from .player import Player, PLayerLanguageLoader
from .player.exception import PlayerNotFoundError
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
        files = [file for file in files if file.stat().st_size or not self._unlink(file)]
        # keep only #keep files
        if len(files) > keep:
            logger.info("keep the last %d '%s' files", keep, pattern)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for file in files[keep:]:
                self._unlink(file)


exceptions = PlayerNotFoundError, LocalproxyError


def run_app(at_last_register: AltLastRegisterT, app_info: AppInfo, keep_logs: int) -> None:
    logger.info("run %s %s %s", app_info.name, app_info.version, app_info.bitness)
    LOC.set_language(PLayerLanguageLoader().language).apply_language(app_info.translations)
    ui = UI(app_info)
    app_config = app_info.config
    app_config.update()
    clean_files = CleanFilesIn(Path(sys.argv[0]).parent)  # in exe dir
    clean_files.keep(1, f"{app_info.name}*.{AppUpdater.old_exe}")
    clean_files.keep(1, f"{app_info.name}*.{AppUpdater.update_exe}")
    try:
        player = Player(app_config, ui)
        app_updater = AppUpdater(app_info, at_last_register)
        app_auto_updater = AppAutoUpdater(app_updater, app_config, ui, player.stop)

        def run() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts_proxies = AccountsProxies(app_info.roaming, ui)
                with LocalProxies(app_config.AllCategory, accounts_proxies.upstreams) as local_proxies:
                    with accounts_proxies.set(local_proxies.by_upstreams) as restore_accounts_proxies:
                        with app_auto_updater:
                            with player.run():
                                restore_accounts_proxies(player.relaunch)
                                ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)

        ui.run_in_thread(run, *exceptions)

    except exceptions as err:
        ui.showinfo(str(err), force_create=True)
        logger.warning(str(err))
    finally:
        ui.quit()
        clean_files.keep(keep_logs, f"{app_info.name} - *.log")
