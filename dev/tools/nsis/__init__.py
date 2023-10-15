import subprocess
import winreg
from functools import cached_property
from pathlib import Path
from typing import Optional

from ..utils.color import Low, Ok, Title, Warn
from ..utils.command import CommandMonitor
from ..utils.dist import repr_size
from ..utils.env import PythonEnv
from ..utils.protocols import CfgBuild, CfgLOC
from .installer import NSISInstaller
from .virus_scan import VirusScan


class MakeNSIS:
    regkey64 = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\NSIS"
    regkey = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NSIS"
    exe = "makensis.exe"

    @cached_property
    def path(self) -> Path:
        try:
            nsis_dir = winreg.QueryValue(*MakeNSIS.regkey)
        except OSError:
            nsis_dir = winreg.QueryValue(*MakeNSIS.regkey64)
        return Path(nsis_dir) / MakeNSIS.exe

    def get_version(self) -> str:
        version = subprocess.run((self.path, "/VERSION"), text=True, check=False, capture_output=True)
        return version.stdout[1:]


class NSIS:
    nsis_args = "/V4 /INPUTCHARSET UTF8".split()

    def __init__(self, build: CfgBuild, loc: CfgLOC, do_run: bool) -> None:
        self.do_run = do_run
        self.installer = NSISInstaller(build, loc)
        self.virus_scan = VirusScan(update=do_run)
        self.make_nsis = MakeNSIS()

    def run(self, python_env: PythonEnv) -> Optional[Path]:
        if self.do_run:
            print(Title("Installer by NSIS"), Ok(self.make_nsis.get_version()))
            install = self.installer.create(python_env)
            nsis = CommandMonitor(self.make_nsis.path, *NSIS.nsis_args, str(install.script.resolve()))
            if nsis.run(out=Title, err=Warn):
                if self.virus_scan.run_on(install.exe):
                    print(Title("Built"), Ok(str(install.exe.as_posix())), Low(repr_size(install.exe)))
                    return install.exe
                install.exe.unlink(missing_ok=True)
        else:
            print(Warn("Skip Installer by NSIS"))
        return None
