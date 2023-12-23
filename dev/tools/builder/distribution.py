import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Optional

from ..env import PythonEnv
from ..scanner import VirusScanner
from ..utils.color import Ok, Title, Warn
from ..utils.dist import Dist
from ..utils.protocols import CfgBuild


class Distribution(ABC):
    name: ClassVar[str]
    _retry_antivirus_lock = 5

    def __init__(self, build: CfgBuild, do_run: bool) -> None:
        self.build = build
        self.do_run = do_run
        self.dist = Dist(build)

    def clean_logs(self, python_env: PythonEnv) -> None:
        dist = self.dist.dist_dir(python_env)
        if self.build.logs_dir:
            logs_dir = dist / self.build.logs_dir
            if logs_dir.is_dir():
                shutil.rmtree(logs_dir)
            logs_dir.mkdir(parents=True)

    def check_exe(self, python_env: PythonEnv) -> bool:
        dist = self.dist.dist_dir(python_env)
        exe = dist / f"{self.build.name}.exe"
        return dist.is_dir() and exe.is_file() and VirusScanner().scan(dist)

    def run(self, python_env: PythonEnv) -> bool:
        if self.do_run:
            print(Title(f"Build with {self.name}"), Ok(python_env.package_version(self.name)))
            build_dir = self.dist.build_dir(python_env) / self.name.lower()
            build_dir.mkdir(exist_ok=True)
            built_dist = self.create(python_env.exe, build_dir)
            if built_dist is None:
                return False
            dist_dir = self.dist.dist_dir(python_env)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir)
            # AV might lock the file
            for _ in range(Distribution._retry_antivirus_lock):
                try:
                    built_dist.rename(dist_dir)
                    break
                except PermissionError:
                    time.sleep(2)
            else:
                print(Warn(f"AV locked {dist_dir}"))
        else:
            print(Warn("Skip Build with"), Warn(self.name))

        self.clean_logs(python_env)
        if self.check_exe(python_env):
            return True
        return False

    @abstractmethod
    def create(self, python_exe: Path, build_dir: Path) -> Optional[Path]:
        ...
