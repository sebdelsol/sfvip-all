import os
import queue
import textwrap
import threading
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, NamedTuple, Optional

from ..color import ToStyle


class Line(NamedTuple):
    text: str
    is_error: bool


def lines_clear(n: int) -> None:
    for _ in range(n):
        print("\033[F", end="")  # back one line
        print("\033[K", end="")  # line clear


class CommandMonitor(Popen):
    """monitor command stdout and stderr in realtime"""

    def __init__(self, exe_path: Path, *args: str) -> None:
        self._width = os.get_terminal_size()[0]
        self._queue: queue.Queue[Optional[Line]] = queue.Queue()
        super().__init__((exe_path, *args), stdout=PIPE, stderr=PIPE, bufsize=0, text=True)

    def _monitor(self, io: Optional[IO[str]], is_error: bool) -> threading.Event:
        def get_lines() -> None:
            for text in io or ():
                self._queue.put(Line(text, is_error))
            done.set()
            self._queue.put(None)

        done = threading.Event()
        threading.Thread(target=get_lines).start()
        return done

    def run(self, out: ToStyle, error: ToStyle) -> bool:
        ok = True
        done_flags = self._monitor(self.stdout, False), self._monitor(self.stderr, True)
        while not all(done.is_set() for done in done_flags):
            n_lines = 0
            for line in iter(self._queue.get, None):
                if line.is_error:
                    print(error(line.text.replace("\n", "")))
                    n_lines = 0
                    ok = False
                else:
                    lines_clear(n_lines)
                    lines = textwrap.wrap(line.text, width=self._width)
                    n_lines = len(lines)
                    for text in lines:
                        print(out(text))
            lines_clear(n_lines)
        return ok
