import hashlib
import logging
from pathlib import Path
from typing import Any, NamedTuple, Optional, Protocol, Self

import requests


class BuildDir(Protocol):
    dir: str


class Github(Protocol):
    owner: str
    repo: str


class AppUpdateLocation:
    def __init__(self, build: BuildDir, github: Github) -> None:
        self._build = build
        self._github_dir = f"{github.owner}/{github.repo}"

    @property
    def github(self) -> str:
        return f"https://github.com/{self._github_dir}/raw/master"

    @property
    def file(self) -> str:
        return f"{self._build.dir}/update_{{bitness}}.json"

    @property
    def url(self) -> str:
        return f"{self.github}/{self.file}"


logger = logging.getLogger(__name__)


class AppUpdate(NamedTuple):
    url: str
    md5: str
    version: str

    @classmethod
    def from_json(cls, json: Optional[Any]) -> Optional[Self]:
        try:
            if json:
                update = cls(**json)
                if all(isinstance(field, str) for field in update._fields):
                    return update
        except TypeError:
            pass
        return None

    @classmethod
    def from_exe(cls, url: str, exe: Path, version: str) -> Self:
        return cls(url=url, md5=cls.compute_md5(exe), version=version)

    def is_valid_exe(self, exe: Path) -> bool:
        return exe.exists() and self.compute_md5(exe) == self.md5

    @staticmethod
    def compute_md5(exe: Path, chunk_size: int = 2**20):
        hash_md5 = hashlib.md5()
        with exe.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


class AppLastestUpdate:
    def __init__(self, url: str) -> None:
        self._url = url

    def get(self, timeout: int) -> Optional[AppUpdate]:
        try:
            with requests.get(self._url, timeout=timeout) as response:
                response.raise_for_status()
                if update := AppUpdate.from_json(response.json()):
                    return update
        except requests.RequestException:
            pass
        return None
