from typing import Iterator, Optional

from tap import Tap

from ..utils.protocols import CfgEnvironments
from . import PythonEnv


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
        self.declarations = dict(x64=environments.X64, x86=environments.X86)
