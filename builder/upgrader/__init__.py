import json
import msvcrt
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple, Optional

from ..color import Stl
from ..command import CommandMonitor
from ..env import PythonEnv
from .columns import Columns, Justify


class _Pckg(NamedTuple):
    name: str
    version: str
    url: Optional[str]


class _PckgsColumns(Columns[_Pckg]):
    ...


def _flush_input_buffer() -> None:
    while msvcrt.kbhit():
        msvcrt.getch()


class Upgrader:
    pip_install = "-m", "pip", "install", "--upgrade", "--require-virtualenv"
    pip_freeze = "-m", "pip", "freeze", "--quiet", "--exclude-editable"
    report_file = "all_requirements.json"

    def __init__(self, python_env: PythonEnv) -> None:
        self._python_env = python_env

    def _install(self, *options: str) -> bool:
        pip = CommandMonitor(self._python_env.exe, *Upgrader.pip_install, *options)
        return pip.run(out=Stl.low, err=Stl.warn)

    def _upgrade(self, eager: bool, dry_run: bool) -> list[_Pckg]:
        if self._python_env.requirements:
            if dry_run:
                print(
                    Stl.title("Check upgrades"),
                    Stl.low("eagerly" if eager else "only needed"),
                    Stl.title("for"),
                    Stl.high(", ".join(self._python_env.requirements)),
                )
            with tempfile.TemporaryDirectory() as temp_dir:
                report_file = Path(temp_dir) / Upgrader.report_file
                self._install(
                    *(("--dry-run",) if dry_run else ()),
                    *("--report", str(report_file)),
                    *sum((("-r", req_file) for req_file in self._python_env.requirements), ()),
                    *("--upgrade-strategy", "eager" if eager else "only-if-needed"),
                )
                if report_file.exists():
                    with report_file.open(mode="r", encoding="utf8") as f:
                        report = json.load(f)
                    return [
                        _Pckg(
                            name=data["name"],
                            version=data["version"],
                            url=pckg.get("download_info", {}).get("url"),
                        )
                        for pckg in report["install"]
                        if (data := pckg.get("metadata"))
                    ]
        return []

    def _install_package(self, pckg: _Pckg) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            # constraint the pckg installation with all other pckg versions in the environment
            constraints = Path(temp_dir) / "current-env.txt"
            freeze = subprocess.run(
                (self._python_env.exe, *Upgrader.pip_freeze, "--exclude", pckg.name),
                capture_output=True,
                check=False,
                text=True,
            )
            constraints.write_text(freeze.stdout)
            if self._install(pckg.url or f"{pckg.name}=={pckg.version}", "-r", str(constraints)):
                return True
        return False

    def check(self, eager: bool) -> None:
        _flush_input_buffer()
        to_upgrade = self._upgrade(eager, dry_run=True)
        while True:
            n = len(to_upgrade)
            if n > 0:
                columns = _PckgsColumns(to_upgrade)
                columns.add_no_column(lambda i: Stl.title(f" {i + 1}."), Justify.RIGHT)
                columns.add_attr_column(lambda pckg: Stl.high(pckg.name), Justify.LEFT)
                columns.add_attr_column(lambda pckg: Stl.warn(pckg.version), Justify.LEFT)
                print(Stl.title("Upgrade:"))
                for row in columns.rows:
                    print(*row)
            else:
                print(Stl.title("Nothing to upgrade"))
                break
            keys = input(
                f"{Stl.title('> E')}{Stl.low('xit,')} {Stl.title('A')}{Stl.low('ll')} "
                f"{Stl.low('or a package')} {Stl.title('#')} {Stl.low('?')} {Stl.title()}"
            ).lower()
            if keys == "e":
                print(Stl.title("Exit"))
                break
            if keys == "a":
                print(Stl.title("Install"), Stl.high("all"))
                upgraded = self._upgrade(eager, dry_run=False)
                to_upgrade = [pckg for pckg in to_upgrade if pckg not in upgraded]  # keep to_upgrade in order
            elif keys.isdigit() and 0 <= (i := int(keys) - 1) < n:
                pckg = to_upgrade[i]
                print(Stl.title("Install"), Stl.high(pckg.name), Stl.warn(pckg.version))
                if self._install_package(pckg):
                    to_upgrade.remove(pckg)
