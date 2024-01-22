import logging
import platform
import sys
from typing import Literal, Self


def get_bitness_str(is_64: bool) -> Literal["x64", "x86"]:
    return "x64" if is_64 else "x86"


def is_py_installer() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def is_nuitka() -> bool:
    return "__compiled__" in globals()


def is_built() -> bool:
    return is_py_installer() or is_nuitka()


class LogProcess:
    def __init__(self, logger: logging.Logger, name: str) -> None:
        self.logger = logger
        self.name = name

    def __enter__(self) -> Self:
        self.logger.info("%s process started", self.name)
        bitness = get_bitness_str(platform.machine().endswith("64"))
        self.logger.info("Run Python %s %s", platform.python_version(), bitness)
        if is_py_installer():
            self.logger.info("Build by PyInstaller")
        elif is_nuitka():
            self.logger.info("Build by Nuitka")
        return self

    def __exit__(self, *_) -> None:
        self.logger.info("%s process stopped", self.name)
