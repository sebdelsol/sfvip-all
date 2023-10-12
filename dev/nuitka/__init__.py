import shutil
from pathlib import Path

from src.sfvip.tools.exe import is64_exe

from ..tools.color import Title, Warn
from ..tools.command import CommandMonitor
from ..tools.dist import get_dist_temp
from ..tools.env import PythonEnv
from ..tools.protocols import CfgBuild
from .files import IncludeFiles


class Nuitka:
    def __init__(self, build: CfgBuild, mingw: bool, do_run: bool) -> None:
        self.build = build
        self.do_run = do_run

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

    def run(self, python_env: PythonEnv) -> bool:
        dist_temp = get_dist_temp(self.build, python_env.is_64)
        if self.do_run:
            print(Title("Build by Nuitka"))
            nuitka = CommandMonitor(
                python_env.exe,
                "-m",
                "nuitka",
                f"--output-dir={dist_temp}",
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
        # check dist exist and the exe inside is the right bitness
        dist = Path(dist_temp) / f"{Path(self.build.main).stem}.dist"
        # create and clean the logs directory (needed if we launch the app in dist)
        if self.build.logs_dir:
            logs_dir = dist / self.build.logs_dir
            if logs_dir.is_dir():
                shutil.rmtree(logs_dir)
            logs_dir.mkdir(parents=True)
        exe = dist / f"{self.build.name}.exe"
        return dist.is_dir() and is64_exe(exe) == python_env.is_64
