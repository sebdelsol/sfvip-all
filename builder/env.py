import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import Optional

from tap import Tap

from .color import Stl
from .protocols import ConfigEnvironments


def get_bitness_str(is_64bit: bool) -> str:
    return "x64" if is_64bit else "x86"


class PythonEnv:
    def __init__(self, environments: Optional[ConfigEnvironments] = None, is_64: Optional[bool] = None) -> None:
        # env = None for current running python
        if environments is None:
            self._exe = Path(sys.executable)
            self._env = self._exe.parent.parent
        else:
            self._env = Path(environments.x64 if is_64 else environments.x86)
            self._exe = self._env / "scripts" / "python.exe"
        self._should_be_64 = is_64

    @property
    def exe(self) -> Path:
        return self._exe

    @cached_property
    def is_64(self) -> bool:
        script = "import sys; sys.exit(int(sys.maxsize == (2**63) - 1))"
        is_64 = subprocess.run([self._exe, "-c", script], check=False)
        return bool(is_64.returncode)

    @cached_property
    def python_version(self) -> str:
        version = subprocess.run([self._exe, "--version"], check=True, capture_output=True, text=True)
        return version.stdout.replace("\n", "").split()[1]

    def package_version(self, package_name: str) -> str:
        script = f"import importlib.metadata; print(importlib.metadata.version('{package_name}'))"
        version = subprocess.run([self._exe, "-c", script], check=False, capture_output=True, text=True)
        return version.stdout.strip()

    def print(self) -> None:
        print(
            Stl.title("In "),
            Stl.high(get_bitness_str(self.is_64)),
            Stl.title(" Python "),
            Stl.high(self.python_version),
            Stl.title(" environment "),
            Stl.low(str(self._env.parent.resolve())),
            Stl.low("\\"),
            Stl.high(str(self._env.name)),
            sep="",
        )

    def check(self) -> bool:
        if not self._exe.exists():
            print(Stl.warn("No Python exe found in the environement !"))
            return False
        if self._should_be_64 is not None and self.is_64 != self._should_be_64:
            print(
                Stl.warn("Wrong Python bitness !"),
                Stl.low("it should be"),
                Stl.high(get_bitness_str(self._should_be_64)),
            )
            return False
        return True


class EnvArgs(Tap):
    both: bool = False  # x64 and x86 versions
    x86: bool = False  # x86 version
    x64: bool = False  # x64 version

    def process_args(self):
        if self.both:
            self.x64, self.x86 = True, True

    def get_python_envs(self, environments: ConfigEnvironments) -> set[PythonEnv]:
        envs = set()
        if self.x64:
            envs.add(PythonEnv(environments, is_64=True))
        if self.x86:
            envs.add(PythonEnv(environments, is_64=False))
        if not envs:
            envs.add(PythonEnv())
        return envs
