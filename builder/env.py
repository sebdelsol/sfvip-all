import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import Sequence

from tap import Tap

from .color import Stl
from .protocols import CfgEnvironments


def get_bitness_str(is_64: bool) -> str:
    return "x64" if is_64 else "x86"


class PythonEnv:
    undefined_version = "undefined"

    def __init__(self, environments: CfgEnvironments, want_64: bool | None = None) -> None:
        # use current Python bitness if not specified
        self._want_64 = sys.maxsize == (2**63) - 1 if want_64 is None else want_64
        env_cfg = environments.X64 if self._want_64 else environments.X86
        self._env_path = Path(env_cfg.path)
        self._exe = self._env_path / "scripts" / "python.exe"
        self._requirements = env_cfg.requirements

    @property
    def exe(self) -> Path:
        return self._exe

    @property
    def requirements(self) -> Sequence[str]:
        return self._requirements

    @cached_property
    def is_64(self) -> bool:
        if self._exe.exists():
            script = "import sys; sys.exit(int(sys.maxsize == (2**63) - 1))"
            is_64 = subprocess.run([self._exe, "-c", script], check=False)
            return bool(is_64.returncode)
        return self._want_64

    @cached_property
    def python_version(self) -> str:
        if self._exe.exists():
            version = subprocess.run([self._exe, "--version"], check=True, capture_output=True, text=True)
            return version.stdout.replace("\n", "").split()[1]
        return PythonEnv.undefined_version

    def package_version(self, package_name: str) -> str:
        if self._exe.exists():
            script = f"import importlib.metadata; print(importlib.metadata.version('{package_name}'))"
            version = subprocess.run([self._exe, "-c", script], check=False, capture_output=True, text=True)
            return version.stdout.strip()
        return PythonEnv.undefined_version

    def print(self) -> None:
        print(
            Stl.title("In "),
            Stl.high(get_bitness_str(self.is_64)),
            Stl.title(" Python "),
            Stl.high(self.python_version),
            Stl.title(" environment "),
            Stl.low(str(self._env_path.parent.resolve().as_posix())),
            Stl.low("/"),
            Stl.high(str(self._env_path.name)),
            sep="",
        )

    def check(self) -> bool:
        if not self._exe.exists():
            print(Stl.warn("No Python exe found !"))
            return False
        if self.is_64 != self._want_64:
            print(Stl.warn("Wrong Python bitness !"))
            print(Stl.warn("It should be"), Stl.high(get_bitness_str(self._want_64)))
            return False
        return True


class EnvArgs(Tap):
    both: bool = False  # x64 and x86 versions
    x86: bool = False  # x86 version
    x64: bool = False  # x64 version

    def process_args(self) -> None:
        if self.both:
            self.x64, self.x86 = True, True

    def get_python_envs(self, environments: CfgEnvironments) -> list[PythonEnv]:
        envs = []
        if self.x64:
            envs.append(PythonEnv(environments, want_64=True))
        if self.x86:
            envs.append(PythonEnv(environments, want_64=False))
        if not envs:
            envs.append(PythonEnv(environments))
        return envs
