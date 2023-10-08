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
        self.args = (
            (
                f"--company-name={build.company}",
                f"--file-version={build.version}",
                f"--product-version={build.version}",
                "--mingw64" if mingw else "--clang",
                f"--windows-icon-from-ico={build.ico}",
                f"--output-filename={build.name}.exe",
                *IncludeFiles(build.files, build.ico).all,
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                *build.nuitka_args,
                "--standalone",
                build.main,
            )
            if do_run
            else ()
        )

    def run(self, python_env: PythonEnv) -> bool:
        dist_temp = get_dist_temp(self.build, python_env.is_64)
        if self.do_run:
            print(Title("Build by Nuitka"))
            nuitka = CommandMonitor(
                python_env.exe,
                "-m",
                "nuitka",
                f"--output-dir={dist_temp}",
                *(arg.format(python_env=python_env.path_str) for arg in self.args),
            )
            if not nuitka.run(out=Title):
                return False
        else:
            print(Warn("Skip Build by Nuitka"))
        # check dist exist and the exe inside is the right bitness
        dist = Path(dist_temp) / f"{Path(self.build.main).stem}.dist"
        exe = dist / f"{self.build.name}.exe"
        return dist.is_dir() and is64_exe(exe) == python_env.is_64
