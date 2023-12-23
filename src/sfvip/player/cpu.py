import logging
import platform
import struct
from pathlib import Path
from typing import NamedTuple, Optional

from cpuinfo.cpuinfo import _get_cpu_info_from_cpuid

logger = logging.getLogger(__name__)

_MACHINE_I386 = 332
_MACHINE_AMD64 = 34404


def is64_exe(exe: Path) -> Optional[bool]:
    if exe.is_file():
        with exe.open("rb") as f:
            s = f.read(2)
            if s == b"MZ":  # exe ?
                f.seek(60)
                s = f.read(4)
                header_offset = struct.unpack("<L", s)[0]
                f.seek(header_offset + 4)
                s = f.read(2)
                machine = struct.unpack("<H", s)[0]
                if machine == _MACHINE_AMD64:
                    return True
                if machine == _MACHINE_I386:
                    return False
    return None


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
        logger.info("Get cpu spec")
        if (is64 := is64_exe(player_exe)) is not None:
            if is64 and Cpu.is64 and (cpu_info := _get_cpu_info_from_cpuid()):
                cpu_flags = set(cpu_info.get("flags", []))
                x86_64_v3 = Cpu._x86_64_v3_flags.issubset(cpu_flags)
            else:
                x86_64_v3 = False
            return Cpu.Spec(is64, x86_64_v3)
        return None
