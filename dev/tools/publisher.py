import json
import tempfile
from enum import Enum
from pathlib import Path
from typing import Iterator, Literal, NamedTuple, Optional, Self, Sequence
from urllib.parse import quote

import requests

from update import AppLatestUpdate, AppUpdate

from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist, repr_size
from .utils.env import EnvArgs, PythonEnv, PythonEnvs
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub


# comments are turned into argparse help
class Args(EnvArgs):
    version: str = ""  # version published (current if none)
    info: bool = False  # info about what's been published locally and on github


class AppLatestUpdateLocal(AppLatestUpdate):
    encoding = "utf-8"

    def from_exe(self, exe: Path, version: str) -> Optional[AppUpdate]:
        url = f"{self._github_dir}/{quote(str(exe.as_posix()))}"
        return AppUpdate.from_exe(url, exe, version)

    def local_load(self, bitness: Literal["x64", "x86"]) -> Optional[AppUpdate]:
        update_json = self._file(bitness)
        if update_json.exists():
            with update_json.open(mode="r", encoding=AppLatestUpdateLocal.encoding) as f:
                return AppUpdate.from_dict(json.load(f))
        return None

    def local_save(self, update: AppUpdate, bitness: Literal["x64", "x86"]) -> None:
        update_json = self._file(bitness)
        with update_json.open(mode="w", encoding=AppLatestUpdateLocal.encoding) as f:
            json.dump(update._asdict(), f, indent=2)


class Valid(Enum):
    OK = Ok("Valid")
    NOTFOUND = Warn("Exe not found")
    MD5 = Warn("Wrong md5 Exe")
    ERROR = Warn("Can't open Exe")

    @classmethod
    def check_exe(cls, exe: Path, update: AppUpdate) -> Self:
        if not exe.exists():
            return cls.NOTFOUND
        try:
            if not update.is_valid_exe(exe):
                return cls.MD5
        except OSError:
            return cls.ERROR
        return cls.OK


class Published(NamedTuple):
    url: str
    md5: str
    version: str
    bitness: str
    valid: Valid
    size: str

    @classmethod
    def from_update(cls, update: AppUpdate, exe: Path, python_env: PythonEnv) -> Self:
        return Published(
            bitness=python_env.bitness,
            url=update.url,
            md5=update.md5,
            version=update.version,
            valid=Valid.check_exe(exe, update),
            size=repr_size(exe),
        )


class Publisher:
    timeout = 10

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.build = build
        self.dist = Dist(build)
        self.app_latest_update = AppLatestUpdateLocal(build, github)
        self.all_python_envs = PythonEnvs(environments).all
        self.environments = environments

    def publish(self, python_env: PythonEnv) -> None:
        exe = self.dist.installer_exe(python_env)
        exe_str = str(exe.as_posix())
        if update := self.app_latest_update.from_exe(exe, self.build.version):
            self.app_latest_update.local_save(update, python_env.bitness)
            print(Title("Publish update"), Ok(exe_str), Low(update.md5))
        else:
            print(Warn("Publish update failed"), Ok(exe_str))

    def publish_all(self) -> bool:
        args = Args().parse_args()
        if not args.info:
            if args.version:
                self.build.version = args.version
            for python_env in PythonEnvs(self.environments, args).asked:
                self.publish(python_env)
        return not args.info

    def get_local_versions(self) -> Iterator[Published]:
        for python_env in self.all_python_envs:
            if update := self.app_latest_update.local_load(python_env.bitness):
                exe = self.dist.installer_exe(python_env, update.version)
                yield Published.from_update(update, exe, python_env)

    def get_online_versions(self) -> Iterator[Published]:
        for python_env in self.all_python_envs:
            if update := self.app_latest_update.online_load(python_env.bitness, Publisher.timeout):
                with requests.get(update.url, timeout=Publisher.timeout) as response:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        exe = Path(temp_dir) / "exe"
                        with exe.open("wb") as f:
                            f.write(response.content)
                        yield Published.from_update(update, exe, python_env)

    def _show_versions(self, publisheds: Iterator[Published], old: Sequence[Published] = ()) -> list[Published]:
        all_publisheds = []
        for published in publisheds:
            version_color = Ok if published.version == self.build.version else Warn
            print(
                Ok(f". {self.build.name}"),
                version_color(f"v{published.version}"),
                Ok(published.bitness),
                Low(f"- {published.md5} - {published.size}"),
                Ok(f" {published.valid.value}"),
                (Ok(" Already published") if published in old else Title(" New")) if old else "",
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
