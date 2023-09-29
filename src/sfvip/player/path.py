import logging
import os
import winreg
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional

from ..app_info import AppConfig
from ..ui import UI
from .downloader import download_player
from .exception import PlayerError
from .registry import Registry

logger = logging.getLogger(__name__)


class _RegistrySearch(NamedTuple):
    method: Callable[[int, str, Any], Optional[str]] | Callable[[int, str, str], list[str]]
    hkey: int
    path: str
    handle_found: Callable[[Any], list[str]]


_registry_searches = (
    _RegistrySearch(
        Registry.name_by_value,
        winreg.HKEY_CLASSES_ROOT,
        r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache",
        lambda found: [os.path.splitext(found)[0]],
    ),
    _RegistrySearch(
        Registry.search_name_contains,
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store",
        lambda found: found,
    ),
)


def player_from_registry(player_name: str) -> Iterator[str]:
    for search in _registry_searches:
        if found := search.method(search.hkey, search.path, player_name):
            for player in search.handle_found(found):
                yield player


class PlayerPath:
    """find the player exe"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"

    def __init__(self, app_config: AppConfig, ui: UI) -> None:
        self._ui = ui
        self._app_config = app_config
        player = app_config.Player.path
        if not self._valid_exe(player):
            player = self._find_player()
        assert player
        self.path = app_config.Player.path = player
        logger.info("player is '%s'", self.path)

    def _find_player(self) -> str:
        for find_player_method in (
            self._player_from_registry,
            self._player_from_user,
            self._player_from_download,
        ):
            for player in find_player_method():
                if self._valid_exe(player):
                    return player
        raise PlayerError("Sfvip Player not found")

    @staticmethod
    def _valid_exe(path: Optional[Path | str]) -> bool:
        return bool(path and (_path := Path(path)).is_file() and _path.match(PlayerPath._pattern))

    @staticmethod
    def _player_from_registry() -> Iterator[str]:
        logger.info("try to find the player in the registry")
        for player in player_from_registry(PlayerPath._name):
            yield player

    # TODO single window for both _player_from_user and _player_from_download
    def _player_from_user(self) -> Iterator[str]:
        self._ui.showinfo(f"Please find {PlayerPath._name.capitalize()}")
        while True:
            logger.info("ask the user to find the player")
            if player := self._ui.find_file(PlayerPath._name, PlayerPath._pattern):
                yield player
            if not self._ui.askretry(message=f"{PlayerPath._name.capitalize()} not found, try again ?"):
                break

    def _player_from_download(self) -> Iterator[str]:
        if self._ui.askyesno(message=f"Download {PlayerPath._name.capitalize()} ?"):
            logger.info("try to download the player")
            if player := download_player(PlayerPath._name, timeout=self._app_config.App.requests_timeout):
                yield player
