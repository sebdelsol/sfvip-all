import logging
import os
import winreg
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional, Self

from shared import get_bitness_str
from shared.version import Version
from translations.loc import LOC

from ...winapi.version import get_version_string
from ..app_info import AppInfo
from ..ui import UI
from .cpu import Cpu, is64_exe
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


class FoundExe(NamedTuple):
    exe: Path
    version: Version
    bitness: bool

    @classmethod
    def from_exe(cls, exe: Path) -> Self:
        version = Version(get_version_string(str(exe.resolve()), "FileVersion"))
        bitness = is64_exe(exe)
        return cls(exe, version, Cpu.is64 if bitness is None else bitness)

    def update(self) -> Self:
        return self.__class__.from_exe(self.exe)


class PlayerExe:
    """find the player exe"""

    _name = "sfvip player"
    _pattern = "*sf*vip*player*.exe"
    _min_version = "1.2.5.7"
    _version_without_all_channels = "1.2.5.7"

    def __init__(self, app_info: AppInfo, ui: UI) -> None:
        self._ui = ui
        self._app_info = app_info
        self._app_config = app_info.config
        self._found = self._find()
        app_info.config.Player.exe = str(self._found.exe.resolve())
        logger.info(
            "player is '%s' %s %s",
            self._found.exe,
            self._found.version,
            get_bitness_str(self._found.bitness),
        )

    @property
    def exe(self) -> Path:
        return self._found.exe

    @property
    def has_all_channels(self) -> bool:
        return self._found.version > Version(PlayerExe._version_without_all_channels)

    @property
    def found(self) -> FoundExe:
        return self._found

    @staticmethod
    def _find_from(*finders: Callable[[], Iterator[str]]) -> FoundExe | bool:
        found = None
        for find in finders:
            for exe in find():
                exe = Path(exe)
                if exe.is_file() and exe.match(PlayerExe._pattern):
                    found = FoundExe.from_exe(exe)
                    if found.version >= Version(PlayerExe._min_version):
                        return found
        return bool(found)

    def _find(self) -> FoundExe:
        if found := self._find_from(self._from_config, self._from_registry):
            if isinstance(found, FoundExe):
                return found
            self._ui.showinfo(LOC.PlayerTooOld % (PlayerExe._name.title(), PlayerExe._min_version))
        if found := self._find_from(self._from_file_or_download):
            if isinstance(found, FoundExe):
                return found
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
                exe = download_player(PlayerExe._name, self._app_info, self._app_config.Player.requests_timeout)
            if exe:
                yield exe
                break
