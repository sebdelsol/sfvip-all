import itertools
import winreg
from contextlib import suppress
from typing import Any, Optional


class RegKey:
    """find stuff in the registry"""

    @staticmethod
    def name_by_value(hkey: int, path: str, searched_value: Any) -> Optional[str]:
        with suppress(WindowsError), winreg.OpenKey(hkey, path) as key:
            for i in itertools.count():
                name, value, _ = winreg.EnumValue(key, i)
                if value == searched_value:
                    return name
        return None

    @staticmethod
    def value_by_name(hkey: int, path: str, name: str) -> Optional[Any]:
        with suppress(WindowsError, FileNotFoundError), winreg.OpenKey(hkey, path) as k:
            value = winreg.QueryValueEx(k, name)[0]
            return value
        return None

    @staticmethod
    def search_name_contains(hkey: int, path: str, substring: str) -> list[str]:
        names: list[str] = []
        with suppress(WindowsError), winreg.OpenKey(hkey, path) as key:
            for i in itertools.count():
                name = winreg.EnumValue(key, i)[0]
                if substring in name:
                    names.append(name)
        return names
