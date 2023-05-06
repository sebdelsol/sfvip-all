import json
import sys
from os.path import getmtime
from pathlib import Path
from types import ModuleType
from typing import IO


def _is_bundled() -> bool:
    """launched by either pyinstaller or nuitka ?"""
    is_pyinstaller = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    is_nuitka = "__compiled__" in globals()
    return is_pyinstaller or is_nuitka


class Loader:
    """load & save as json a py module populated with str, int or pure class"""

    def __init__(self, config: ModuleType, path: Path) -> None:
        self._path = path
        self._config = config

    def _open(self, mode: str) -> IO:
        return self._path.open(mode=mode, encoding="utf-8")

    def save(self):
        with self._open("w") as f:
            json.dump(self._as_dict(self._config), f, indent=2)

    def load(self):
        with self._open("r") as f:
            self._map_dict(self._config, json.load(f))

    def update_from_json(self) -> None:
        try:
            self._raise_if_newer()
            self.load()
        except (json.JSONDecodeError, FileNotFoundError):
            self.save()

    def _raise_if_newer(self) -> None:
        if not _is_bundled():
            if getmtime(self._config.__file__) > getmtime(self._path):
                raise FileNotFoundError

    def _as_dict(self, config: type) -> dict:
        return {
            k: self._as_dict(o) if isinstance(o, type) else o
            for k, o in config.__dict__.items()
            if not k.startswith("_")  # only public class attributes
        }

    def _map_dict(self, config: type, dct: dict) -> None:
        for k, v in dct.items():
            if hasattr(config, k):
                o = getattr(config, k)
                if isinstance(v, dict) and isinstance(o, type):
                    self._map_dict(o, v)
                else:
                    setattr(config, k, v)
