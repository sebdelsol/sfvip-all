from pathlib import Path
from typing import Optional

from ..env import PythonEnv
from .protocols import CfgBuild


def to_ico(img_file: str) -> str:
    assert not img_file.endswith(".ico")
    return str(Path(img_file).with_suffix(".ico").as_posix())


def repr_size(file: Path) -> str:
    if file.is_file():
        size = file.stat().st_size / 1024
        return f"{size:,.0f} kB".replace(",", " ")
    return "Unknown size"


class Dist:
    def __init__(self, build: CfgBuild) -> None:
        self.build = build

    def build_dir(self, python_env: PythonEnv) -> Path:
        return Path(self.build.dir) / "temp" / python_env.bitness

    @property
    def dist_dir_name(self) -> str:
        return f"{Path(self.build.main).stem}.dist"

    def dist_dir(self, python_env: PythonEnv) -> Path:
        return self.build_dir(python_env) / self.dist_dir_name

    def installer_exe(self, python_env: PythonEnv, version: Optional[str] = None) -> Path:
        return (
            Path(self.build.dir)
            / (version or self.build.version)
            / python_env.bitness
            / f"Install {self.build.name}.exe"
        )
