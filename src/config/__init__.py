import json
import logging
import sys
from os.path import getmtime
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Any, Iterator, Self, cast, get_type_hints

from ..winapi import mutex

logger = logging.getLogger(__name__)


def _public_only(dct: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for k, v in dct.items():
        if not k.startswith("_"):
            yield k, v


class ConfigLoader:
    """
    load & save as json a pure nested class in a module
    validate types @ save and load
    note: all fields starting with _ are removed
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file_lock = mutex.SystemWideMutex(f"file lock for {path}")
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
        # always save if the config file needs some fixes
        self.save()

    def _im_newer(self) -> bool:
        if "__compiled__" in globals():  # launched as an exe build by nuitka ?
            return False
        module_file = sys.modules[self.__module__].__file__
        return bool(module_file and getmtime(module_file) > getmtime(self._path))

    def _dict_from(self, config: Self | SimpleNamespace) -> dict[str, Any]:
        """recursively get a dict from SimpleNamespace with fields validation & default values"""
        dct = {}
        for name, obj in _public_only(config.__dict__):
            if hasattr(config, name):
                if isinstance(obj, SimpleNamespace):
                    dct[name] = self._dict_from(obj)
                else:
                    # check typing hint if available
                    hint = get_type_hints(config).get(name) if hasattr(config, "__annotations__") else None
                    if not hint or isinstance(obj, hint):
                        dct[name] = obj
                    else:
                        dct[name] = config.__defaults__[name]  # type: ignore
        return dct

    def _map_dict_to(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        """recursively map a dict to SimpleNamespace with fields validation & default values"""
        for name, obj in _public_only(dct):
            if hasattr(config, name):
                if isinstance(obj, dict) and isinstance(ns := getattr(config, name), SimpleNamespace):
                    self._map_dict_to(ns, cast(dict[str, Any], obj))
                else:
                    # check hint if available
                    hint = get_type_hints(config).get(name) if hasattr(config, "__annotations__") else None
                    if not hint or isinstance(obj, hint):
                        setattr(config, name, obj)

    def _to_simplenamespace(self, config: Self | SimpleNamespace, dct: dict[str, Any]) -> None:
        """recursively turn a class into SimpleNamespace with typing hints & default values"""
        for name, obj in _public_only(dct):
            if isinstance(obj, type):
                self._to_simplenamespace(ns := SimpleNamespace(), dict(obj.__dict__))
                setattr(config, name, ns)
                # add typing hints
                ns.__annotations__ = obj.__annotations__
            else:
                setattr(config, name, obj)
        # add defaults values
        config.__defaults__ = dict(_public_only(config.__dict__))  # type: ignore
