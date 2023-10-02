import shutil
from pathlib import Path
from typing import Iterator, Literal, Sequence

from PIL import Image

from .publisher import Publisher
from .tools.color import Low, Ok, Title, Warn
from .tools.command import CommandMonitor
from .tools.dist import get_bitness_str, get_dist_name, get_dist_temp
from .tools.env import EnvArgs, PythonEnv
from .tools.protocols import (
    CfgBuild,
    CfgEnvironments,
    CfgFile,
    CfgFileResize,
    CfgGithub,
)
from .upgrader import Upgrader


# comments are automatically turned into argparse help
class Args(EnvArgs):
    nobuild: bool = False  # update readme and post only
    readme: bool = False  # update readme and post only
    upgrade: bool = False  # upgrade the environment
    noexe: bool = False  # create only a zip (faster)
    nozip: bool = False  # create only a exe
    mingw: bool = False  # build with mingw64
    publish: bool = False  # publish it

    def process_args(self) -> None:
        super().process_args()
        self.nobuild |= self.readme


class IncludeFiles:
    def __init__(self, files: Sequence[CfgFile | CfgFileResize]) -> None:
        self._files = files

    def _create_all(self) -> None:
        if self._files:
            for file in self._files:
                if isinstance(file, CfgFileResize):
                    Image.open(file.src).resize(file.resize).save(file.path)
                print(Title("Include"), Ok(file.path))

    @property
    def all(self) -> Iterator[str]:
        self._create_all()
        return (f"--include-data-file={file.path}={file.path}" for file in self._files)


class Builder:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        args = Args().parse_args()
        self.publisher = Publisher(build, github) if args.publish else None
        self.python_envs = args.get_python_envs(environments)
        self.build_exe = not (args.noexe or args.nobuild)
        self.build_zip = not (args.nozip or args.nobuild)
        self.upgrade = args.upgrade
        self.build = build
        if self.build_exe or self.build_zip:
            self.nuitka_args = (
                *(("--onefile",) if self.build_exe else ()),
                f"--windows-file-version={build.version}",
                f"--windows-company-name={build.company}",
                "--mingw64" if args.mingw else "--clang",
                f"--windows-icon-from-ico={build.ico}",
                f"--output-filename={build.name}.exe",
                *IncludeFiles(build.files).all,
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                *build.nuitka_args,
                "--standalone",
                build.main,
            )
        else:
            self.nuitka_args = ()

    def _build(self, python_env: PythonEnv) -> Iterator[str]:
        def _built(ext: Literal["exe", "zip"]) -> str:
            size = Path(f"{dist_name}.{ext}").stat().st_size / 1024
            print(Title("Built"), Ok(f"{dist_name}.{ext}"), Low(f"{size:.0f} KB"))
            return f"{dist_name}.{ext}"

        name = f"{self.build.name} v{self.build.version} {get_bitness_str(python_env.is_64)}"
        print(python_env)
        print(Title("Building"), Ok(name))
        if python_env.check():
            if self.upgrade:
                Upgrader(python_env).check(eager=True)
            dist_name = get_dist_name(self.build, python_env.is_64)
            dist_temp = get_dist_temp(self.build, python_env.is_64)
            nuitka = CommandMonitor(
                python_env.exe,
                "-m",
                "nuitka",
                f"--output-dir={dist_temp}",
                f"--onefile-tempdir-spec=%CACHE_DIR%/{self.build.name} {get_bitness_str(python_env.is_64)}",
                *(arg.format(python_env=python_env.path_str) for arg in self.nuitka_args),
            )
            if nuitka.run(out=Title):
                Path(dist_name).parent.mkdir(parents=True, exist_ok=True)
                if self.build_zip:
                    shutil.make_archive(dist_name, "zip", f"{dist_temp}/{Path(self.build.main).stem}.dist")
                    yield _built("zip")
                if self.build_exe:
                    shutil.copy(f"{dist_temp}/{self.build.name}.exe", f"{dist_name}.exe")
                    yield _built("exe")
                    if self.publisher:
                        self.publisher.publish(python_env.is_64)

                return
        print(Warn("Build failed"), Ok(name))

    def build_all(self) -> bool:
        builts = []
        if self.build_exe or self.build_zip:
            for python_env in self.python_envs:
                for built in self._build(python_env):
                    builts.append(built)
        # missing built versions
        for is_64 in True, False:
            for ext in "exe", "zip":
                build = f"{get_dist_name(self.build, is_64)}.{ext}"
                if build not in builts:
                    print(Warn("Not built"), Ok(build))
        return self.build_exe
