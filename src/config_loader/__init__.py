import json
import logging
import sys
from os.path import getmtime
from pathlib import Path
from types import FunctionType, MethodType, SimpleNamespace
from typing import IO, Any, Iterator, Self, cast, get_type_hints

from ..winapi import mutex

logger = logging.getLogger(__name__)


def _public_non_method(dct: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for k, v in dct.items():
        if not k.startswith("_") and not isinstance(v, (MethodType, FunctionType)):
            yield k, v


class ConfigLoader:
    """
    load & save as json a pure nested class in a module
    validate types @ save and load
    note: all fields starting with _ are removed
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._name = self.__class__.__name__
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
        logger.info("%s saved to '%s'", self._name, self._path)

    def load(self) -> None:
        with self._open("r") as f:
            self._map_dict_to(self, json.load(f))
        logger.info("%s loaded from '%s'", self._name, self._path)

    def update(self) -> None:
        try:
            if not self._im_newer():
                self.load()
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        # always save if the config file needs some fixes
        self.save()

    def _update_field(self, path_str: str, value: Any) -> bool:
        fields = path_str.split(".")
        *path, field = fields
        config: Self | SimpleNamespace = self
        for name in path:
            if not hasattr(config, name):
                return True
            config = getattr(config, name)
        if hasattr(config, field):
            if getattr(config, field) != value:
                # check hint if available
                hint = get_type_hints(config).get(field) if hasattr(config, "__annotations__") else None
                # pylint: disable=isinstance-second-argument-not-valid-type
                if not hint or isinstance(value, hint):
                    setattr(config, field, value)
                    logger.info("%s.%s updated", self._name, ".".join(fields))
                    return True
        return False

    def update_field(self, path_str: str, value: Any) -> None:
        if self._update_field(path_str, value):
            self.save()

    def update_fields(self, *paths_values: tuple[str, Any]) -> None:
        updated = False
        for path, value in paths_values:
            updated |= self._update_field(path, value)
        if updated:
            self.save()

    def _im_newer(self) -> bool:
        # launched by nuitka ?
        if "__compiled__" in globals():
            return False
        module_file = sys.modules[self.__module__].__file__
        return bool(module_file and getmtime(module_file) > getmtime(self._path))

    def _dict_from(self, config: Self | SimpleNamespace) -> dict[str, Any]:
        """recursively get a dict from SimpleNamespace with fields validation & default values"""
        dct = {}
        for name, obj in _public_non_method(config.__dict__):
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
        for name, obj in _public_non_method(dct):
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
        for name, obj in _public_non_method(dct):
            if isinstance(obj, type):
                self._to_simplenamespace(ns := SimpleNamespace(), dict(obj.__dict__))
                setattr(config, name, ns)
                # add typing hints
                ns.__annotations__ = obj.__annotations__
            else:
                setattr(config, name, obj)
        # add defaults values
        config.__defaults__ = dict(_public_non_method(config.__dict__))  # type: ignore
