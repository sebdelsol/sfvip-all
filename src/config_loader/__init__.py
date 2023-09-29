import json
import logging
import sys
from os.path import getmtime
from pathlib import Path
from types import FunctionType, MappingProxyType, MethodType, SimpleNamespace
from typing import IO, Any, Iterator, Optional, cast, get_type_hints

from ..winapi import mutex

logger = logging.getLogger(__name__)


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

    def __getattribute__(self, __name: str) -> Any:
        attr = super().__getattribute__(__name)
        if _is_public_attribute(__name, attr) and isinstance(attr, _ProxyNamespace):
            self._config.append_path(__name)
        return attr

    def __setattr__(self, __name: str, __value: Any) -> None:
        try:
            attr = super().__getattribute__(__name)
            if _is_public_attribute(__name, attr) and not isinstance(attr, _ProxyNamespace):
                self._config.setattr(__name, __value)
        except AttributeError:
            super().__setattr__(__name, __value)

    def setattr(self, __name: str, __value: Any) -> None:
        super().__setattr__(__name, __value)

    def getattr(self, __name: str) -> Any:
        return super().__getattribute__(__name)

    def hasattr(self, __name: str) -> bool:
        try:
            super().__getattribute__(__name)
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

    __slots__ = "_inner", "_file", "_path", "_name", "_file_lock", "_base_proxy"
    _default: Optional[type] = None
    _module_file = None

    def __init_subclass__(cls) -> None:
        if not cls._default:
            # defaults are stored in the 1st child
            cls._default = cls
            cls._module_file = sys.modules[cls.__module__].__file__

    def __init__(self, file: Path) -> None:
        ConfigLoader._not_in_inner = set(dict(ConfigLoader.__dict__).keys())
        ConfigLoader._not_in_inner.update(set(dict(_ProxyNamespace.__dict__).keys()))
        self._file = file
        self._path: list[str] = []
        self._name = self.__class__.__name__
        self._file_lock = mutex.SystemWideMutex(f"file lock for {file}")
        # turn all config nested classes into _ProxyNamespace instances
        self._base_proxy: _ProxyNamespace = _ProxyNamespace(self)
        assert self._default  # not None if it has been correctly inherited
        self._to_simplenamespace(self._base_proxy, self._default)

    def append_path(self, __name: str) -> None:
        self._path.append(__name)

    def clear_path(self) -> None:
        self._path = []

    def __getattribute__(self, __name: str) -> Any:
        if __name in ConfigLoader._not_in_inner:
            return super().__getattribute__(__name)
        try:
            attr = self._base_proxy.getattr(__name)
            if _is_public_attribute(__name, attr) and isinstance(attr, _ProxyNamespace):
                self.clear_path()
                self.append_path(__name)
        except AttributeError:
            attr = super().__getattribute__(__name)
        return attr

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in ConfigLoader._not_in_inner:
            super().__setattr__(__name, __value)
        try:
            attr = self._base_proxy.getattr(__name)
            if _is_public_attribute(__name, attr) and not isinstance(attr, _ProxyNamespace):
                self.clear_path()
                self.setattr(__name, __value)
        except AttributeError:
            super().__setattr__(__name, __value)

    def setattr(self, __name: str, __value: Any) -> None:
        proxy: _ProxyNamespace = self._base_proxy
        for path in self._path:
            if not proxy.hasattr(path):
                break
            proxy = proxy.getattr(path)
        else:
            if proxy.hasattr(__name):
                if proxy.getattr(__name) != __value:
                    if is_right_type(proxy, __name, __value):
                        logger.info("%s.%s updated", self._name, ".".join((*self._path, __name)))
                        proxy.setattr(__name, __value)
                        self._save()
        self.clear_path()

    def _open(self, mode: str) -> IO[str]:
        with self._file_lock:
            return self._file.open(mode, encoding="utf-8")

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with self._open("w") as f:
            json.dump(self._dict_from(self._base_proxy), f, indent=2)
        logger.info("%s saved to '%s'", self._name, self._file)

    def _load(self) -> None:
        with self._open("r") as f:
            self._map_dict_to(self._base_proxy, json.load(f))
        logger.info("%s loaded from '%s'", self._name, self._file)

    def update(self) -> None:
        try:
            if not self._im_newer():
                self._load()
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        # always save if the config file needs some fixes
        self._save()

    def _im_newer(self) -> bool:
        # launched by nuitka ?
        if "__compiled__" in globals():
            return False
        return bool(self._module_file and getmtime(self._module_file) > getmtime(self._file))

    def _dict_from(self, proxy: _ProxyNamespace) -> dict[str, Any]:
        """recursively get a dict from _ProxyNamespace with fields validation & default values"""
        dct = {}
        for key, value in _public_attributes(proxy.__dict__):
            if proxy.hasattr(key):
                if isinstance(value, _ProxyNamespace):
                    dct[key] = self._dict_from(value)
                elif is_right_type(proxy, key, value):
                    dct[key] = value
                else:
                    dct[key] = proxy.__defaults__[key]
        return dct

    def _map_dict_to(self, proxy: _ProxyNamespace, dct: dict[str, Any]) -> None:
        """recursively map a dict to _ProxyNamespace with fields validation & default values"""
        for key, value in _public_attributes(dct):
            if proxy.hasattr(key):
                if isinstance(value, dict) and isinstance(ns := getattr(proxy, key), _ProxyNamespace):
                    self._map_dict_to(ns, cast(dict[str, Any], value))
                elif is_right_type(proxy, key, value):
                    proxy.setattr(key, value)

    def _to_simplenamespace(self, proxy: _ProxyNamespace, obj: type) -> None:
        """recursively turn a class into _ProxyNamespac with typing hints & default values"""
        for key, value in _public_attributes(obj.__dict__):
            if isinstance(value, type):
                proxy_value = _ProxyNamespace(self)
                proxy.setattr(key, proxy_value)
                self._to_simplenamespace(proxy_value, value)
            else:
                proxy.setattr(key, value)
        # set hints & defaults values
        proxy.__defaults__ = dict(_public_attributes(proxy.__dict__))
        proxy.__annotations__ = obj.__annotations__
