import os
import winreg
from typing import Any, Callable, Iterator, NamedTuple, Optional

from ..registry import Registry


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
