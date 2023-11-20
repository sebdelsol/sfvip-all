import logging
import os
import winreg
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional

from translations.loc import LOC

from ..app_info import AppInfo
from ..ui import UI
from .downloader import download_player
from .exception import PlayerNotFoundError
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


class PlayerExe:
    """find the player exe"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"

    def __init__(self, app_info: AppInfo, ui: UI) -> None:
        self._ui = ui
        self._app_info = app_info
        self._app_config = app_info.config
        self._exe = app_info.config.Player.exe = self._find()
        logger.info("player is '%s'", self._exe)

    @property
    def exe(self) -> str:
        return self._exe

    def _find(self) -> str:
        for find_exe in self._from_config, self._from_registry, self._from_file_or_download:
            for exe in find_exe():
                if (path := Path(exe)).is_file() and path.match(PlayerExe._pattern):
                    return exe
        raise PlayerNotFoundError(LOC.NotFound % PlayerExe._name.title())

    def _from_config(self) -> Iterator[str]:
        if exe := self._app_config.Player.exe:
            yield exe

    @staticmethod
    def _from_registry() -> Iterator[str]:
        logger.info("try to find the player in the registry")
        for registry_search in _registry_searches:
            if found := registry_search.method(registry_search.hkey, registry_search.path, PlayerExe._name):
                for exe in registry_search.handle_found(found):
                    yield exe

    def _from_file_or_download(self) -> Iterator[str]:
        while True:
            ok = self._ui.ask(
                f"{LOC.NotFound % PlayerExe._name.title()}\n{LOC.SearchOrDownload}",
                LOC.Search,
                LOC.Download,
            )
            if ok is None:
                break
            if ok:
                logger.info("ask the user to find the player")
                exe = self._ui.find_file(PlayerExe._name, PlayerExe._pattern)
            else:
                logger.info("try to download the player")
                exe = download_player(PlayerExe._name, self._app_info, self._app_config.App.requests_timeout)
            if exe:
                yield exe
                break
