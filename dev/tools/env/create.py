import sys
from pathlib import Path
from types import ModuleType

from shared.version import Version

from ..utils.color import Low, Ok, Title, Warn
from ..utils.command import CommandMonitor
from ..utils.protocols import CfgEnvironments
from . import PythonEnv, get_bitness_str


def run_exe(exe: Path | str, *args: str) -> bool:
    return CommandMonitor(exe, *args).run(out=Title, err=Warn)


def running_version(length: int) -> Version:
    return Version(".".join(map(str, sys.version_info[:length])))


def running_bitness() -> bool:
    return sys.maxsize == (2**63) - 1


class CreatePythonEnv(PythonEnv):
    _venv = "-m", "venv"
    _install = "-m", "pip", "install"
    _upgrade_pip = *_install, "--upgrade", "pip"

    def __init__(self, environments: CfgEnvironments) -> None:
        super().__init__(environments, running_bitness())

    def handle_in_use(self) -> None:
        if self.exe.exists():
            old_exe = self.clean_old_exe()
            self.exe.rename(old_exe)

    def right_python(self, calling_module: ModuleType) -> bool:
        if self._env_path.name in Path(sys.executable).parts or running_version(2) != self._want_python:
            print(Warn("You should use:"), end=" ")
            module_name = calling_module.__spec__.name if calling_module.__spec__ else ""
            print(Ok(f"py -{self._want_python}-{'64' if self.bitness else '32'} -m {module_name}"))
            return False
        return True

    def create(self) -> bool:
        print(Title("Create"), Ok(f"{self._env_path} environment"), end=" ")
        print(Low("based on"), Ok(f"Python {running_version(3)}"), Ok(get_bitness_str(self._want_64)))
        return run_exe(sys.executable, *CreatePythonEnv._venv, self.path_str)

    def upgrade_pip(self) -> bool:
        print(Title("Upgrade"), Ok("pip"))
        return run_exe(self.exe, *CreatePythonEnv._upgrade_pip)

    def install_requirements(self) -> bool:
        print(Title("Install"), Ok(", ".join((*self.requirements, *self.constraints))))
        requirements = sum((("-r", requirements) for requirements in self.requirements), ())
        constraints = sum((("-c", constraints) for constraints in self.constraints), ())
        return run_exe(self.exe, *CreatePythonEnv._install, *requirements, *constraints)

    def create_and_install(self, calling_module: ModuleType) -> None:
        if self.right_python(calling_module):
            self.handle_in_use()
            self.create()
            self.upgrade_pip()
            self.install_requirements()
