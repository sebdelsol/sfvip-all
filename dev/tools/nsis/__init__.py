import subprocess
import winreg
from functools import cached_property
from pathlib import Path
from typing import Optional

from shared.version import Version

from ..env import PythonEnv
from ..monitor.command import CommandMonitor
from ..scanner import VirusScanner
from ..utils.color import Low, Ok, Title, Warn
from ..utils.dist import repr_size
from ..utils.protocols import CfgBuild, CfgLOC
from .installer import NSISInstaller
from .upgrader import NSISUpgrader


class MakeNSIS:
    regkey64 = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\NSIS"
    regkey = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NSIS"
    exe = "makensis.exe"

    @cached_property
    def path(self) -> Optional[Path]:
        try:
            nsis_dir = winreg.QueryValue(*MakeNSIS.regkey)
        except OSError:
            try:
                nsis_dir = winreg.QueryValue(*MakeNSIS.regkey64)
            except FileNotFoundError:
                return None
        return Path(nsis_dir) / MakeNSIS.exe

    def get_version(self) -> Version:
        if self.path:
            version = subprocess.run((self.path, "/VERSION"), text=True, check=False, capture_output=True)
            return Version(version.stdout[1:])
        return Version(None)

    def upgrade(self) -> None:
        if NSISUpgrader(self.get_version()).upgrade():
            self.__dict__.pop("path", None)  # clear cache


class NSIS:
    nsis_args = "/V4 /INPUTCHARSET UTF8".split()

    def __init__(self, build: CfgBuild, loc: CfgLOC, do_run: bool, upgrade: bool) -> None:
        self.do_run = do_run
        if do_run:
            self.installer = NSISInstaller(build, loc)
            self.make_nsis = MakeNSIS()
            if upgrade or not self.make_nsis.path:
                self.make_nsis.upgrade()

    def run(self, python_env: PythonEnv) -> Optional[Path]:
        if self.do_run and self.make_nsis.path:
            print(Title("Installer with NSIS"), Ok(str(self.make_nsis.get_version())))
            install = self.installer.create(python_env)
            nsis = CommandMonitor(self.make_nsis.path, *NSIS.nsis_args, str(install.installer.resolve()))
            if nsis.run(out=Title, err=Warn):
                if VirusScanner().scan(install.exe):
                    print(Title("Built"), Ok(str(install.exe.as_posix())), Low(repr_size(install.exe)))
                    return install.exe
                install.exe.unlink(missing_ok=True)
        else:
            print(Warn("Skip Installer with NSIS"))
        return None
