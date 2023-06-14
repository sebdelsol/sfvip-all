import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import Optional

from .color import Stl


def get_bitness_str(is_64bit: bool) -> str:
    return "x64" if is_64bit else "x86"


class PythonEnv:
    def __init__(self, env: Optional[str] = None) -> None:
        # env = None for current running python
        if env is None:
            self._env = Path(sys.executable).parent.parent
            self._exe = None
        else:
            self._env = Path(env)
            self._exe = self._env / "scripts" / "python.exe"

    @property
    def exe(self) -> Path:
        return Path(sys.executable) if self._exe is None else self._exe

    @cached_property
    def is_64bit(self) -> bool:
        if self._exe:
            script = "import sys; sys.exit(int(sys.maxsize == (2**63) - 1))"
            is_64 = subprocess.run([self._exe, "-c", script], check=False)
            return bool(is_64.returncode)
        return sys.maxsize == (2**63) - 1

    @cached_property
    def version(self) -> str:
        if self._exe:
            version = subprocess.run([self._exe, "--version"], check=True, capture_output=True, text=True)
            return version.stdout.replace("\n", "").split()[1]
        return sys.version.split(" ", maxsplit=1)[0]

    def print(self) -> None:
        print(
            Stl.high(get_bitness_str(self.is_64bit)),
            Stl.title(" environment "),
            Stl.low(str(self._env.parent.resolve())),
            Stl.low("\\"),
            Stl.high(str(self._env.name)),
            sep="",
        )

    def check(self, is_64: Optional[bool] = None) -> bool:
        if self._exe and not self._exe.exists():
            print(Stl.warn("No Python exe found in the environement !"))
            return False
        if is_64 is not None and self.is_64bit != is_64:
            print(Stl.warn("Wrong Python bitness !"), Stl.low("it should be"), Stl.high(get_bitness_str(is_64)))
            return False
        return True
