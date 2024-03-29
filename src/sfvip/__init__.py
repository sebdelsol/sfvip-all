import logging

from translations.loc import LOC

from .accounts import AccountsProxies
from .app_info import AppInfo
from .app_updater import AltLastRegisterT, AppAutoUpdater, AppUpdater
from .exceptions import LocalproxyError, PlayerNotFoundError
from .player import Player, PlayerLanguageLoader
from .ui import UI
from .utils.clean_files import CleanFilesIn

logger = logging.getLogger(__name__)


def run_app(at_last_register: AltLastRegisterT, app_info: AppInfo, keep_logs: int) -> None:
    logger.info("Run %s %s %s", app_info.name, app_info.version, app_info.bitness)
    exceptions = PlayerNotFoundError, LocalproxyError
    LOC.set_tranlastions(app_info.translations)
    LOC.set_language(PlayerLanguageLoader().language)
    app_config = app_info.config.update()
    ui = UI(app_info)
    try:
        player = Player(app_info, ui)
        # for faster startup perception
        ui.splash.show(player.rect)
        # pylint: disable=import-outside-toplevel
        from .proxies import LocalProxies

        app_updater = AppUpdater(app_info, at_last_register)
        app_auto_updater = AppAutoUpdater(app_updater, app_config, ui, player.stop)

        def run() -> None:
            while player.want_to_launch():
                ui.splash.show(player.rect)
                accounts_proxies = AccountsProxies(app_info.roaming, ui)
                with LocalProxies(app_info, player.capabilities, accounts_proxies, ui) as local_proxies:
                    with accounts_proxies.set(local_proxies.by_upstreams) as restore_accounts_proxies:
                        with app_auto_updater:
                            with player.run():
                                restore_accounts_proxies(player.relaunch)
                                ui.splash.hide(fade_duration_ms=1000, wait_ms=1000)

        ui.run_in_thread(run, *exceptions)
    except exceptions as err:
        ui.showinfo(str(err), force_create=True)
        logger.warning(str(err).capitalize())
    finally:
        ui.quit()
        CleanFilesIn(app_info.logs_dir).keep(keep_logs, f"{app_info.name} - *.log")
