import configparser
import shutil
import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import Iterator, Literal, Optional, Sequence

import pkg_resources
from tap import Tap

from .color import Low, Ok, Title, Warn
from .command import CommandMonitor
from .protocols import CfgEnvironments


def get_bitness(is_64: bool) -> Literal["x64", "x86"]:
    return "x64" if is_64 else "x86"


class PythonEnv:
    undefined_version = "undefined"

    def __init__(self, environments: CfgEnvironments, want_64: Optional[bool] = None) -> None:
        # use current Python bitness if not specified
        self._want_64 = sys.maxsize == (2**63) - 1 if want_64 is None else want_64
        environment = environments.X64 if self._want_64 else environments.X86
        self._requirements = environments.requirements
        self._constraints = environment.constraints
        self._env_path = Path(environment.path)

    @cached_property
    def home(self) -> Path:
        # https://docs.python.org/3/library/venv.html#creating-virtual-environments
        pyvenv = self._env_path / "pyvenv.cfg"
        config = configparser.ConfigParser()
        config.read_string(f"[env]\n{pyvenv.read_text()}")
        return Path(config.get("env", "home"))

    @cached_property
    def exe(self) -> Path:
        return self._env_path / "scripts" / "python.exe"

    @cached_property
    def bitness(self) -> Literal["x64", "x86"]:
        return get_bitness(self.is_64)

    @cached_property
    def is_64(self) -> bool:
        script = "import sys; print(int(sys.maxsize == (2**63) - 1))"
        if is_64 := self.run_python("-c", script):
            return bool(int(is_64))
        return self._want_64

    @cached_property
    def python_version(self) -> str:
        if version := self.run_python("--version"):
            return version.split()[1]
        return PythonEnv.undefined_version

    def clear_cached_properties(self) -> None:
        del self.home
        del self.exe
        del self.bitness
        del self.is_64
        del self.python_version

    @property
    def path_str(self) -> str:
        return str(self._env_path.resolve())

    @property
    def site_packages(self) -> str:
        return str((self._env_path / "lib" / "site-packages").resolve())

    @property
    def requirements(self) -> Sequence[str]:
        return self._requirements

    @property
    def constraints(self) -> Sequence[str]:
        return self._constraints

    def run_python(self, *args: str, exe: Optional[Path] = None) -> Optional[str]:
        if self.exe.exists():
            try:
                return subprocess.run([exe or self.exe, *args], check=True, capture_output=True, text=True).stdout
            except subprocess.CalledProcessError:
                return None
        return None

    def package_version(self, package_name: str) -> str:
        script = f"import importlib.metadata; print(importlib.metadata.version('{package_name}'))"
        if version := self.run_python("-c", script):
            return version.strip()
        return PythonEnv.undefined_version

    def check(self) -> bool:
        if not self.exe.exists():
            print(Warn("No Python exe found !"))
            return False
        if self.is_64 != self._want_64:
            print(Warn("Wrong Python bitness !"))
            print(Warn("It should be"), Ok(get_bitness(self._want_64)))
            return False
        return True

    def __repr__(self) -> str:
        return "".join(
            (
                Title("In "),
                Ok(self.bitness),
                Title(" Python "),
                Ok(self.python_version),
                Title(" environment "),
                Low(str(self._env_path.parent.resolve().as_posix())),
                Low("/"),
                Ok(str(self._env_path.name)),
            )
        )

    def upgrade_python(self) -> bool:
        # need to rename the python in use
        old_exe = self.exe.with_suffix(".exe.old")
        try:
            old_exe.unlink(missing_ok=True)
        except PermissionError:
            older = old_exe.with_suffix(".older")
            older.unlink(missing_ok=True)
            old_exe.rename(older)
        self.exe.rename(old_exe)
        # upgrade from home python
        py = CommandMonitor(self.home / "python.exe", "-m", "venv", "--upgrade", self.path_str)
        if py.run(out=Title, err=Warn):
            self.clear_cached_properties()
            return True
        # undo
        old_exe.rename(self.exe)
        return False

    def clean_partially_uninstalled(self) -> None:
        site_packages = self._env_path / "Lib" / "site-packages"
        for folder in site_packages.glob("~*"):
            if folder.is_dir():
                shutil.rmtree(folder, ignore_errors=True)


# comments are turned into argparse help
class EnvArgs(Tap):
    both: bool = False  # x64 and x86 versions
    x86: bool = False  # x86 version
    x64: bool = False  # x64 version

    def process_args(self) -> None:
        if self.both:
            self.x64, self.x86 = True, True

    def get_python_envs(self, environments: CfgEnvironments) -> list[PythonEnv]:
        return [PythonEnv(environments, bitness) for bitness in self.get_bitness()]

    def get_bitness(self) -> Iterator[bool | None]:
        if self.x64 or self.x86:
            if self.x64:
                yield True
            if self.x86:
                yield False
        else:
            yield None


class PythonEnvs:
    def __init__(self, environments: CfgEnvironments, args: Optional[EnvArgs] = None) -> None:
        self.asked = args.get_python_envs(environments) if args else []
        self.all = [PythonEnv(environments, bitness) for bitness in (True, False)]
        self.x64 = PythonEnv(environments, True)
        self.x86 = PythonEnv(environments, False)


class RequiredBy:
    def __init__(self, python_env: PythonEnv) -> None:
        self._required_by: dict[str, list[str]] = {}
        for pckg in pkg_resources.WorkingSet((python_env.site_packages,)):
            for required in pckg.requires():
                self._required_by.setdefault(required.project_name, []).append(pckg.project_name)

    def get(self, name: str) -> list[str]:
        return self._required_by.get(name.lower().replace("_", "-"), [])
