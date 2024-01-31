import os
import queue
import textwrap
import threading
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, Iterator, NamedTuple, Optional

from ..utils.color import Low, ToStyle, Warn
from . import clear_lines


class _Line(NamedTuple):
    text: str
    is_error: bool


class CommandMonitor:
    """monitor command stdout and stderr in realtime"""

    def __init__(self, exe_path: Path | str, *args: str) -> None:
        self._args = exe_path, *args
        self._width = os.get_terminal_size()[0]
        self._queue: queue.Queue[Optional[_Line]] = queue.Queue()

    def _monitor(self, io: Optional[IO[str]], is_error: bool) -> threading.Event:
        def queue_lines() -> None:
            for text in io or ():
                self._queue.put(_Line(text, is_error))
            done.set()
            self._queue.put(None)

        done = threading.Event()
        threading.Thread(target=queue_lines).start()
        return done

    def _lines(self, process: Popen[str]) -> Iterator[_Line]:
        def completed() -> bool:
            return all(done.is_set() for done in done_flags)

        done_flags = self._monitor(process.stdout, False), self._monitor(process.stderr, True)
        while not completed():
            for line in iter(self._queue.get, None):
                yield line

    def run(
        self,
        out: Optional[ToStyle] = None,
        err: Optional[ToStyle] = None,
        keep_error: bool = True,
        err_is_out: bool = False,
    ) -> bool:
        with Popen(
            self._args,
            stdout=PIPE if out else None,
            stderr=PIPE if err else None,
            bufsize=0,
            text=True,
        ) as process:
            error = False
            n_lines = 0
            out = out or Low
            err = err or Warn
            for line in self._lines(process):
                is_error = line.is_error and not err_is_out
                error |= is_error
                if is_error and keep_error:
                    print(err(line.text.replace("\n", "")))
                    n_lines = 0
                else:
                    clear_lines(n_lines)
                    lines = textwrap.wrap(line.text, width=self._width)
                    to_style = err if is_error else out
                    n_lines = len(lines)
                    for text in lines:
                        print(to_style(text))
            clear_lines(n_lines)
        return not (error or process.returncode)
