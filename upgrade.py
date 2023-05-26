import json
import msvcrt
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, Protocol

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()


class Color:
    class ToStyle(Protocol):  # to handle hint for the callable default paramater
        def __call__(self, txt: str = "") -> str:
            ...

    @staticmethod
    def _use_style(style: str) -> ToStyle:
        return lambda txt="": f"{style}{txt}{Style.RESET_ALL}" if txt else style

    _use_style = _use_style.__func__

    title = _use_style(Fore.GREEN + Style.BRIGHT)
    warn = _use_style(Fore.RED + Style.BRIGHT)
    high = _use_style(Fore.YELLOW)
    low = _use_style(Fore.CYAN)


class Pckg(NamedTuple):
    req: str
    name: str
    version: str


def format_columns(sequence: list[Pckg], key_to_str: Callable[[Pckg], str]) -> Iterator[str]:
    txts = [key_to_str(pckg) for pckg in sequence]
    len_txt = len(max(txts, key=len))
    for txt in txts:
        yield f"{txt: <{len_txt + 1}}"


def line_clear() -> None:
    print("\x1b[2K", end="")


class Upgrader:
    pip_install = sys.executable, "-m", "pip", "install", "-U", "--require-virtualenv"

    @staticmethod
    def _install(*options: str) -> None:
        with subprocess.Popen(
            [*Upgrader.pip_install, *options],
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
                        print(Color.warn(line.replace("\n", "")))
                    else:
                        line = line.replace("\n", "")[:width]
                        print(f"{line}\r", end="")
            line_clear()

    def _to_upgrade(self, req_file: str) -> list[Pckg]:
        print(Color.title("Check upgrade for"), Color.high(req_file))

        report_file = f"{req_file}.json"
        self._install("--dry-run", "-r", req_file, "--report", report_file)

        report_file = Path(report_file)
        if report_file.exists():
            with open(report_file, mode="r", encoding="utf8") as f:
                report = json.load(f)
            report_file.unlink()

            return [
                Pckg(req=req_file, name=data["name"], version=data["version"])
                for pckg in report["install"]
                if (data := pckg.get("metadata"))
            ]
        return []

    @staticmethod
    def _show_upgrade(to_upgrade: list[Pckg]) -> int:
        if (n := len(to_upgrade)) > 0:
            print()
            print(Color.title("Upgrade"))
            for i, (name, version, req) in enumerate(
                zip(
                    format_columns(to_upgrade, key_to_str=lambda pckg: Color.high(pckg.name)),
                    format_columns(to_upgrade, key_to_str=lambda pckg: Color.warn(pckg.version)),
                    format_columns(to_upgrade, key_to_str=lambda pckg: Color.low(pckg.req)),
                )
            ):
                print(Color.title(f" {i + 1}."), name, version, Color.low("from"), req)
        return n

    def install_for(self, *req_files: str) -> None:
        # flush the input buffer
        while msvcrt.kbhit():
            msvcrt.getch()

        to_upgrade = sum((self._to_upgrade(req_file) for req_file in req_files), [])

        while True:
            n = self._show_upgrade(to_upgrade)

            if n == 0:
                print()
                print(Color.title("Nothing to upgrade"))
                break

            key = input(
                f"{Color.title('> q')}{Color.low('uit')} {Color.low('or')} "
                f"{Color.title('#')} {Color.low('?')} {Color.title()}"
            )
            if key == "q":
                print()
                break

            if key.isdigit() and 0 <= (i := int(key) - 1) < n:
                pckg = to_upgrade[i]
                print()
                print(
                    Color.title("Install"),
                    Color.high(pckg.name),
                    Color.warn(pckg.version),
                )
                self._install(pckg.name)
                to_upgrade.remove(pckg)

        print(Color.warn("Exit"))


if __name__ == "__main__":
    Upgrader().install_for("requirements.txt", "requirements.dev.txt")