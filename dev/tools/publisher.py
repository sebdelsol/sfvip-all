import json
import tempfile
from enum import Enum
from pathlib import Path
from typing import Iterator, NamedTuple, Self, Sequence
from urllib.parse import quote

import requests

from app_update import AppLastestUpdate, AppUpdate, AppUpdateLocation

from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist, repr_size
from .utils.env import EnvArgs, PythonEnv, PythonEnvs
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
    encoding = "utf-8"
    timeout = 10

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.build = build
        self.dist = Dist(build)
        self.update_location = AppUpdateLocation(build, github)
        self.all_python_envs = PythonEnvs(environments).all
        self.environments = environments

    def update_file(self, python_env: PythonEnv) -> Path:
        return Path(self.update_location.file.format(bitness=python_env.bitness))

    def update_url(self, python_env: PythonEnv) -> str:
        return self.update_location.url.format(bitness=python_env.bitness)

    def publish(self, python_env: PythonEnv) -> None:
        installer_exe = self.dist.installer_exe(python_env)
        installer_exe_str = str(installer_exe.as_posix())
        if installer_exe.exists():
            update_json = self.update_file(python_env)
            with update_json.open(mode="w", encoding=Publisher.encoding) as f:
                update = AppUpdate.from_exe(
                    url=f"{self.update_location.github}/{quote(installer_exe_str)}",
                    exe=installer_exe,
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
        for python_env in self.all_python_envs:
            update_json = self.update_file(python_env)
            if update_json.exists():
                with update_json.open(mode="r", encoding=Publisher.encoding) as f:
                    if update := AppUpdate.from_json(json.load(f)):
                        exe = self.dist.installer_exe(python_env, version=update.version)
                        yield Published.from_update(update, exe, python_env)

    def get_online_versions(self) -> Iterator[Published]:
        for python_env in self.all_python_envs:
            latest_update = AppLastestUpdate(self.update_url(python_env))
            if update := latest_update.get(timeout=Publisher.timeout):
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
