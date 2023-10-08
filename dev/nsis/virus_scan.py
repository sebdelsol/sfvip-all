import os
import subprocess
from pathlib import Path
from typing import Iterator, NamedTuple

from ..tools.color import Low, Ok, Title, Warn


class Scan(NamedTuple):
    threats: tuple[str, ...]
    is_clean: bool

    def __repr__(self) -> str:
        if self.is_clean:
            return Ok("clean")
        return f"{Warn('detected')} {Low(','.join(self.threats))}"


class VirusScan:
    defender = Path(os.environ["ProgramFiles"]) / "Windows Defender" / "MpCmdRun"
    args = "-Scan -ScanType 3 -DisableRemediation -Trace -Level 0x10".split()

    @staticmethod
    def get_threats(stdout: str) -> Iterator[str]:
        for line in stdout.splitlines():
            if line.startswith("Threat"):
                yield line.split()[-1]

    def run_on(self, file: Path) -> bool:
        print(Title("Scan virus"), Low(str(file)), end=" ")
        defender = VirusScan.defender, *VirusScan.args, "-File", file.absolute()
        process = subprocess.run(defender, timeout=30, capture_output=True, text=True, check=False)
        threats = tuple(self.get_threats(process.stdout))
        scan = Scan(
            threats=threats,
            is_clean=not (process.returncode or threats),
        )
        print(scan)
        return scan.is_clean
