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
import platform
import sys

from shared import get_bitness_str

logger = logging.getLogger(__name__)


def is_py_installer() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def is_nuitka() -> bool:
    return "__compiled__" in globals()


def is_built() -> bool:
    return is_py_installer() or is_nuitka()


log_polluters = "ipytv.playlist", "ipytv.channel", "mitmproxy.proxy.server"


def set_logging(from_) -> None:
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

    if from_ == "__main__":
        logger.info(
            "Run Python %s %s",
            platform.python_version(),
            get_bitness_str(platform.machine().endswith("64")),
        )
        if is_py_installer():
            logger.info("Build by PyInstaller")
        elif is_nuitka():
            logger.info("Build by Nuitka")
    else:
        # do not pollute the log
        for polluter in log_polluters:
            logging.getLogger(polluter).setLevel(logging.WARNING)
