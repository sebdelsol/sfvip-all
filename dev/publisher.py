import json
import sys
import tempfile
from pathlib import Path
from typing import Iterator, NamedTuple, Self
from urllib.parse import quote

import pefile
import requests

from src.sfvip.app_info import AppInfo
from src.sfvip.app_updater import AppLastestUpdate, AppUpdate
from src.sfvip.tools.exe import compute_md5, is64_exe

from .tools.color import Low, Ok, Title, Warn
from .tools.command import clear_lines
from .tools.dist import get_dist_name, get_dist_name_from_version
from .tools.env import EnvArgs, get_bitness_str
from .tools.protocols import CfgBuild, CfgGithub


# comments are automatically turned into argparse help
class Args(EnvArgs):
    version: str = ""  # version published (current if none)
    info: bool = False  # info about what's been published locally and on github


def fix_pe(exe: Path) -> None:
    # https://practicalsecurityanalytics.com/pe-checksum/
    print(Title("Fixing PE"), Ok(str(exe)))
    with pefile.PE(exe) as pe:
        pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()  # type: ignore
    pe.write(exe)
    clear_lines(1)


class Published(NamedTuple):
    url: str
    md5: str
    version: str
    is_64: bool

    @classmethod
    def from_update(cls, update: AppUpdate, is_64: bool) -> Self:
        return Published(url=update.url, md5=update.md5, version=update.version, is_64=is_64)


class Publisher:
    encoding = "utf-8"
    timeout = 5

    def __init__(self, build: CfgBuild, github: CfgGithub) -> None:
        self.build = build
        self.github = github
        self.app_info = AppInfo.from_build(self.build, self.github)

    def _update_path(self, is_64: bool) -> Path:
        return Path(self.build.dir) / self.build.update.format(bitness=get_bitness_str(is_64))

    def publish(self, is_64: bool) -> None:
        if self.build.update:
            exe_name = f"{get_dist_name(self.build, is_64=is_64)}.exe"
            exe_path = Path(exe_name)
            if exe_path.exists() and is_64 == is64_exe(exe_path):
                fix_pe(exe_path)
                update_path = self._update_path(is_64)
                with update_path.open(mode="w", encoding=Publisher.encoding) as f:
                    github_path = f"{self.github.owner}/{self.github.repo}"
                    update = AppUpdate(
                        url=f"https://github.com/{github_path}/raw/master/{quote(exe_name)}",
                        md5=compute_md5(exe_path),
                        version=self.build.version,
                    )
                    json.dump(update._asdict(), f, indent=2)
                print(Title("Publish update"), Ok(exe_name), Low(update.md5))
            else:
                print(Warn("Publish update failed"), Ok(exe_name))

    def publish_all(self) -> bool:
        args = Args().parse_args()
        if not args.info:
            if args.version:
                self.build.version = args.version
            for is_64 in args.get_bitness():
                if is_64 is None:
                    is_64 = sys.maxsize == (2**63) - 1
                self.publish(is_64)
        return not args.info

    def get_local_versions(self) -> Iterator[Published]:
        if self.build.update:
            for is_64 in True, False:
                update_path = self._update_path(is_64)
                if update_path.exists():
                    with update_path.open(mode="r", encoding=Publisher.encoding) as f:
                        if update := AppUpdate.from_json(json.load(f)):
                            exe = Path(f"{get_dist_name_from_version(self.build, is_64, update.version)}.exe")
                            if exe.exists() and compute_md5(exe) == update.md5:
                                yield Published.from_update(update, is_64)

    def get_online_versions(self) -> Iterator[Published]:
        if self.build.update:
            for is_64 in True, False:
                latest_update = AppLastestUpdate(self.app_info.update_url.format(bitness=get_bitness_str(is_64)))
                if update := latest_update.get(timeout=Publisher.timeout):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        exe = Path(temp_dir) / "exe"
                        with requests.get(update.url, timeout=Publisher.timeout) as response:
                            with exe.open("wb") as f:
                                f.write(response.content)
                        if exe.exists() and compute_md5(exe) == update.md5:
                            yield Published.from_update(update, is_64)

    def _show_versions(self, publisheds: Iterator[Published]) -> None:
        nothing_published = True
        for published in publisheds:
            version_color = Ok if published.version == self.build.version else Warn
            print(
                Ok(f". {self.build.name}"),
                version_color(f"v{published.version}"),
                Ok(get_bitness_str(published.is_64)),
            )
            nothing_published = False
        if nothing_published:
            print(Warn(". None"))

    def show_versions(self) -> None:
        print(Title("Locally"), Ok("published updates"))
        self._show_versions(self.get_local_versions())
        print(Title("Online"), Ok("published updates"))
        self._show_versions(self.get_online_versions())
