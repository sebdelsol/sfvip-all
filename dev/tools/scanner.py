import os
import subprocess
from pathlib import Path
from typing import Iterator, NamedTuple, Self, Sequence

from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist
from .utils.env import EnvArgs, PythonEnvs
from .utils.protocols import CfgBuild, CfgEnvironments


class Scan(NamedTuple):
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
    def from_process(cls, process: subprocess.CompletedProcess) -> Self:
        threats = tuple(cls.get_threats(process.stdout))
        return Scan(
            threats=threats,
            is_clean=not (process.returncode or threats),
            has_failed=bool(process.returncode),
        )


class VirusScan:
    defender = Path(os.environ["ProgramFiles"]) / "Windows Defender" / "MpCmdRun"
    scan_args = "-Scan -ScanType 3 -DisableRemediation -Trace -Level 0x10".split()
    update_args = "-SignatureUpdate -MMPC".split()
    timeout = 20

    @classmethod
    def run(cls, *args: str | Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            (cls.defender, *args), timeout=cls.timeout, capture_output=True, check=False, text=True
        )

    @classmethod
    def update(cls) -> None:
        print(Title("Update"), Ok("virus signatures"), end=" ")
        process = cls.run(*cls.update_args)
        print(Low("-"), Warn("Failed") if process.returncode else Ok("Done"))

    @classmethod
    def scan(cls, file: Path) -> bool:
        if file.exists():
            print(Title("Scan virus"), Ok(str(file.as_posix())), end=" ")
            process = cls.run(*cls.scan_args, "-File", file.resolve())
            scan = Scan.from_process(process)
            print(Low("-"), scan)
            return scan.is_clean
        return False

    @classmethod
    def scan_all(cls, build: CfgBuild, environments: CfgEnvironments) -> None:
        cls.update()
        args = EnvArgs().parse_args()
        dist = Dist(build)
        for python_env in PythonEnvs(environments, args).asked:
            cls.scan(dist.dist_dir(python_env))
            cls.scan(dist.installer_exe(python_env))
