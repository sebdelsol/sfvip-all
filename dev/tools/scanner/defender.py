import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Iterator, NamedTuple, Self, Sequence

from ..utils.color import Low, Ok, Warn


class DefenderScan(NamedTuple):
    threats: Sequence[str]
    is_clean: bool
    has_failed: bool

    def __repr__(self) -> str:
        if self.has_failed:
            return Warn("Failed")
        if self.is_clean:
            return Ok("Clean")
        return f"{Warn('Detected:')} {Low(','.join(self.threats))}"

    @staticmethod
    def get_threats(stdout: str) -> Iterator[str]:
        for line in stdout.splitlines():
            if line.startswith("Threat"):
                yield line.split()[-1]

    @classmethod
    def from_process(cls, process: subprocess.CompletedProcess[str]) -> Self:
        threats = tuple(cls.get_threats(process.stdout))
        return cls(
            threats=threats,
            is_clean=not (process.returncode or threats),
            has_failed=bool(process.returncode),
        )


class DefenderVersion(Enum):
    SIGNATURE = "AntivirusSignatureVersion"
    ENGINE = "AMEngineVersion"

    def __str__(self) -> str:
        get_version = f"(Get-MpComputerStatus).{self.value}"
        process = subprocess.run(("PowerShell", get_version), capture_output=True, check=False, text=True)
        return process.stdout.replace("\n", "")


class Defender:
    exe = Path(os.environ["ProgramFiles"]) / "Windows Defender" / "MpCmdRun"
    scan_args = "-Scan -ScanType 3 -DisableRemediation -Trace -Level 0x10".split()
    update_args = "-SignatureUpdate -MMPC".split()
    timeout = 20

    @classmethod
    def _run(cls, *args: str | Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run((cls.exe, *args), timeout=cls.timeout, capture_output=True, check=False, text=True)

    @classmethod
    def _update(cls) -> bool:
        return cls._run(*cls.update_args).returncode == 0

    @classmethod
    def _scan(cls, file: Path) -> DefenderScan:
        process = cls._run(*cls.scan_args, "-File", file.resolve())
        return DefenderScan.from_process(process)

    @property
    def engine(self) -> str:
        return str(DefenderVersion.ENGINE)

    @property
    def signature(self) -> str:
        return str(DefenderVersion.SIGNATURE)
