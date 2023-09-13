import json
import msvcrt
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple, Optional

from ..color import Low, Ok, Title, Warn
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


def _plural(text: str, n: int, plural: str = "s") -> str:
    return f"{text}{plural if n > 1 else ''}"


class Upgrader:
    _prompt = Title("> Choose e"), Ok("xit, "), Title("a"), Ok("ll or "), Title("# "), Ok("? ")
    _pip_install = "-m", "pip", "install", "--upgrade", "--require-virtualenv"
    _pip_freeze = "-m", "pip", "freeze", "--quiet", "--exclude-editable"

    def __init__(self, python_env: PythonEnv) -> None:
        self._python_env = python_env

    def _install(self, *options: str) -> bool:
        pip = CommandMonitor(self._python_env.exe, *Upgrader._pip_install, *options)
        return pip.run(out=Low, err=Warn)

    def _upgrade(self, eager: bool, dry_run: bool) -> list[_Pckg]:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_file = Path(temp_dir) / "report.json"
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
            try:
                freeze = subprocess.run(
                    (self._python_env.exe, *Upgrader._pip_freeze, "--exclude", pckg.name),
                    capture_output=True,
                    check=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                pass
            else:
                constraints.write_text(freeze.stdout)
                if self._install(pckg.url or f"{pckg.name}=={pckg.version}", "-r", str(constraints)):
                    return True
        return False

    def check(self, eager: bool) -> None:
        if not self._python_env.requirements:
            print(Warn("No requirements to check"))
            return
        print(
            Title("Check upgrades"),
            Low(f"{'eagerly' if eager else 'only needed'} for"),
            Ok(", ".join(self._python_env.requirements)),
        )
        to_upgrade: list[_Pckg] = self._upgrade(eager, dry_run=True)
        while True:
            n = len(to_upgrade)
            if n > 0:
                columns = _PckgsColumns(to_upgrade)
                columns.add_no_column(lambda i: Title(f" {i + 1}."), Justify.RIGHT)
                columns.add_attr_column(lambda pckg: Ok(pckg.name), Justify.LEFT)
                columns.add_attr_column(lambda pckg: Warn(pckg.version), Justify.LEFT)
                print()
                print(Title("Available"), Ok(f"{_plural('upgrade', len(columns.rows))}:"))
                for row in columns.rows:
                    print(row)
            else:
                print(Title("Nothing to upgrade"))
                break
            print()
            print(*Upgrader._prompt, end="", sep="")
            _flush_input_buffer()
            match input(Title()).lower():
                case "e":
                    print(Title("Exit"))
                    break
                case "a":
                    print(Title("Install"), Ok(f"all {_plural('package', len(columns.rows))}"))
                    upgraded = self._upgrade(eager, dry_run=False)
                    to_upgrade = [pckg for pckg in to_upgrade if pckg not in upgraded]  # keep to_upgrade in order
                case choice if choice.isdigit() and 0 <= (i := int(choice) - 1) < n:
                    pckg = to_upgrade[i]
                    print(Title("Install"), " ".join(columns.rows[i].split()))
                    if self._install_package(pckg):
                        to_upgrade.remove(pckg)
