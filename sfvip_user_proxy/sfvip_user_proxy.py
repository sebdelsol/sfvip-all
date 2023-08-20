# Use Python 3.11 with no dependencies

# set a global user proxy:
# python -m sfvip_user_proxy http://127.0.0.1:8888

# remove the global user proxy:
# python -m sfvip_puser_proxy

import argparse
import json
import logging
import re
import winreg
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

logging.basicConfig(level=logging.INFO, format="%(message)s")


def reg_value_by_name(hkey: int, path: str, name: str) -> str:
    with suppress(WindowsError, FileNotFoundError), winreg.OpenKey(hkey, path) as k:
        value = winreg.QueryValueEx(k, name)[0]
        return value
    return ""


class _JsonTrailingCommas:
    _object = re.compile(r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    _array = re.compile(r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')

    @staticmethod
    def remove(json_str: str) -> str:
        json_str = _JsonTrailingCommas._object.sub("}", json_str)
        return _JsonTrailingCommas._array.sub("]", json_str)


class User(SimpleNamespace):
    _playlist_ext = ".m3u", ".m3u8"

    def __init__(self, **kwargs: str) -> None:
        # pylint: disable=invalid-name
        self.Name: str
        self.Address: str
        self.HttpProxy: str
        super().__init__(**kwargs)

    def is_playlist(self) -> bool:
        path = Path(self.Address)
        return path.suffix in User._playlist_ext or path.is_file()


class Users:
    _from_registry = winreg.HKEY_CURRENT_USER, r"SOFTWARE\SFVIP", "ConfigDir"
    _filename = "Database.json"
    _encoding = "utf-8"

    class _Encoder(json.JSONEncoder):
        def default(self, o: User) -> dict[str, str]:
            return o.__dict__

    def __init__(self) -> None:
        self._users: list[User] = []
        self._database = Path(reg_value_by_name(*Users._from_registry)) / Users._filename
        logging.info("Users database %s", self._database if self._database.is_file() else "NOT found")

    def _load(self) -> None:
        with self._database.open("r", encoding=Users._encoding) as f:
            json_str = _JsonTrailingCommas.remove(f.read())
            try:
                self._users = json.loads(json_str, object_hook=lambda dct: User(**dct))
            except json.decoder.JSONDecodeError:
                self._users = []

    def _save(self) -> None:
        with self._database.open("w", encoding=Users._encoding) as f:
            json.dump(self._users, f, cls=Users._Encoder, indent=2, separators=(",", ":"))

    def set_user_proxy(self, user_proxy: str) -> None:
        if self._database.is_file():
            self._load()
            user_proxy = user_proxy.strip()
            users = [user for user in self._users if not user.is_playlist()]
            logging.info("%s global user proxy %s", "Set" if user_proxy else "Remove", user_proxy)
            logging.info("For %s", ", ".join(user.Name for user in users) if users else "No users")
            for user in users:
                user.HttpProxy = user_proxy
            self._save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="", help="global user proxy url")
    Users().set_user_proxy(parser.parse_args().url)
