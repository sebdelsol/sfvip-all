import logging
import re
import threading
import time
from pathlib import Path
from typing import Optional, Protocol, Self

import requests

from shared.version import Version
from translations.loc import LOC

from ..app_info import AppConfig
from ..ui import UI
from ..ui.window import AskWindow
from ..utils.guardian import ThreadGuardian
from ..utils.scheduler import Scheduler
from .downloader import upgrade_player
from .find_exe import PlayerExe

logger = logging.getLogger(__name__)


class PlayerLatestUpdate:
    _url = "https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/main/Update.json"
    _re_version = r"^v([\d\.]+)"
    _key_version = "tag_name"

    @staticmethod
    def get_version(timeout: int) -> Optional[Version]:
        try:
            with requests.get(PlayerLatestUpdate._url, timeout=timeout) as response:
                response.raise_for_status()
                name = response.json()[PlayerLatestUpdate._key_version]
                version = re.findall(PlayerLatestUpdate._re_version, name)[0]
                return Version(version)
        except (requests.RequestException, KeyError, IndexError):
            return None


class PlayerUpdater:
    def __init__(self, player_exe: PlayerExe, app_config: AppConfig) -> None:
        self._timeout = app_config.Player.requests_timeout
        self._player_exe = player_exe
        self._current = player_exe.update_found()

    def is_new(self, version: Version) -> bool:
        return version > self._current.version

    def get_current_version_str(self) -> str:
        return f"{self._current.version} {self._current.bitness}"

    def get_latest_version(self) -> Optional[Version]:
        logger.info("check latest Sfvip Player version")
        if version := PlayerLatestUpdate().get_version(self._timeout):
            logger.info("found update Sfvip Player %s", version)
            return version
        logger.warning("check latest Sfvip Player failed")
        return None

    def install(self) -> None:
        if self._can_install():
            # TODO use bitness of the player
            upgrade_player(Path(self._player_exe.exe), self._timeout)
            self._current = self._player_exe.update_found()

    def _can_install(self) -> bool:
        while True:
            try:
                time.sleep(0.5)  # needed for the player to actually stop
                with Path(self._current.exe).open("ab"):
                    # could write the player exe == it's not running
                    return True
            except PermissionError:
                if not self._ask_retry():
                    return False

    @staticmethod
    def _ask(name: str, message: str, ok: str) -> bool:
        def _ask() -> bool:
            ask_win.wait_window()
            return bool(ask_win.ok)

        ask_win = AskWindow(f"{LOC.Install} {name}", message % name, ok, LOC.Cancel)
        return bool(ask_win.run_in_thread(_ask))

    def _ask_retry(self) -> bool:
        return self._ask("Sfvip Player", LOC.AlreadyRunning, LOC.Retry)

    def ask_install(self, version: Version) -> bool:
        return self._ask(f"Sfvip Player {version}", LOC.RestartInstall, LOC.Install)


# prevent execution if already in use in another thread
_updating = ThreadGuardian()


class SetRelaunchT(Protocol):
    def __call__(self, sleep_duration_s: float = ..., can_relaunch: Optional[threading.Event] = ...) -> None:
        ...


class PlayerAutoUpdater:
    def __init__(
        self, player_exe: PlayerExe, app_config: AppConfig, ui: UI, relaunch_player: SetRelaunchT
    ) -> None:
        self._player_updater = PlayerUpdater(player_exe, app_config)
        self._relaunch_player = relaunch_player
        self._scheduler = Scheduler()
        self._app_config = app_config
        self._ui = ui

    def __enter__(self) -> Self:
        self._ui.set_player_version(self._player_updater.get_current_version_str())
        self._ui.set_player_auto_update(self._app_config.Player.auto_update, self._on_auto_update_changed)
        return self

    def __exit__(self, *_) -> None:
        self._scheduler.cancel_all()

    def _on_auto_update_changed(self, auto_update: bool) -> None:
        self._app_config.Player.auto_update = auto_update
        self._scheduler.cancel_all()
        if auto_update:
            self._scheduler.next(self._check, 0)
        else:
            self._ui.set_player_update()

    @_updating
    def _check(self, cancelled: threading.Event) -> None:
        version = self._player_updater.get_latest_version()
        if not cancelled.is_set():
            self._scheduler.cancel_all()
            if version:

                @_updating
                def install() -> None:
                    assert version
                    self._ui.set_player_updating()
                    if self._player_updater.ask_install(version):
                        can_relaunch = threading.Event()
                        self._relaunch_player(0, can_relaunch)
                        self._player_updater.install()
                        can_relaunch.set()
                    else:
                        self._ui.set_player_update(LOC.Install, install, str(version))

                if self._player_updater.is_new(version):
                    self._ui.set_player_update(LOC.Install, install, str(version))
            else:
                self._scheduler.next(self._check, self._app_config.Player.retry_minutes * 60)
