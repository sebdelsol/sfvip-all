import shutil

from ..scanner import VirusScan
from ..utils.color import Ok, Title, Warn
from ..utils.command import CommandMonitor
from ..utils.dist import Dist
from ..utils.env import PythonEnv
from ..utils.protocols import CfgBuild
from .files import IncludeFiles


class Nuitka:
    def __init__(self, build: CfgBuild, mingw: bool, do_run: bool) -> None:
        self.build = build
        self.do_run = do_run
        self.dist = Dist(build)
        if do_run:
            self.args = (
                "--enable-console" if build.enable_console else "--disable-console",
                *IncludeFiles(build.files, build.ico).all,
                f"--windows-icon-from-ico={build.ico}",
                f"--output-filename={build.name}.exe",
                f"--product-version={build.version}",
                "--mingw64" if mingw else "--clang",
                f"--company-name={build.company}",
                f"--file-version={build.version}",
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                "--deployment",  # disable Nuitka safeguards
                "--standalone",
                build.main,
            )
            if build.logs_dir:
                logs = f"--force-stderr-spec=%PROGRAM%/../{build.logs_dir}/{build.name} - %TIME%.log"
                self.args = logs, *self.args
        else:
            self.args = ()

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
        return dist.is_dir() and exe.is_file() and VirusScan.scan(dist)

    def run(self, python_env: PythonEnv) -> bool:
        if self.do_run:
            print(Title("Build by Nuitka"), Ok(python_env.package_version("nuitka")))
            nuitka = CommandMonitor(
                python_env.exe,
                "-m",
                "nuitka",
                f"--output-dir={self.dist.build_dir(python_env)}",
                *self.args,
            )
            if not nuitka.run(out=Title):
                return False
        else:
            print(Warn("Skip Build by Nuitka"))

        if self.check_exe(python_env):
            self.clean_logs(python_env)
            return True
        return False
