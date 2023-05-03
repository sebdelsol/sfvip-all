import itertools
import json
import winreg
from contextlib import suppress
from pathlib import Path
from typing import IO, Any, Optional


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


class Serializer:
    """(De)serialize a nested pure class"""

    @classmethod
    def as_dict(cls) -> dict:
        return {
            k: o.as_dict() if isinstance(o, type) and issubclass(o, Serializer) else o
            for k, o in cls.__dict__.items()
            if not k.startswith("_")  # only public class attributes
        }

    @classmethod
    def map_dict(cls, dct: dict) -> None:
        for k, v in dct.items():
            if o := getattr(cls, k, None):
                if isinstance(v, dict) and isinstance(o, type) and issubclass(o, Serializer):
                    o.map_dict(v)
                else:
                    setattr(cls, k, v)


class Loader(Serializer):
    """load and save a nested pure class as json"""

    def __init_subclass__(cls, path: Path) -> None:
        cls._path = path
        return super().__init_subclass__()

    @classmethod
    def _open(cls, mode: str) -> IO:
        cls._path: Path
        return cls._path.open(mode=mode, encoding="utf-8")

    @classmethod
    def save(cls):
        with cls._open("w") as f:
            json.dump(cls.as_dict(), f, indent=2)

    @classmethod
    def load(cls):
        with cls._open("r") as f:
            cls.map_dict(json.load(f))

    @classmethod
    def update_from_json(cls) -> None:
        try:
            cls.load()
        except (json.JSONDecodeError, FileNotFoundError):
            cls.save()
