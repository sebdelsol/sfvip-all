import os
from pathlib import Path
from typing import Iterator, Self

from winpty import Backend, PtyProcess

from ..utils.color import ToStyle
from . import clear_lines


class _PtyProcess:
    def __init__(self, exe_path: Path | str, *args: str) -> None:
        if isinstance(exe_path, Path):
            exe_path = str(exe_path.resolve())
        self._process = PtyProcess.spawn(
            [exe_path, *args],
            dimensions=os.get_terminal_size()[::-1],
            backend=Backend.WinPTY,
        )

    def readlines(self) -> Iterator[str]:
        line = ""
        while self._process.isalive():
            try:
                char = self._process.read(1)
            except EOFError:
                yield line
            else:
                line += char
                if char in ("\r", "\n"):
                    yield line
                    line = ""

    @property
    def exit_without_error(self) -> bool:
        return self._process.exitstatus == 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        del self._process


class PtyMonitor:
    def __init__(self, exe_path: Path | str, *args: str) -> None:
        self._exe_path = exe_path
        self._args = args

    def run(self, out: ToStyle) -> bool:
        with _PtyProcess(self._exe_path, *self._args) as process:
            n_lines = 0
            for line in process.readlines():
                clear_lines(n_lines)
                print(out(line), end="")
                n_lines = 1 if line.endswith("\n") else 0
            clear_lines(n_lines)
            return process.exit_without_error
