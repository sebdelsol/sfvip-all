import winreg
from pathlib import Path
from typing import Optional

from ..utils.color import Low, Ok, Title, Warn
from ..utils.command import CommandMonitor
from ..utils.env import PythonEnv
from ..utils.protocols import CfgBuild, CfgLOC
from .installer import NSISInstaller
from .virus_scan import VirusScan


class NSIS:
    regkey64 = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\NSIS"
    regkey = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NSIS"
    nsis_args = "/V4 /INPUTCHARSET UTF8".split()
    exe = "makensis.exe"

    def __init__(self, build: CfgBuild, loc: CfgLOC, do_run: bool) -> None:
        self.do_run = do_run
        self.installer = NSISInstaller(build, loc)
        self.virus_scan = VirusScan(update=do_run)

    @property
    def nsis_path(self) -> Path:
        try:
            nsis_dir = winreg.QueryValue(*NSIS.regkey)
        except OSError:
            nsis_dir = winreg.QueryValue(*NSIS.regkey64)
        return Path(nsis_dir) / NSIS.exe

    def run(self, python_env: PythonEnv) -> Optional[Path]:
        if self.do_run:
            print(Title("Installer by NSIS"))
            install = self.installer.create(python_env)
            nsis = CommandMonitor(self.nsis_path, *NSIS.nsis_args, str(install.script.resolve()))
            if nsis.run(out=Title, err=Warn):
                if self.virus_scan.run_on(install.exe):
                    size = install.exe.stat().st_size / 1024
                    print(Title("Built"), Ok(str(install.exe.as_posix())), Low(f"{size:.0f} KB"))
                    return install.exe
                install.exe.unlink(missing_ok=True)
        else:
            print(Warn("Skip Installer by NSIS"))
        return None
