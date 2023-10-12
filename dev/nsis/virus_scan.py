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
            return Ok("Clean")
        return f"{Warn('Detected:')} {Low(','.join(self.threats))}"


class VirusScan:
    defender = Path(os.environ["ProgramFiles"]) / "Windows Defender" / "MpCmdRun"
    scan_args = "-Scan -ScanType 3 -DisableRemediation -Trace -Level 0x10".split()
    update_args = "-SignatureUpdate -MMPC".split()

    def __init__(self, update: bool) -> None:
        if update:
            print(Title("Update"), Low("virus signatures definitions"))
            defender_update = VirusScan.defender, *VirusScan.update_args
            subprocess.run(defender_update, timeout=30, capture_output=True, text=True, check=True)

    @staticmethod
    def get_threats(stdout: str) -> Iterator[str]:
        for line in stdout.splitlines():
            if line.startswith("Threat"):
                yield line.split()[-1]

    def run_on(self, file: Path) -> bool:
        print(Title("Scan virus"), Ok(str(file.as_posix())), end=" ")
        defender = VirusScan.defender, *VirusScan.scan_args, "-File", file.absolute()
        process = subprocess.run(defender, timeout=30, capture_output=True, text=True, check=False)
        threats = tuple(self.get_threats(process.stdout))
        scan = Scan(
            threats=threats,
            is_clean=not (process.returncode or threats),
        )
        print(Low("-"), scan)
        return scan.is_clean
