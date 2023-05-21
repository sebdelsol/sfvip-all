import json
import sys
from os.path import getmtime
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Any, Iterator, Self, cast

from .mutex import SystemWideMutex


def _launched_by_noitka() -> bool:
    return "__compiled__" in globals()


class ModuleIsNewer(Exception):
    pass


class Loader:
    """load & save as json a py module populated with str, int or pure class"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file_lock = SystemWideMutex(f"file lock for {path}")
        # each nested classes is turned into a SimpleNamespace attached to self
        self._to_simplenamespace(self, self.__class__.__dict__)

    def _open(self, mode: str) -> IO[str]:
        with self._file_lock:
            return self._path.open(mode, encoding="utf-8")

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._open("w") as f:
            json.dump(self._dict_from(self), f, indent=2)

    def load(self) -> None:
        with self._open("r") as f:
            self._map_dict_to(self, json.load(f))

    def update(self) -> None:
        try:
            self._raise_if_im_newer()
            self.load()
        except (json.JSONDecodeError, FileNotFoundError, ModuleIsNewer):
            self.save()

    def _raise_if_im_newer(self) -> None:
        if not _launched_by_noitka():
            module_file = sys.modules[self.__module__].__file__
            if module_file and getmtime(module_file) > getmtime(self._path):
                raise ModuleIsNewer

    @staticmethod
    def _public_items_only(dct: dict[str, Any]) -> Iterator[tuple[str, Any]]:
        for k, v in dct.items():
            if not k.startswith("_"):
                yield k, v

    def _dict_from(self, config: Self | SimpleNamespace) -> dict[str, Any]:
        return {
            k: self._dict_from(obj) if isinstance(obj, SimpleNamespace) else obj
            for k, obj in self._public_items_only(config.__dict__)
        }

    def _map_dict_to(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        for k, v in self._public_items_only(dct):
            if hasattr(config, k):
                if isinstance(v, dict) and isinstance(obj := getattr(config, k), SimpleNamespace):
                    self._map_dict_to(obj, cast(dict[str, Any], v))
                else:
                    setattr(config, k, v)

    def _to_simplenamespace(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        for k, v in self._public_items_only(dct):
            if isinstance(v, type):
                self._to_simplenamespace(obj := SimpleNamespace(), dict(v.__dict__))
                setattr(config, k, obj)
            else:
                setattr(config, k, v)
