import json
import msvcrt
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from colorama import Fore, Style


class Stl:
    @staticmethod
    def _style(txt, style):
        reset = Style.RESET_ALL if txt else ""
        return f"{style}{txt or ''}{reset}"

    @staticmethod
    def title(txt=None):
        return Stl._style(txt, f"{Fore.GREEN}{Style.BRIGHT}")

    @staticmethod
    def high(txt=None):
        return Stl._style(txt, Fore.YELLOW)

    @staticmethod
    def low(txt=None):
        return Stl._style(txt, Fore.CYAN)

    @staticmethod
    def warn(txt=None):
        return Stl._style(txt, f"{Fore.RED}{Style.BRIGHT}")


def cols(sequence, key):
    txts = [key(obj) for obj in sequence]
    len_txt = len(max(txts, key=len))
    for txt in txts:
        yield f"{txt: <{len_txt + 1}}"


def line_clear():
    print("\x1b[2K", end="")


@dataclass
class Pckg:
    req: Path
    name: str
    version: str


class Upgrader:
    pip_install = sys.executable, "-m", "pip", "install", "-U"

    @staticmethod
    def _install(*options):
        with subprocess.Popen(
            [*Upgrader.pip_install, *options],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            text=True,
        ) as proc:
            if proc.stdout:
                for line in proc.stdout:
                    line_clear()
                    if "error" in line.lower():
                        print(Stl.warn(line.replace("\n", "")))
                    else:
                        print(line.replace("\n", "\r"), end="")
            line_clear()

    def _to_upgrade(self, req_file) -> list[Pckg]:
        print(Stl.title("Check upgrade for"), Stl.high(req_file))

        report_file = Path(f"{req_file}.json")
        self._install("--dry-run", "-r", req_file, "--report", report_file)

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
    def _show_upgrade(to_upgrade: list[Pckg]):
        if (n := len(to_upgrade)) > 0:
            print()
            print(Stl.title("Upgrade"))
            for i, (name, version, req) in enumerate(
                zip(
                    cols(to_upgrade, key=lambda pckg: Stl.high(pckg.name)),
                    cols(to_upgrade, key=lambda pckg: Stl.warn(pckg.version)),
                    cols(to_upgrade, key=lambda pckg: Stl.low(pckg.req)),
                )
            ):
                print(Stl.title(f" {i + 1}."), name, version, Stl.low("from"), req)
        return n

    def install_for(self, *req_files):
        # flush the input buffer
        while msvcrt.kbhit():
            msvcrt.getch()

        to_upgrade = sum((self._to_upgrade(req_file) for req_file in req_files), [])

        while True:
            n = self._show_upgrade(to_upgrade)

            if n == 0:
                print()
                print(Stl.title("Nothing to upgrade"))
                break

            key = input(
                f"{Stl.title('> q')}{Stl.low('uit')}"
                f" {Stl.low('or')} {Stl.title('#')}"
                f" {Stl.low('?')} {Stl.title()}"
            )
            if key == "q":
                print()
                break

            if key.isdigit() and 0 <= (i := int(key) - 1) < n:
                pckg = to_upgrade[i]
                print()
                print(
                    Stl.title("Install"),
                    Stl.high(pckg.name),
                    Stl.warn(pckg.version),
                )
                self._install(pckg.name)
                to_upgrade.remove(pckg)

        print(Stl.warn("Exit"))


if __name__ == "__main__":
    Upgrader().install_for("requirements.txt", "requirements.dev.txt")
