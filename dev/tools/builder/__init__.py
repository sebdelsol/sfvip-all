from pathlib import Path
from typing import Optional

from ..env.envs import EnvArgs, PythonEnv, PythonEnvs
from ..env.upgrader import Upgrader
from ..nsis import NSIS
from ..publisher import Publisher
from ..scanner import VirusScanner
from ..utils.color import Ok, Title, Warn
from ..utils.dist import Dist
from ..utils.protocols import CfgBuild, CfgEnvironments, CfgLOC
from .nuitka import Nuitka
from .pyinstaller import Pyinstaller


# comments are turned into argparse help
class Args(EnvArgs):
    readme: bool = False  # create only the readme
    nobuild: bool = False  # run only nsis, you should have built before
    noinstaller: bool = False  # run only nuitka, do not produce an installer exe
    mingw: bool = False  # build with mingw64
    upgrade: bool = False  # upgrade the environment
    publish: bool = False  # publish it
    pyinstaller: bool = False  # use pyinstaller instead

    def process_args(self) -> None:
        super().process_args()
        if self.readme:
            self.nobuild, self.noinstaller = True, True

    @property
    def build(self) -> bool:
        return not self.nobuild

    @property
    def installer(self) -> bool:
        return not self.noinstaller


class Builder:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments, loc: CfgLOC, publisher: Publisher) -> None:
        self.build = build
        self.dist = Dist(build)
        self.publisher = publisher
        self.args = Args().parse_args()
        self.builder = (
            Pyinstaller(build, self.args.build)
            if self.args.pyinstaller
            else Nuitka(build, self.args.mingw, self.args.build)
        )
        self.nsis = NSIS(build, loc, self.args.installer, self.args.upgrade)
        self.python_envs = PythonEnvs(environments, self.args)

    def build_in(self, python_env: PythonEnv) -> Optional[Path]:
        name = f"{self.build.name} {self.build.version} {python_env.bitness}"
        print(python_env)
        print(Title("Building"), Ok(name))
        if python_env.check():
            if self.args.upgrade:
                Upgrader(python_env).upgrade(eager=True)
            if self.builder.run(python_env):
                if built := self.nsis.run(python_env):
                    if self.args.publish:
                        self.publisher.publish(python_env, self.build.version)
                return built
        print(Warn("Build failed"), Ok(name))
        return None

    def build_all(self) -> bool:
        builts: list[Path] = []
        if self.args.build or self.args.installer:
            VirusScanner().update()
            print()
            for python_env in self.python_envs.asked:
                if built := self.build_in(python_env):
                    builts.append(built)
                print()
            # show what's not built
            not_builts: list[Path] = []
            for python_env in self.python_envs.all:
                if (build := self.dist.installer_exe(python_env)) not in builts:
                    not_builts.append(build)
            if not_builts:
                print(Title("Not built"))
                for build in not_builts:
                    print(Warn(f". {build}"))
        # has some exe been created ?
        return bool(builts and self.args.installer)
