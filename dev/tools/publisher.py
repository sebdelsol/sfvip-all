import json
import tempfile
from enum import Enum
from pathlib import Path
from typing import Iterator, NamedTuple, Self, Sequence
from urllib.parse import quote

import requests

from src.sfvip.app_info import get_app_update_url, get_github_raw
from src.sfvip.app_updater import AppLastestUpdate, AppUpdate
from src.sfvip.utils.exe import compute_md5

from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist
from .utils.env import EnvArgs, PythonEnv, PythonEnvs, get_bitness_str
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub


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

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.build = build
        self.dist = Dist(build)
        self.github_raw = get_github_raw(github)
        self.update_url = get_app_update_url(build, github)
        # self.args = Args().parse_args()
        self.all_python_envs = PythonEnvs(environments).all
        self.environments = environments

    def _update_json(self, is_64: bool) -> Path:
        return Path(self.build.dir) / self.build.update.format(bitness=get_bitness_str(is_64))

    def publish(self, python_env: PythonEnv) -> None:
        if self.build.update:
            installer_exe = self.dist.installer_exe(python_env)
            installer_exe_str = str(installer_exe.as_posix())
            if installer_exe.exists():
                update_json = self._update_json(python_env.is_64)
                with update_json.open(mode="w", encoding=Publisher.encoding) as f:
                    update = AppUpdate(
                        url=f"{self.github_raw}/{quote(installer_exe_str)}",
                        md5=compute_md5(installer_exe),
                        version=self.build.version,
                    )
                    json.dump(update._asdict(), f, indent=2)
                print(Title("Publish update"), Ok(installer_exe_str), Low(update.md5))
            else:
                print(Warn("Publish update failed"), Ok(installer_exe_str))

    def publish_all(self) -> bool:
        args = Args().parse_args()
        if not args.info:
            if args.version:
                self.build.version = args.version
            for python_env in PythonEnvs(self.environments, args).asked:
                self.publish(python_env)
        return not args.info

    def get_local_versions(self) -> Iterator[Published]:
        if self.build.update:
            for python_env in self.all_python_envs:
                update_json = self._update_json(python_env.is_64)
                if update_json.exists():
                    with update_json.open(mode="r", encoding=Publisher.encoding) as f:
                        if update := AppUpdate.from_json(json.load(f)):
                            exe = self.dist.installer_exe(python_env, version=update.version)
                            yield Published.from_update(update, exe, python_env.is_64)

    def get_online_versions(self) -> Iterator[Published]:
        if self.build.update:
            for python_env in self.all_python_envs:
                latest_update = AppLastestUpdate(self.update_url.format(bitness=python_env.bitness_str))
                if update := latest_update.get(timeout=Publisher.timeout):
                    with requests.get(update.url, timeout=Publisher.timeout) as response:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            exe = Path(temp_dir) / "exe"
                            with exe.open("wb") as f:
                                f.write(response.content)
                            yield Published.from_update(update, exe, python_env.is_64)

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
