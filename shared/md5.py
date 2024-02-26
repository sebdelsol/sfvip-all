import hashlib
from pathlib import Path


def compute_md5(exe: Path, chunk_size: int = 2**20) -> str:
    hash_md5 = hashlib.md5()
    with exe.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
