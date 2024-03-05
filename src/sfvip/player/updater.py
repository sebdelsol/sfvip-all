import logging
import re
import threading
from pathlib import Path
from typing import Optional, Protocol, Self

import requests

from shared import get_bitness_str
from shared.version import Version
from translations.loc import LOC

from ..app_info import AppConfig
from ..ui import UI
from ..ui.window import AskWindow
from ..utils.guardian import ThreadGuardian
from ..utils.scheduler import Scheduler
from .downloader import update_player
from .find_exe import PlayerExe

logger = logging.getLogger(__name__)


class PlayerLatestUpdate:
    _url = "https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/main/Update.json"
    _changelong_title = "Sfvip Player changelog:"
    _re_version = re.compile(r"^v([\d\.]+)")
    _key_version = "tag_name"

    def __init__(self, ui: UI) -> None:
        self._changelogs: list[str] = []
        ui.set_changelog_callback(self.get_changelog)

    def get_changelog(self) -> str:
        return "\n\n".join(
            (
                PlayerLatestUpdate._changelong_title,
                *(f" • {changelog}" for changelog in self._changelogs),
            )
        )

    def get_version(self, timeout: int) -> Optional[Version]:
        try:
            with requests.get(PlayerLatestUpdate._url, timeout=timeout) as response:
                response.raise_for_status()
                changelog = response.json()[PlayerLatestUpdate._key_version]
                if changelog not in self._changelogs:
                    self._changelogs.append(changelog)
                version = PlayerLatestUpdate._re_version.findall(changelog)[0]
                return Version(version)
        except (requests.RequestException, KeyError, IndexError):
            return None


class PlayerUpdater:
    def __init__(self, player_exe: PlayerExe, app_config: AppConfig, ui: UI) -> None:
        self._timeout = app_config.Player.requests_timeout
        self._player_exe = player_exe
        self._current = player_exe.found
        self._player_latest_update = PlayerLatestUpdate(ui)

    def is_new(self, version: Version) -> bool:
        return version > self._current.version

    def get_current_version_str(self) -> str:
        return f"{self._current.version} {get_bitness_str(self._current.bitness)}"

    def get_latest_version(self) -> Optional[Version]:
        logger.info("Check latest Sfvip Player version")
        if version := self._player_latest_update.get_version(self._timeout):
            logger.info("Found update Sfvip Player %s", version)
            return version
        logger.warning("Check latest Sfvip Player failed")
        return None

    def install(self) -> None:
        while True:
            if not self._can_install():
                break
            if update_player(self._current.exe, self._current.bitness, self._timeout):
                self._current = self._player_exe.found.update()
                break
            if not self._ask("Sfvip Player", LOC.UpgradeFailed, LOC.Retry):
                break

    def _can_install(self) -> bool:
        while True:
            try:
                # could write the player exe == it's not running
                with Path(self._current.exe).open("ab"):
                    return True
            except PermissionError:
                if not self._ask("Sfvip Player", LOC.AlreadyRunning, LOC.Retry):
                    return False

    @staticmethod
    def _ask(name: str, message: str, ok: str) -> bool:
        def _ask() -> bool:
            ask_win.wait_window()
            return bool(ask_win.ok)

        ask_win = AskWindow(f"{LOC.Install} {name}", message % name, ok, LOC.Cancel)
        return bool(ask_win.run_in_thread(_ask))

    def ask_install(self, version: Version) -> bool:
        return self._ask(f"Sfvip Player {version}", LOC.RestartInstall, LOC.Install)


# prevent execution if already in use in another thread
_updating = ThreadGuardian()


class SetRelaunchT(Protocol):
    def __call__(self, sleep_duration_s: float = ..., can_relaunch: Optional[threading.Event] = ...) -> None: ...


class PlayerAutoUpdater:
    def __init__(
        self, player_exe: PlayerExe, app_config: AppConfig, ui: UI, relaunch_player: SetRelaunchT
    ) -> None:
        self._player_updater = PlayerUpdater(player_exe, app_config, ui)
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
