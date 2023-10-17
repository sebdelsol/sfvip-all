import logging
import platform
from pathlib import Path
from typing import NamedTuple, Optional

from cpuinfo.cpuinfo import _get_cpu_info_from_cpuid

from app_update.exe import is64_exe

logger = logging.getLogger(__name__)


class Cpu:
    class Spec(NamedTuple):
        is64: bool
        v3: bool = False

    # https://en.wikipedia.org/wiki/X86-64#Microarchitecture_levels
    _x86_64_v3_flags = {"avx", "avx2", "bmi1", "bmi2", "fma", "movbe", "osxsave", "f16c"}
    is64 = platform.machine().endswith("64")

    @staticmethod
    def spec(player_exe: Path) -> Optional[Spec]:
        # it takes ~2s to check v3 microarchitecture
        logger.info("get cpu spec")
        if (is64 := is64_exe(player_exe)) is not None:
            if is64 and Cpu.is64 and (cpu_info := _get_cpu_info_from_cpuid()):
                cpu_flags = set(cpu_info.get("flags", []))
                x86_64_v3 = Cpu._x86_64_v3_flags.issubset(cpu_flags)
            else:
                x86_64_v3 = False
            return Cpu.Spec(is64, x86_64_v3)
        return None
