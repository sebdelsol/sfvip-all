import os
import platform
import sys
from pathlib import Path
from typing import NamedTuple, Protocol, Self, Sequence

from app_update import AppUpdateLocation, Github
from sfvip_all_config import AppDefaultConfig


class AppConfig(AppDefaultConfig):
    def __init__(self, app_roaming: Path) -> None:
        super().__init__(app_roaming / "Config All.json")


class Files(Protocol):
    __name__: str
    path: str


class Build(Protocol):
    dir: str
    name: str
    version: str
    logs_dir: str

    @property
    def files(self) -> Sequence[Files]:
        ...


def get_bitness(is_64: bool) -> str:
    return "x64" if is_64 else "x86"


APP_64BIT = sys.maxsize == (2**63) - 1
OS_64BIT: bool = platform.machine().endswith("64")


class AppInfo(NamedTuple):
    name: str
    version: str
    update_url: str
    roaming: Path
    config: AppConfig
    logo: Path
    splash: Path
    translations: Path
    logs_dir: Path
    current_dir: Path

    bitness = get_bitness(APP_64BIT)
    os_bitness = get_bitness(OS_64BIT)

    @classmethod
    def from_build(cls, build: Build, github: Github, app_dir: Path = Path()) -> Self:
        roaming = Path(os.environ["APPDATA"]) / build.name
        current_dir = Path(sys.argv[0]).parent
        files = {file.__name__: app_dir / file.path for file in build.files}
        return cls(
            name=build.name,
            version=build.version,
            update_url=AppUpdateLocation(build, github).url.format(bitness=cls.bitness),
            roaming=roaming,
            config=AppConfig(roaming),
            logo=files["Logo"],
            splash=files["Splash"],
            translations=files["Translations"],
            logs_dir=current_dir / build.logs_dir,
            current_dir=current_dir,
        )
