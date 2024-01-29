from pathlib import Path
from typing import Iterator, Optional

import pyinstaller_versionfile

from ..utils.color import Title, Warn
from ..utils.monitor.command import CommandMonitor
from ..utils.protocols import CfgBuild
from .distribution import Distribution
from .files import IncludeFiles


class IncludeFilesPyInstaller(IncludeFiles):
    def get_file(self, path: Path) -> Iterator[str]:
        if path.is_dir():
            yield f"--add-data={path.resolve()}:{path}"
        elif path.is_file():
            yield f"--add-data={path.resolve()}:{path.parent}"


class Pyinstaller(Distribution):
    name = "PyInstaller"
    excluded_module_option = "exclude-module"

    def __init__(self, build: CfgBuild, do_run: bool) -> None:
        super().__init__(build, do_run)
        if do_run:
            self.args = (
                "--console" if build.enable_console else "--windowed",
                *IncludeFilesPyInstaller(build.files, build.ico).all,
                *self.get_excluded_modules(build.excluded),
                f"--icon={Path(build.ico).resolve()}",
                f"--name={build.name}",
                "-y",
                "--clean",
                "--onedir",
                "--contents-directory=.",  # so that ressources are available for nsis
                build.main,
            )
            self.version = dict(
                version=self.build.version,
                company_name=self.build.company,
                file_description=self.build.name,
                internal_name=self.build.name,
                product_name=self.build.name,
            )
        else:
            self.args = ()

    def create(self, python_exe: Path, build_dir: Path) -> Optional[Path]:
        versionfile = build_dir / "versionfile.txt"
        pyinstaller_versionfile.create_versionfile(output_file=versionfile, **self.version)
        ok = CommandMonitor(
            python_exe,
            "-O",  # optimization
            "-m",
            "PyInstaller",
            f"--version-file={versionfile.resolve()}",
            f"--specpath={build_dir}",
            f"--distpath={build_dir / '.dist'}",
            f"--workpath={build_dir / '.work'}",
            *self.args,
        ).run(out=Title, err=Warn, err_is_out=True)
        return build_dir / ".dist" / self.build.name if ok else None
