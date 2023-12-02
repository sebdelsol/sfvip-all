import sys
from pathlib import Path

from shared.version import Version

from ..utils.color import Low, Ok, Title, Warn
from ..utils.command import CommandMonitor
from ..utils.protocols import CfgEnvironments
from . import PythonEnv


def run_exe(exe: Path | str, *args: str) -> bool:
    return CommandMonitor(exe, *args).run(out=Title, err=Warn)


def running_version(length: int) -> Version:
    return Version(".".join(map(str, sys.version_info[:length])))


def running_bitness() -> bool:
    return sys.maxsize == (2**63) - 1


class CreatePythonEnv(PythonEnv):
    _install = "-m", "pip", "install"
    _venv = "-m", "venv"
    _upgrade_pip = "--upgrade", "pip"

    def __init__(self, environments: CfgEnvironments) -> None:
        super().__init__(environments, running_bitness())

    def handle_in_use(self) -> None:
        if self.exe.exists():
            old_exe = self.clean_old_exe()
            self.exe.rename(old_exe)

    def check(self) -> bool:
        if self._env_path.name in Path(sys.executable).parts or running_version(2) != self._want_python:
            print(Warn("You should use:"))
            print(Ok(f"py -{self._want_python}-{'64' if self.bitness else '32'} -m dev.create"))
            return False
        return True

    def create(self) -> bool:
        return run_exe(sys.executable, *CreatePythonEnv._venv, self.path_str)

    def upgrade_pip(self) -> bool:
        print(Title("Upgrade"), Ok("pip"))
        return run_exe(self.exe, *CreatePythonEnv._install, *CreatePythonEnv._upgrade_pip)

    def install_requirements(self) -> bool:
        print(Title("Install"), Ok(", ".join((*self.requirements, *self.constraints))))
        requirements = sum((("-r", requirements) for requirements in self.requirements), ())
        constraints = sum((("-c", constraints) for constraints in self.constraints), ())
        return run_exe(self.exe, *CreatePythonEnv._install, *requirements, *constraints)

    def __repr__(self) -> str:
        return "".join(
            (
                Ok(f"{self._env_path} environment"),
                Low(" based on "),
                Ok(f"Python {running_version(3)}"),
            )
        )

    def create_and_install(self) -> None:
        print(Title("Create"), str(self))
        if self.check():
            self.handle_in_use()
            self.create()
            self.upgrade_pip()
            self.install_requirements()
