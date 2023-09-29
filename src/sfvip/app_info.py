import os
import platform
import sys
from pathlib import Path
from typing import NamedTuple, Protocol, Self

from sfvip_all_config import AppDefaultConfig


class Build(Protocol):
    name: str
    version: str
    dir: str
    update: str


class Github(Protocol):
    owner: str
    repo: str


class AppConfig(AppDefaultConfig):
    def __init__(self, app_roaming: Path) -> None:
        super().__init__(app_roaming / "Config All.json")


class AppInfo(NamedTuple):
    name: str
    version: str
    update_url: str
    roaming: Path
    config: AppConfig
    app_64bit: bool = sys.maxsize == (2**63) - 1
    os_64bit: bool = platform.machine().endswith("64")

    @classmethod
    def from_build(cls, build: Build, github: Github) -> Self:
        github_path = f"{github.owner}/{github.repo}"
        update_url = f"https://github.com/{github_path}/raw/master/{build.dir}/{build.update}"
        roaming = Path(os.environ["APPDATA"]) / build.name
        config = AppConfig(roaming)
        return cls(build.name, build.version, update_url, roaming, config)

    @property
    def bitness(self) -> str:
        return "x64" if self.app_64bit else "x86"

    @property
    def os_bitness(self) -> str:
        return "x64" if self.os_64bit else "x86"
