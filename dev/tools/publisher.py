import json
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Iterator, NamedTuple, Optional, Self, Sequence

import requests

from shared.update import AppLatestUpdate, AppUpdate, BitnessT

from .env.envs import EnvArgs, PythonEnv, PythonEnvs
from .release import ReleaseCreator
from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist, repr_size
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub


# comments are turned into argparse help
class Args(EnvArgs):
    version: str = ""  # version published (current if none)
    info: bool = False  # info about what's been published locally and on github


class AppLatestUpdateLocal(AppLatestUpdate):
    encoding = "utf-8"

    def local_load(self, bitness: BitnessT) -> Optional[AppUpdate]:
        update_json = self._file(bitness)
        if update_json.exists():
            with update_json.open(mode="r", encoding=AppLatestUpdateLocal.encoding) as f:
                return AppUpdate.from_dict(json.load(f))
        return None

    def local_save(self, update: AppUpdate, bitness: BitnessT) -> None:
        update_json = self._file(bitness)
        with update_json.open(mode="w", encoding=AppLatestUpdateLocal.encoding) as f:
            json.dump(update._asdict(), f, indent=2)


class Valid(StrEnum):
    OK = Ok("Valid")
    NOTFOUND = Warn("Exe not found")
    MD5 = Warn("Wrong md5 Exe")
    ERROR = Warn("Can't open Exe")

    @classmethod
    def check_exe(cls, exe: Path, update: AppUpdate) -> str:
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
    bitness: BitnessT
    exe: Path
    valid: str
    size: str

    @classmethod
    def from_update(cls, update: AppUpdate, exe: Path, python_env: PythonEnv) -> Self:
        return cls(
            bitness=python_env.bitness,
            url=update.url,
            md5=update.md5,
            version=update.version,
            exe=exe,
            valid=Valid.check_exe(exe, update),
            size=repr_size(exe),
        )

    def __eq__(self, other: Self) -> bool:
        fields = Published._fields
        return all(getattr(self, field) == getattr(other, field) for field in fields if field != "exe")


class Publisher:
    timeout = 10

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.build = build
        self.dist = Dist(build)
        self.release = ReleaseCreator(build, environments, github)
        self.app_latest_update = AppLatestUpdateLocal(build, github)
        self.all_python_envs = PythonEnvs(environments).all
        self.environments = environments

    def publish(self, python_env: PythonEnv, version: str) -> bool:
        exe = self.dist.installer_exe(python_env, version)
        version = version or self.build.version
        if url := self.release.create(python_env, version):
            if update := AppUpdate.from_exe(url, exe, version):
                self.app_latest_update.local_save(update, python_env.bitness)
                print(Title("Release"), Ok(exe.name), Low("-"), Low(update.md5), Low("-"), Low(repr_size(exe)))
                return True
        return False

    def publish_all(self) -> bool:
        args = Args().parse_args()
        if not args.info:
            version = args.version if args.version else self.build.version
            published = True
            for python_env in PythonEnvs(self.environments, args).asked:
                published &= self.publish(python_env, version)
            return published
        return False

    def get_local_version(self, python_env: PythonEnv) -> Optional[Published]:
        if update := self.app_latest_update.local_load(python_env.bitness):
            exe = self.dist.installer_exe(python_env, update.version)
            return Published.from_update(update, exe, python_env)
        return None

    def get_local_versions(self) -> Iterator[Published]:
        for python_env in self.all_python_envs:
            if published := self.get_local_version(python_env):
                yield published

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
        all_publisheds: list[Published] = []
        for published in publisheds:
            version_color = Ok if published.version == self.build.version else Warn
            print(
                Ok(f". {self.build.name}"),
                version_color(f"v{published.version}"),
                version_color(published.bitness),
                Low(f"• {published.md5} • {published.size} •"),
                Ok(published.valid),
                (Ok("• Already published") if published in old else Title("• New")) if old else "",
            )
            all_publisheds.append(published)
        if not all_publisheds:
            print(Warn(". None"))
        return all_publisheds

    def show_versions(self) -> None:
        print(Title("Online"), Ok("published releases"))
        online_versions = self._show_versions(self.get_online_versions())
        print(Title("Locally"), Ok("published releases"))
        self._show_versions(self.get_local_versions(), online_versions)
