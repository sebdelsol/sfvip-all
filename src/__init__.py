# done before everything else is imported
# to be sure it'll be the very last to execute
import atexit
from typing import Callable


class AtVeryLast:
    def __init__(self) -> None:
        self._last_action = None
        atexit.register(self._at_last)

    def _at_last(self) -> None:
        if self._last_action:
            self._last_action()

    def register(self, last_action: Callable[[], None]) -> None:
        self._last_action = last_action


at_very_last = AtVeryLast()

# pylint: disable=wrong-import-position
import logging
import sys


def is_py_installer() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def is_nuitka() -> bool:
    return "__compiled__" in globals()


def is_built() -> bool:
    return is_py_installer() or is_nuitka()


def set_logging() -> None:
    if is_py_installer():
        # pylint: disable=import-outside-toplevel
        import time
        from pathlib import Path

        from build_config import Build

        time_ms = round(time.time() * 1000)
        logfile = Path(Build.logs_dir) / f"{Build.name} - {time_ms}.log"
    else:
        logfile = None  # it's handled in dev.builder.nuitka

    logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s - %(message)s")
    if is_py_installer():
        logging.info("build by PyInstaller")
    elif is_nuitka():
        logging.info("build by Nuitka")
