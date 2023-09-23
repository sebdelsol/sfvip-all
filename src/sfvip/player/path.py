import logging
import os
import winreg
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional

from ..config import Config
from ..registry import Registry
from ..ui import UI
from ..update import download_player
from .exception import PlayerError

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

    def __init__(self, config: Config, ui: UI) -> None:
        player = config.player_path
        if not self._valid_exe(player):
            player = self._find_player(ui)
        assert player
        self.path = config.player_path = player
        logger.info("player is '%s'", self.path)

    def _find_player(self, ui: UI) -> str:
        for find_player_method in (
            self._player_from_registry,
            self._player_from_user,
            self._player_from_download,
        ):
            for player in find_player_method(ui):
                if self._valid_exe(player):
                    return player
        raise PlayerError("Sfvip Player not found")

    @staticmethod
    def _valid_exe(path: Optional[Path | str]) -> bool:
        return bool(path and (_path := Path(path)).is_file() and _path.match(PlayerPath._pattern))

    @staticmethod
    def _player_from_registry(_) -> Iterator[str]:
        logger.info("try to find the player in the registry")
        for player in player_from_registry(PlayerPath._name):
            yield player

    # TODO single window for both _player_from_user and _player_from_download
    @staticmethod
    def _player_from_user(ui: UI) -> Iterator[str]:
        ui.showinfo(f"Please find {PlayerPath._name.capitalize()}")
        while True:
            logger.info("ask the user to find the player")
            if player := ui.find_file(PlayerPath._name, PlayerPath._pattern):
                yield player
            if not ui.askretry(message=f"{PlayerPath._name.capitalize()} not found, try again ?"):
                break

    @staticmethod
    def _player_from_download(ui: UI) -> Iterator[str]:
        if ui.askyesno(message=f"Download {PlayerPath._name.capitalize()} ?"):
            logger.info("try to download the player")
            if player := download_player(PlayerPath._name):
                yield player
