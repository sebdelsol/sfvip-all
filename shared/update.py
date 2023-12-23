import hashlib
from pathlib import Path
from typing import Any, Literal, NamedTuple, Optional, Protocol, Self

import requests


class BuildDir(Protocol):
    dir: str


class Github(Protocol):
    owner: str
    repo: str


def compute_md5(exe: Path, chunk_size: int = 2**20) -> str:
    hash_md5 = hashlib.md5()
    with exe.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class AppUpdate(NamedTuple):
    url: str
    md5: str
    version: str

    @classmethod
    def from_dict(cls, dct: Optional[dict[str, Any]]) -> Optional[Self]:
        try:
            if dct:
                if all(isinstance(value, str) for value in dct.values()):
                    return cls(**dct)
        except TypeError:
            pass
        return None

    @classmethod
    def from_exe(cls, url: str, exe: Path, version: str) -> Optional[Self]:
        if exe.is_file():
            return cls(url=url, md5=compute_md5(exe), version=version)
        return None

    def is_valid_exe(self, exe: Path) -> bool:
        return exe.exists() and compute_md5(exe) == self.md5


class AppLatestUpdate:
    def __init__(self, build: BuildDir, github: Github) -> None:
        self._build_dir = build.dir
        self._github_dir = f"https://github.com/{github.owner}/{github.repo}/raw/master"

    def _file(self, bitness: Literal["x64", "x86"]) -> Path:
        return Path(f"{self._build_dir}/update_{bitness}.json")

    def _url(self, bitness: Literal["x64", "x86"]) -> str:
        return f"{self._github_dir}/{self._file(bitness).as_posix()}"

    def online_load(self, bitness: Literal["x64", "x86"], timeout: int) -> Optional[AppUpdate]:
        try:
            url = self._url(bitness)
            with requests.get(url, timeout=timeout) as response:
                response.raise_for_status()
                if update := AppUpdate.from_dict(response.json()):
                    return update
        except requests.RequestException:
            pass
        return None
