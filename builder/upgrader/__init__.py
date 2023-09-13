import json
import msvcrt
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


def _flushed_input(text: str) -> str:
    while msvcrt.kbhit():
        msvcrt.getch()
    return input(text)


class Upgrader:
    _prompt = Title("> Choose: e"), Ok("xit, "), Title("a"), Ok("ll or "), Title("# "), Ok("? ")
    _pip_install = "-m", "pip", "install", "--upgrade", "--require-virtualenv"
    _pip_freeze = "-m", "pip", "freeze", "--quiet", "--exclude-editable"

    def __init__(self, python_env: PythonEnv) -> None:
        self._python_env = python_env

    def _install(self, *options: str) -> bool:
        pip = CommandMonitor(self._python_env.exe, *Upgrader._pip_install, *options)
        return pip.run(out=Title, err=Warn)

    def _install_all_packages(self, eager: bool, dry_run: bool) -> list[_Pckg]:
        """install all requirements, return what's been installed"""
        with tempfile.TemporaryDirectory() as temp_dir:
            report_file = Path(temp_dir) / "report.json"
            if self._install(
                *(("--dry-run",) if dry_run else ()),
                *("--report", str(report_file)),
                *("--upgrade-strategy", "eager" if eager else "only-if-needed"),
                *sum((("-r", req_file) for req_file in self._python_env.requirements), ()),
            ):
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
        """install one pckg constrained by all other pckgs' versions in the environment"""
        if freeze := self._python_env.run_python(*Upgrader._pip_freeze, "--exclude", pckg.name):
            with tempfile.TemporaryDirectory() as temp_dir:
                constraints = Path(temp_dir) / "current-env.txt"
                constraints.write_text(freeze)
                if self._install(pckg.url or f"{pckg.name}=={pckg.version}", "-r", str(constraints)):
                    return True
        return False

    def check(self, eager: bool) -> None:
        if not self._python_env.requirements:
            print(Warn("No requirements to check"))
            return
        print(
            *(Title("Check"), Ok("packages")),
            Low(f"{'eagerly' if eager else 'only needed'} for"),
            Ok(", ".join(self._python_env.requirements)),
        )
        to_install: list[_Pckg] = self._install_all_packages(eager, dry_run=True)
        while True:
            n = len(to_install)
            if n > 0:
                columns = _PckgsColumns(to_install)
                columns.add_no_column(lambda i: Title(f"{i + 1}."), Justify.RIGHT)
                columns.add_attr_column(lambda pckg: Ok(pckg.name), Justify.LEFT)
                columns.add_attr_column(lambda pckg: Warn(pckg.version), Justify.LEFT)
                print()
                pckg_plural = "s" if len(columns.rows) > 1 else ""
                print(Title("Install"), Ok(f"package{pckg_plural}:"))
                for row in columns.rows:
                    print(f" {row}")
            else:
                print(Title("Requirements uptodate"))
                break
            print()
            print(*Upgrader._prompt, end="", sep="")
            match _flushed_input(Title()).lower():
                case "e":
                    print(Title("Exit"))
                    break
                case "a":
                    print(Title("Install all"), Ok(f"package{pckg_plural}"))
                    installed = self._install_all_packages(eager, dry_run=False)
                    to_install = [pckg for pckg in to_install if pckg not in installed]
                case choice if choice.isdigit() and 0 <= (i := int(choice) - 1) < n:
                    pckg = to_install[i]
                    print(Title("Install"), Ok("package"), " ".join(columns.rows[i].split()))
                    if self._install_package(pckg):
                        to_install.remove(pckg)
