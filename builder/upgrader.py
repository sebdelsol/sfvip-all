import json
import msvcrt
import os
import subprocess
from pathlib import Path
from typing import NamedTuple, Optional, Sequence, cast

from .color import Stl
from .columns import Columns
from .env import PythonEnv


class Pckg(NamedTuple):
    name: str
    version: str
    url: Optional[str]


class PckgsColumns(Columns[Pckg]):
    ...


def line_clear() -> None:
    print("\x1b[2K", end="")


class Upgrader:
    pip_install = "-m", "pip", "install", "-U", "--require-virtualenv"

    def __init__(self, python_env: PythonEnv) -> None:
        if python_env.check():
            self.python_exe = python_env.exe
        else:
            print(Stl.warn("No Python exe found:"), Stl.high(str(python_env.exe.resolve())))
            self.python_exe = None

    def _install(self, *options: str) -> None:
        assert self.python_exe
        with subprocess.Popen(
            (self.python_exe, *Upgrader.pip_install, *options),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            text=True,
        ) as proc:
            if proc.stdout:
                width, _ = os.get_terminal_size()
                for line in proc.stdout:
                    line_clear()
                    if "error" in line.lower():
                        print(Stl.warn(line.replace("\n", "")))
                    else:
                        line = line.replace("\n", "")[:width]
                        print(f"{line}\r", end="")
            line_clear()

    def _to_upgrade(self, *req_files: str, eager: bool) -> list[Pckg]:
        if req_files:
            print(
                Stl.title("Check"),
                Stl.low("eagerly" if eager else "only needed"),
                Stl.title("upgrades for"),
                Stl.low(" and ").join(Stl.high(req_file) for req_file in req_files),
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

    @staticmethod
    def _show_upgrade(to_upgrade: list[Pckg]) -> int:
        if (n := len(to_upgrade)) > 0:
            columns = PckgsColumns(to_upgrade)
            columns.add_no_column(lambda i: Stl.title(f" {i + 1}."), Columns.Justify.RIGHT)
            columns.add_attr_column(lambda pckg: Stl.high(pckg.name), Columns.Justify.LEFT)
            columns.add_attr_column(lambda pckg: Stl.warn(pckg.version), Columns.Justify.LEFT)
            print()
            print(Stl.title("Upgrade:"))
            for row in columns.rows:
                print(*row)
        return n

    def install_for(self, *req_files: str, eager: bool) -> None:
        if not self.python_exe:
            return
        # flush the input buffer
        while msvcrt.kbhit():
            msvcrt.getch()

        to_upgrade = self._to_upgrade(*req_files, eager=eager)

        while True:
            n = self._show_upgrade(to_upgrade)

            if n == 0:
                print(Stl.title("Nothing to upgrade"))
                break

            key = input(
                f"{Stl.title('> e')}{Stl.low('xit')} {Stl.low('or')} "
                f"{Stl.title('#')} {Stl.low('?')} {Stl.title()}"
            )

            if key == "e":
                print(Stl.title("Exit"))
                break

            if key.isdigit() and 0 <= (i := int(key) - 1) < n:
                pckg = to_upgrade[i]
                print()
                print(
                    Stl.title("Install"),
                    Stl.high(pckg.name),
                    Stl.warn(pckg.version),
                )
                self._install(pckg.url or f"{pckg.name}=={pckg.version}")
                to_upgrade.remove(pckg)
