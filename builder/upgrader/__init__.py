import json
import msvcrt
import os
from pathlib import Path
from typing import NamedTuple, Optional, Sequence, cast

from ..color import Stl
from ..env import PythonEnv
from .columns import Columns, Justify
from .command import CommandMonitor


class Pckg(NamedTuple):
    name: str
    version: str
    url: Optional[str]


class PckgsColumns(Columns[Pckg]):
    ...


def line_clear() -> None:
    print("\x1b[2K", end="")


def flush_input_buffer() -> None:
    while msvcrt.kbhit():
        msvcrt.getch()


class Upgrader:
    pip_install = "-m", "pip", "install", "-U", "--require-virtualenv"

    def __init__(self, python_env: PythonEnv) -> None:
        self._python_env = python_env

    def _install(self, *options: str) -> bool:
        ok = True
        with CommandMonitor(self._python_env.exe, *Upgrader.pip_install, *options) as command:
            width, _ = os.get_terminal_size()
            for line in command.lines:
                line_clear()
                if line.is_error:
                    print(Stl.warn(line.text.replace("\n", "")))
                    ok = False
                else:
                    text = line.text.replace("\n", "")[:width]
                    print(f"{text}\r", end="")
        line_clear()
        return ok

    def _to_upgrade(self, *req_files: str, eager: bool) -> list[Pckg]:
        if req_files:
            print(
                Stl.title("Check"),
                Stl.low("eagerly" if eager else "only needed"),
                Stl.title("upgrades for"),
                Stl.title(", ").join(Stl.high(req_file) for req_file in req_files),
            )

            report_file = Path("all_requirements.json")
            self._install(
                "--dry-run",
                *("--report", report_file.name),
                *sum((("-r", req_file) for req_file in req_files), ()),
                *("--upgrade-strategy", "eager" if eager else "only-if-needed"),
            )

            if report_file.exists():
                with report_file.open(mode="r", encoding="utf8") as f:
                    report = json.load(f)
                report_file.unlink()

                return [
                    Pckg(
                        name=data["name"],
                        version=data["version"],
                        url=pckg.get("download_info", {}).get("url"),
                    )
                    for pckg in cast(Sequence[dict], report["install"])
                    if (data := pckg.get("metadata"))
                ]
        return []

    def check(self, eager: bool) -> None:
        flush_input_buffer()
        to_upgrade = self._to_upgrade(*self._python_env.requirements, eager=eager)

        while True:
            n = len(to_upgrade)
            if n > 0:
                columns = PckgsColumns(to_upgrade)
                columns.add_no_column(lambda i: Stl.title(f" {i + 1}."), Justify.RIGHT)
                columns.add_attr_column(lambda pckg: Stl.high(pckg.name), Justify.LEFT)
                columns.add_attr_column(lambda pckg: Stl.warn(pckg.version), Justify.LEFT)
                print()
                print(Stl.title("Upgrade:"))
                for row in columns.rows:
                    print(*row)
            else:
                print(Stl.title("Nothing to upgrade"))
                break

            keys = input(
                f"{Stl.title('> e')}{Stl.low('xit')} {Stl.low('or')} "
                f"{Stl.title('#')} {Stl.low('?')} {Stl.title()}"
            )

            if keys == "e":
                print(Stl.title("Exit"))
                break

            if keys.isdigit() and 0 <= (i := int(keys) - 1) < n:
                pckg = to_upgrade[i]
                print()
                print(Stl.title("Install"), Stl.high(pckg.name), Stl.warn(pckg.version))
                if self._install(pckg.url or f"{pckg.name}=={pckg.version}"):
                    to_upgrade.remove(pckg)
