from pathlib import Path

from ..env.envs import EnvArgs, PythonEnvs
from ..utils.color import Low, Ok, Title, Warn
from ..utils.dist import Dist
from ..utils.protocols import CfgBuild, CfgEnvironments
from .defender import Defender
from .file import ScanFile


class VirusScanner(Defender):
    def update(self) -> None:
        print(Title("Update"), Ok("virus signatures"), end=" ", flush=True)
        print(Low("•"), Ok("Ok") if self._update() else Warn("Failed"), end=" ")
        print(Low("• Engine"), Ok(self.engine), Low("• Signature"), Ok(self.signature))

    def scan(self, file: Path) -> bool:
        if file.exists():
            print(Title("Scan virus"), Ok(str(file.as_posix())), end=" ", flush=True)
            scan = self._scan(file)
            print(Low("•"), scan)
            ScanFile(file).set(self.engine, self.signature, scan.is_clean)
            return scan.is_clean
        return False

    def scan_all(self, build: CfgBuild, environments: CfgEnvironments) -> None:
        self.update()
        args = EnvArgs().parse_args()
        dist = Dist(build)
        for python_env in PythonEnvs(environments, args).asked:
            self.scan(dist.dist_dir(python_env))
            self.scan(dist.installer_exe(python_env))
