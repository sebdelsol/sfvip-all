import os
import platform
import sys
from pathlib import Path
from typing import NamedTuple, Protocol, Self, Sequence

from sfvip_all_config import AppDefaultConfig
from shared import BitnessT, get_bitness_str
from shared.update import AppLatestUpdate, Github


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
    def files(self) -> Sequence[Files]: ...


APP_64BIT = sys.maxsize == (2**63) - 1
OS_64BIT: bool = platform.machine().endswith("64")


class AppInfo(NamedTuple):
    name: str
    version: str
    roaming: Path
    config: AppConfig
    logo: Path
    splash: Path
    changelog: Path
    translations: Path
    logs_dir: Path
    current_dir: Path
    app_latest_update: AppLatestUpdate
    bitness: BitnessT = get_bitness_str(APP_64BIT)
    os_bitness: BitnessT = get_bitness_str(OS_64BIT)

    @classmethod
    def from_build(cls, build: Build, github: Github, app_dir: Path = Path()) -> Self:
        roaming = Path(os.environ["APPDATA"]) / build.name
        current_dir = Path(sys.argv[0]).parent
        files = {file.__name__: app_dir / file.path for file in build.files}
        return cls(
            name=build.name,
            version=build.version,
            roaming=roaming,
            config=AppConfig(roaming),
            logo=files["Logo"],
            splash=files["Splash"],
            changelog=files["Changelog"],
            translations=files["Translations"],
            logs_dir=current_dir / build.logs_dir,
            current_dir=current_dir,
            app_latest_update=AppLatestUpdate(build, github),
        )
