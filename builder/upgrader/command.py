import queue
import threading
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, Iterator, NamedTuple, Optional


class Line(NamedTuple):
    text: str
    is_error: bool


class CommandMonitor(Popen):
    """monitor command stdout and stderr in realtime"""

    def __init__(self, exe_path: Path, *args: str) -> None:
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

    @property
    def lines(self) -> Iterator[Line]:
        def jobs_completed() -> bool:
            return all(done.is_set() for done in jobs)

        jobs = self._monitor(self.stdout, False), self._monitor(self.stderr, True)
        while not jobs_completed():
            for line in iter(self._queue.get, None):
                yield line
