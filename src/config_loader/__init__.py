import json
import logging
import sys
from os.path import getmtime
from pathlib import Path
from types import FunctionType, MappingProxyType, MethodType, SimpleNamespace
from typing import IO, Any, Iterator, Literal, Optional, Self, cast, get_type_hints

from shared import is_built

from ..winapi import mutex

logger = logging.getLogger(__name__)

""" How to use !
# Create a subclass of ConfigLoader
# It's better to add type hints and default value for all fields
class DefaultConfig(ConfigLoader):
    a_bool: bool = True

    class Nested:
        a_bool: Optional[bool] = None
        a_string: str = "I'm a string"

        class NestedDeeper:
            where_am_I : str = "Uh ?"

# Instantiate this config to link it to a file
config = DefaultConfig(Path("config.json"))

# The json file is read or created with default values
config.update()  # "config.json" file is created with default values

# Your IDE auto complete works :)
print(config.a_bool)  # True

# Set an attribute: it'll be skipped if it's the wrong type
config.Nested.a_bool = "I want to be true"
print(config.Nested.a_bool)  # still None

# Set an attribute: it'll be automatically saved if changed
config.Nested.a_string = "Lorem Ipsum ..."
config.load()
print(config.Nested.a_string)  # "Lorem Ipsum ..."

# Go deeper
print(config.Nested.NestedDeeper.where_am_I)  # "Uh ?"
"""


def _is_public_attribute(key: str, value: Any) -> bool:
    return not key.startswith("_") and not isinstance(value, (MethodType, FunctionType))


def _public_attributes(dct: MappingProxyType[str, Any] | dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for key, value in dct.items():
        if _is_public_attribute(key, value):
            yield key, value


class _ProxyNamespace(SimpleNamespace):
    __slots__ = ("_config",)

    def __init__(self, config: "ConfigLoader", **kwargs: Any) -> None:
        self._config = config
        super().__init__(**kwargs)

    def __getattribute__(self, key: str) -> Any:
        attr = super().__getattribute__(key)
        if _is_public_attribute(key, attr) and isinstance(attr, _ProxyNamespace):
            self._config.append_path(key)
        return attr

    def __setattr__(self, key: str, value: Any) -> None:
        try:
            attr = super().__getattribute__(key)
            if _is_public_attribute(key, attr) and not isinstance(attr, _ProxyNamespace):
                self._config.setattr(key, value)
        except AttributeError:
            super().__setattr__(key, value)

    def setattr(self, key: str, value: Any) -> None:
        super().__setattr__(key, value)

    def getattr(self, key: str) -> Any:
        return super().__getattribute__(key)

    def hasattr(self, key: str) -> bool:
        try:
            super().__getattribute__(key)
            return True
        except AttributeError:
            return False


def is_right_type(proxy: _ProxyNamespace, key: str, value: Any) -> bool:
    """check hint if available"""
    hint = get_type_hints(proxy).get(key) if hasattr(proxy, "__annotations__") else None
    return bool(not hint or isinstance(value, hint))


class ConfigLoader:
    """
    load & save as json a pure nested class
    validate types @ save and load
    note: all fields starting with _ are removed
    """

    __slots__ = "_inner", "_file", "_path", "_name", "_file_lock", "_base_proxy", "_check_newer"
    _default: Optional[type] = None
    _module_file: Optional[str] = None

    def __init_subclass__(cls) -> None:
        if not cls._default:
            # defaults are stored in the 1st child
            cls._default = cls
            cls._module_file = sys.modules[cls.__module__].__file__

    def __init__(self, file: Path, check_newer: bool = True) -> None:
        ConfigLoader._not_in_inner = set(dict(ConfigLoader.__dict__).keys())
        ConfigLoader._not_in_inner.update(set(dict(_ProxyNamespace.__dict__).keys()))
        self._check_newer = check_newer and not is_built()
        self._name = self.__class__.__name__
        self._path: list[str] = []
        self._file = file
        self._file_lock = mutex.SystemWideMutex(f"file lock for {file}")
        # turn all config nested classes into _ProxyNamespace instances
        self._base_proxy: _ProxyNamespace = _ProxyNamespace(self)
        assert self._default  # not None if it has been correctly inherited
        self._to_proxy(self._base_proxy, self._default)

    def append_path(self, key: str) -> None:
        self._path.append(key)

    def clear_path(self) -> None:
        self._path = []

    def __getattribute__(self, key: str) -> Any:
        if key in ConfigLoader._not_in_inner:
            return super().__getattribute__(key)
        try:
            attr = self._base_proxy.getattr(key)
            if _is_public_attribute(key, attr) and isinstance(attr, _ProxyNamespace):
                self.clear_path()
                self.append_path(key)
        except AttributeError:
            attr = super().__getattribute__(key)
        return attr

    def __setattr__(self, key: str, value: Any) -> None:
        if key in ConfigLoader._not_in_inner:
            super().__setattr__(key, value)
        try:
            attr = self._base_proxy.getattr(key)
            if _is_public_attribute(key, attr) and not isinstance(attr, _ProxyNamespace):
                self.clear_path()
                self.setattr(key, value)
        except AttributeError:
            super().__setattr__(key, value)

    def setattr(self, key: str, value: Any) -> None:
        proxy: _ProxyNamespace = self._base_proxy
        for _key in self._path:
            if not proxy.hasattr(_key):
                break
            proxy = proxy.getattr(_key)
        else:
            if proxy.hasattr(key):
                if proxy.getattr(key) != value:
                    if is_right_type(proxy, key, value):
                        logger.info("%s.%s updated", self._name, ".".join((*self._path, key)))
                        proxy.setattr(key, value)
                        self.save()
        self.clear_path()

    def _open(self, mode: Literal["r", "w"]) -> IO[str]:
        with self._file_lock:
            return self._file.open(mode, encoding="utf-8")

    def save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with self._open("w") as f:
            json.dump(self._as_dict(self._base_proxy), f, indent=2)
        logger.info("%s saved to '%s'", self._name, self._file)

    def load(self) -> None:
        with self._open("r") as f:
            self._from_dict(self._base_proxy, json.load(f))
        logger.info("%s loaded from '%s'", self._name, self._file)

    def update(self) -> Self:
        try:
            if not self._im_newer():
                self.load()
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        # always save if the config file needs some fixes
        self.save()
        return self

    def _im_newer(self) -> bool:
        return self._check_newer and bool(self._module_file and getmtime(self._module_file) > getmtime(self._file))

    def _as_dict(self, proxy: _ProxyNamespace) -> dict[str, Any]:
        """recursively get a dict from _ProxyNamespace with fields validation & default values"""
        dct: dict[str, Any] = {}
        for key, value in _public_attributes(proxy.__dict__):
            if proxy.hasattr(key):
                if isinstance(value, _ProxyNamespace):
                    dct[key] = self._as_dict(value)
                elif is_right_type(proxy, key, value):
                    dct[key] = value
                else:
                    dct[key] = proxy.__defaults__[key]
        return dct

    def _from_dict(self, proxy: _ProxyNamespace, dct: dict[str, Any]) -> None:
        """recursively map a dict to _ProxyNamespace with fields validation & default values"""
        for key, value in _public_attributes(dct):
            if proxy.hasattr(key):
                if isinstance(value, dict) and isinstance(ns := getattr(proxy, key), _ProxyNamespace):
                    self._from_dict(ns, cast(dict[str, Any], value))
                elif is_right_type(proxy, key, value):
                    proxy.setattr(key, value)

    def _to_proxy(self, proxy: _ProxyNamespace, obj: type) -> None:
        """recursively turn a class into _ProxyNamespace with typing hints & default values"""
        for key, value in _public_attributes(obj.__dict__):
            if isinstance(value, type):
                proxy_value = _ProxyNamespace(self)
                proxy.setattr(key, proxy_value)
                self._to_proxy(proxy_value, value)
            else:
                proxy.setattr(key, value)
        # set hints & defaults values
        proxy.__defaults__ = dict(_public_attributes(proxy.__dict__))
        proxy.__annotations__ = obj.__annotations__
