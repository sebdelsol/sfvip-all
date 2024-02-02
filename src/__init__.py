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


# pylint: disable=import-outside-toplevel, import-outside-toplevel
def set_logging_and_exclude(*log_polluters: str) -> None:
    import logging

    from shared import is_py_installer

    if is_py_installer():
        import os
        import sys
        import time
        import traceback
        from pathlib import Path
        from types import TracebackType
        from typing import NoReturn

        from build_config import Build

        class StreamToLogger:
            def __init__(self, logger_write: Callable[[str], None]):
                self.logger_write = logger_write
                self.buf: list[str] = []

            def write(self, msg: str):
                if msg.endswith("\n"):
                    self.buf.append(msg.removesuffix("\n"))
                    self.logger_write("".join(self.buf))
                    self.buf = []
                else:
                    self.buf.append(msg)

            def flush(self):
                pass

        def excepthook(_type: type[BaseException], _value: BaseException, _traceback: TracebackType) -> NoReturn:
            traceback.print_exception(_type, _value, _traceback)
            sys.exit(0)  # pyinstaller won't show its crash window

        sys.excepthook = excepthook  # remove the pyinstaller crash window in the main thread
        sys.stderr = StreamToLogger(logging.error)  # add exception traceback in loggging.error
        logfile = Path(Build.logs_dir) / f"{Build.name} - {round(time.time() * 1000)} - {os.getpid()}.log"
    else:
        logfile = None  # it's handled in dev.builder.nuitka

    logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s - %(message)s")

    # do not pollute the log
    for polluter in log_polluters:
        logging.getLogger(polluter).setLevel(logging.WARNING)
