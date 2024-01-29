import os
from pathlib import Path
from typing import Iterator

from winpty import Backend, PtyProcess

from ..color import ToStyle
from . import clear_lines


class PtyMonitor:
    def __init__(self, exe_path: Path | str, *args: str) -> None:
        exe = str(exe_path.resolve()) if isinstance(exe_path, Path) else exe_path
        self._dimension = os.get_terminal_size()[::-1]
        self._args = [exe, *args]

    @staticmethod
    def readline(process: PtyProcess) -> Iterator[str]:
        buf = ""
        while process.isalive():
            try:
                ch = process.read(1)
            except EOFError:
                yield buf
            else:
                buf += ch
                if ch in ("\r", "\n"):
                    yield buf
                    buf = ""

    def run(self, out: ToStyle) -> bool:
        process = PtyProcess.spawn(self._args, dimensions=self._dimension, backend=Backend.WinPTY)
        n_lines = 0
        for line in self.readline(process):
            clear_lines(n_lines)
            print(out(line), end="")
            n_lines = 1 if line.endswith("\n") else 0
        clear_lines(n_lines)
        ok = process.exitstatus == 0
        del process
        return ok
