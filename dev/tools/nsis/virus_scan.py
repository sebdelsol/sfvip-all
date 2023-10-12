import os
import subprocess
from pathlib import Path
from typing import Iterator, NamedTuple, Sequence

from ..utils.color import Low, Ok, Title, Warn


class Scan(NamedTuple):
    threats: Sequence[str]
    is_clean: bool

    def __repr__(self) -> str:
        if self.is_clean:
            return Ok("Clean")
        return f"{Warn('Detected:')} {Low(','.join(self.threats))}"


class VirusScan:
    defender = Path(os.environ["ProgramFiles"]) / "Windows Defender" / "MpCmdRun"
    scan_args = "-Scan -ScanType 3 -DisableRemediation -Trace -Level 0x10".split()
    update_args = "-SignatureUpdate -MMPC".split()
    timeout = 20

    def __init__(self, update: bool) -> None:
        if update:
            print(Title("Update"), Low("virus signatures definitions"))
            self.run(*VirusScan.update_args, check=True)

    @staticmethod
    def run(*args: str | Path, check: bool) -> subprocess.CompletedProcess:
        return subprocess.run(
            (VirusScan.defender, *args), timeout=VirusScan.timeout, capture_output=True, check=check, text=True
        )

    @staticmethod
    def get_threats(stdout: str) -> Iterator[str]:
        for line in stdout.splitlines():
            if line.startswith("Threat"):
                yield line.split()[-1]

    def run_on(self, file: Path) -> bool:
        print(Title("Scan virus"), Ok(str(file.as_posix())), end=" ")
        process = self.run(*VirusScan.scan_args, "-File", file.resolve(), check=False)
        threats = tuple(self.get_threats(process.stdout))
        scan = Scan(
            threats=threats,
            is_clean=not (process.returncode or threats),
        )
        print(Low("-"), scan)
        return scan.is_clean
