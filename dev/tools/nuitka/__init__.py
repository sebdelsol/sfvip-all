import shutil

from src.sfvip.utils.exe import is64_exe

from ..utils.color import Title, Warn
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
                *(f"--enable-plugin={plugin}" for plugin in build.nuitka_plugins),
                "--enable-console" if build.enable_console else "--disable-console",
                f"--company-name={build.company}",
                f"--file-version={build.version}",
                f"--product-version={build.version}",
                "--mingw64" if mingw else "--clang",
                f"--windows-icon-from-ico={build.ico}",
                f"--output-filename={build.name}.exe",
                *IncludeFiles(build.files, build.ico).all,
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
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
        return dist.is_dir() and is64_exe(exe) == python_env.is_64

    def run(self, python_env: PythonEnv) -> bool:
        if self.do_run:
            print(Title("Build by Nuitka"))
            nuitka = CommandMonitor(
                python_env.exe,
                "-m",
                "nuitka",
                f"--output-dir={self.dist.build_dir(python_env)}",
                *(
                    f"--include-plugin-directory={python_env.path_str}/Lib/site-packages/{plugin_dir}"
                    for plugin_dir in self.build.nuitka_plugin_dirs
                ),
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
