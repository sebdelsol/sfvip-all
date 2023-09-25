import hashlib
import struct
from pathlib import Path
from typing import Optional

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


def compute_md5(path: Path, chunk_size: int = 2**20):
    hash_md5 = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
