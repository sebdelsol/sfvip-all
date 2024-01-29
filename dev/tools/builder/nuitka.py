from pathlib import Path
from typing import Iterator, Optional

from ..utils.color import Title
from ..utils.monitor.pty import PtyMonitor
from ..utils.protocols import CfgBuild
from .distribution import Distribution
from .files import IncludeFiles


class IncludeFilesNuitka(IncludeFiles):
    def get_file(self, path: Path) -> Iterator[str]:
        if path.is_dir():
            yield f"--include-data-dir={path}={path}"
        elif path.is_file():
            yield f"--include-data-file={path}={path}"


class Nuitka(Distribution):
    name = "Nuitka"
    excluded_module_option = "nofollow-import-to"

    def __init__(self, build: CfgBuild, mingw: bool, do_run: bool) -> None:
        super().__init__(build, do_run)
        if do_run:
            self.args = (
                "--enable-console" if build.enable_console else "--disable-console",
                *IncludeFilesNuitka(build.files, build.ico).all,
                *self.get_excluded_modules(build.excluded),
                f"--windows-icon-from-ico={build.ico}",
                f"--output-filename={build.name}.exe",
                f"--product-version={build.version}",
                "--mingw64" if mingw else "--clang",
                f"--company-name={build.company}",
                f"--file-version={build.version}",
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                "--deployment",  # disable Nuitka safeguards, comment if some issues
                "--standalone",
                build.main,
            )
            if build.logs_dir:
                logs = f"--force-stderr-spec={{PROGRAM}}/../{build.logs_dir}/{build.name} - {{TIME}} - {{PID}}.log"
                self.args = logs, *self.args

    def create(self, python_exe: Path, build_dir: Path) -> Optional[Path]:
        ok = PtyMonitor(
            python_exe,
            "-m",
            "nuitka",
            f"--output-dir={build_dir}",
            *self.args,
        ).run(out=Title)
        return build_dir / self.dist.dist_dir_name if ok else None
