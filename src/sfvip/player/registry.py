import itertools
import winreg
from contextlib import suppress
from typing import Any, Optional


class Registry:
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
        with suppress(WindowsError, FileNotFoundError), winreg.OpenKey(hkey, path) as key:
            value = winreg.QueryValueEx(key, name)[0]
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

    @staticmethod
    def create_key(hkey: int, path: str, name: str, value: str) -> None:
        with suppress(WindowsError), winreg.CreateKey(hkey, path) as key:
            with suppress(WindowsError), winreg.OpenKey(hkey, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
