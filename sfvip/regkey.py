import itertools
import winreg
from contextlib import suppress
from typing import Any, Optional


class RegKey:
    """find stuff in the registry"""

    @staticmethod
    def name_by_value(hkey: winreg.HKEYType, path: str, searched_value: Any) -> Optional[str]:
        with suppress(WindowsError), winreg.OpenKey(hkey, path) as key:
            for i in itertools.count():
                name, value, _ = winreg.EnumValue(key, i)
                if value == searched_value:
                    return name
        return None

    @staticmethod
    def value_by_name(hkey: winreg.HKEYType, path: str, name: str) -> Optional[Any]:
        with suppress(WindowsError, FileNotFoundError), winreg.OpenKey(hkey, path) as k:
            value, _ = winreg.QueryValueEx(k, name)
            return value
        return None