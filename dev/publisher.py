import json
import sys
import tempfile
from enum import Enum
from pathlib import Path
from typing import Iterator, NamedTuple, Self, Sequence
from urllib.parse import quote

import requests

from src.sfvip.app_info import get_app_update_url, get_github_raw
from src.sfvip.app_updater import AppLastestUpdate, AppUpdate
from src.sfvip.tools.exe import compute_md5

from .tools.color import Low, Ok, Title, Warn
from .tools.dist import get_dist_name, get_dist_name_from_version
from .tools.env import EnvArgs, get_bitness_str
from .tools.protocols import CfgBuild, CfgGithub


# comments are turned into argparse help
class Args(EnvArgs):
    version: str = ""  # version published (current if none)
    info: bool = False  # info about what's been published locally and on github


class Valid(Enum):
    OK = Ok("Valid")
    NOTFOUND = Warn("Exe not found")
    MD5 = Warn("Wrong md5 Exe")
    ERROR = Warn("Can't open Exe")

    @classmethod
    def check_exe(cls, exe: Path, md5: str) -> Self:
        if not exe.exists():
            return cls.NOTFOUND
        try:
            if compute_md5(exe) != md5:
                return cls.MD5
        except OSError:
            return cls.ERROR
        return cls.OK


class Published(NamedTuple):
    url: str
    md5: str
    version: str
    is_64: bool
    valid: Valid

    @classmethod
    def from_update(cls, update: AppUpdate, exe: Path, is_64: bool) -> Self:
        return Published(
            is_64=is_64,
            url=update.url,
            md5=update.md5,
            version=update.version,
            valid=Valid.check_exe(exe, update.md5),
        )


class Publisher:
    encoding = "utf-8"
    timeout = 10

    def __init__(self, build: CfgBuild, github: CfgGithub) -> None:
        self.build = build
        self.github_raw = get_github_raw(github)
        self.update_url = get_app_update_url(build, github)

    def _update_json(self, is_64: bool) -> Path:
        return Path(self.build.dir) / self.build.update.format(bitness=get_bitness_str(is_64))

    def publish(self, is_64: bool) -> None:
        if self.build.update:
            exe_name = f"{get_dist_name(self.build, is_64=is_64)}.exe"
            exe_path = Path(exe_name)
            if exe_path.exists():
                # fix_pe(exe_path)
                update_json = self._update_json(is_64)
                with update_json.open(mode="w", encoding=Publisher.encoding) as f:
                    update = AppUpdate(
                        url=f"{self.github_raw}/{quote(exe_name)}",
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

    def _get_all_builds(self) -> Iterator[bool]:
        if self.build.update:
            for is_64 in True, False:
                yield is_64

    def get_local_versions(self) -> Iterator[Published]:
        for is_64 in self._get_all_builds():
            update_json = self._update_json(is_64)
            if update_json.exists():
                with update_json.open(mode="r", encoding=Publisher.encoding) as f:
                    if update := AppUpdate.from_json(json.load(f)):
                        exe = Path(f"{get_dist_name_from_version(self.build, is_64, update.version)}.exe")
                        yield Published.from_update(update, exe, is_64)

    def get_online_versions(self) -> Iterator[Published]:
        for is_64 in self._get_all_builds():
            latest_update = AppLastestUpdate(self.update_url.format(bitness=get_bitness_str(is_64)))
            if update := latest_update.get(timeout=Publisher.timeout):
                with requests.get(update.url, timeout=Publisher.timeout) as response:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        exe = Path(temp_dir) / "exe"
                        with exe.open("wb") as f:
                            f.write(response.content)
                        yield Published.from_update(update, exe, is_64)

    def _show_versions(self, publisheds: Iterator[Published], old: Sequence[Published] = ()) -> list[Published]:
        all_publisheds = []
        for published in publisheds:
            version_color = Ok if published.version == self.build.version else Warn
            print(
                Ok(f". {self.build.name}"),
                version_color(f"v{published.version}"),
                Ok(get_bitness_str(published.is_64)),
                Low(published.md5),
                published.valid.value,
                f"{Low('-')} {Ok('Already published') if published in old else Title('New')}" if old else "",
            )
            all_publisheds.append(published)
        if not all_publisheds:
            print(Warn(". None"))
        return all_publisheds

    def show_versions(self) -> None:
        print(Title("Online"), Ok("published updates"))
        online_versions = self._show_versions(self.get_online_versions())
        print(Title("Locally"), Ok("published updates"))
        self._show_versions(self.get_local_versions(), online_versions)
