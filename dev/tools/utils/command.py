import os
import queue
import textwrap
import threading
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, Iterator, NamedTuple, Optional

from .color import Low, ToStyle, Warn


class _Line(NamedTuple):
    text: str
    is_error: bool


def _line_clear() -> None:
    print("\033[2K", end="")


def _line_back() -> None:
    print("\033[F", end="")


def clear_lines(n: int) -> None:
    for _ in range(n):
        _line_clear()
        _line_back()
        _line_clear()


class CommandMonitor:
    """monitor command stdout and stderr in realtime"""

    def __init__(self, exe_path: Path, *args: str) -> None:
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

    def _lines(self, process: Popen) -> Iterator[_Line]:
        def completed() -> bool:
            return all(done.is_set() for done in done_flags)

        done_flags = self._monitor(process.stdout, False), self._monitor(process.stderr, True)
        while not completed():
            for line in iter(self._queue.get, None):
                yield line

    def run(self, out: Optional[ToStyle] = None, err: Optional[ToStyle] = None) -> bool:
        with Popen(
            self._args,
            stdout=PIPE if out else None,
            stderr=PIPE if err else None,
            bufsize=0,
            text=True,
        ) as process:
            ok = True
            n_lines = 0
            out = out or Low
            err = err or Warn
            for line in self._lines(process):
                if line.is_error:
                    print(err(line.text.replace("\n", "")))
                    n_lines = 0
                    ok = False
                else:
                    clear_lines(n_lines)
                    lines = textwrap.wrap(line.text, width=self._width)
                    n_lines = len(lines)
                    for text in lines:
                        print(out(text))
            clear_lines(n_lines)
        return ok and not process.returncode
