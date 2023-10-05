import os
import platform
import sys
from pathlib import Path
from typing import NamedTuple, Protocol, Self, Sequence

from sfvip_all_config import AppDefaultConfig


class Files(Protocol):
    __name__: str
    path: str


class BuildUpdate(Protocol):
    dir: str
    update: str


class Build(BuildUpdate, Protocol):
    name: str
    version: str

    @property
    def files(self) -> Sequence[Files]:
        ...


class Github(Protocol):
    owner: str
    repo: str


class AppConfig(AppDefaultConfig):
    def __init__(self, app_roaming: Path) -> None:
        super().__init__(app_roaming / "Config All.json")


def get_github_raw(github: Github) -> str:
    return f"https://github.com/{github.owner}/{github.repo}/raw/master"


def get_app_update_url(build: BuildUpdate, github: Github) -> str:
    return f"{get_github_raw(github)}/{build.dir}/{build.update}"


class AppInfo(NamedTuple):
    name: str
    version: str
    update_url: str
    roaming: Path
    config: AppConfig
    logo: Path
    splash: Path
    translations: Path
    app_64bit: bool = sys.maxsize == (2**63) - 1
    os_64bit: bool = platform.machine().endswith("64")

    @classmethod
    def from_build(cls, build: Build, github: Github, app_dir: Path = Path()) -> Self:
        roaming = Path(os.environ["APPDATA"]) / build.name
        files = {file.__name__: app_dir / file.path for file in build.files}
        return cls(
            name=build.name,
            version=build.version,
            update_url=get_app_update_url(build, github),
            roaming=roaming,
            config=AppConfig(roaming),
            logo=files["Logo"],
            splash=files["Splash"],
            translations=files["Translations"],
        )

    @property
    def bitness(self) -> str:
        return "x64" if self.app_64bit else "x86"

    @property
    def os_bitness(self) -> str:
        return "x64" if self.os_64bit else "x86"
