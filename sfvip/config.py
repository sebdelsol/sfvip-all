import json
from os.path import getmtime
from pathlib import Path
from types import ModuleType
from typing import IO


def _launched_by_noitka() -> bool:
    return "__compiled__" in globals()


class ModuleIsNewer(Exception):
    pass


class AppConfigLoader:
    """load & save as json a py module populated with str, int or pure class"""

    def __init__(self, config: ModuleType, path: Path) -> None:
        self._path = path
        self._config = config

    def _open(self, mode: str) -> IO:
        return self._path.open(mode=mode, encoding="utf-8")

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._open("w") as f:
            json.dump(self._dict_from(self._config), f, indent=2)

    def load(self):
        with self._open("r") as f:
            self._map_dict_to(json.load(f), self._config)

    def update(self) -> None:
        try:
            self._raise_on_newer_module()
            self.load()
        except (json.JSONDecodeError, FileNotFoundError, ModuleIsNewer):
            self.save()

    def _raise_on_newer_module(self) -> None:
        if not _launched_by_noitka():
            if getmtime(self._config.__file__) > getmtime(self._path):
                raise ModuleIsNewer

    def _dict_from(self, config: type) -> dict:
        return {
            k: self._dict_from(o) if isinstance(o, type) else o
            for k, o in config.__dict__.items()
            if not k.startswith("_")  # only public class attributes
        }

    def _map_dict_to(self, dct: dict, config: type) -> None:
        for k, v in dct.items():
            if hasattr(config, k):
                o = getattr(config, k)
                if isinstance(v, dict) and isinstance(o, type):
                    self._map_dict_to(v, o)
                else:
                    setattr(config, k, v)
