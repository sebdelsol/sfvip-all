import json
import logging
import sys
from os.path import getmtime
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Any, Iterator, Self, cast

from mutex import SystemWideMutex

logger = logging.getLogger(__name__)


class ConfigLoader:
    """load & save as json a pure nested class"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file_lock = SystemWideMutex(f"file lock for {path}")
        # turn all config nested classes into SimpleNamespace instance attributes
        self._to_simplenamespace(self, self.__class__.__dict__)

    def _open(self, mode: str) -> IO[str]:
        with self._file_lock:
            return self._path.open(mode, encoding="utf-8")

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._open("w") as f:
            json.dump(self._dict_from(self), f, indent=2)
        logger.info("config saved to %s", self._path)

    def load(self) -> None:
        with self._open("r") as f:
            self._map_dict_to(self, json.load(f))
        logger.info("config loaded from %s", self._path)

    def update(self) -> None:
        try:
            if not self._im_newer():
                self.load()
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        self.save()  # save always to potentially fix the config file

    def _im_newer(self) -> bool:
        if "__compiled__" in globals():  # launched as an exe build by nuitka ?
            return False
        module_file = sys.modules[self.__module__].__file__
        return bool(module_file and getmtime(module_file) > getmtime(self._path))

    @staticmethod
    def _public_only(dct: dict[str, Any]) -> Iterator[tuple[str, Any]]:
        for k, v in dct.items():
            if not k.startswith("_"):
                yield k, v

    def _dict_from(self, config: Self | SimpleNamespace) -> dict[str, Any]:
        return {
            k: self._dict_from(obj) if isinstance(obj, SimpleNamespace) else obj
            for k, obj in self._public_only(config.__dict__)
        }

    def _map_dict_to(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        for k, v in self._public_only(dct):
            if hasattr(config, k):
                if isinstance(v, dict) and isinstance(obj := getattr(config, k), SimpleNamespace):
                    self._map_dict_to(obj, cast(dict[str, Any], v))
                else:
                    setattr(config, k, v)

    def _to_simplenamespace(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        for k, v in self._public_only(dct):
            if isinstance(v, type):
                self._to_simplenamespace(obj := SimpleNamespace(), dict(v.__dict__))
                setattr(config, k, obj)
            else:
                setattr(config, k, v)
