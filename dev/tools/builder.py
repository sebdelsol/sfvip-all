from pathlib import Path
from typing import Optional

from .nsis import NSIS
from .nuitka import Nuitka
from .publisher import Publisher
from .scanner import VirusScan
from .upgrader import Upgrader
from .utils.color import Ok, Title, Warn
from .utils.dist import Dist
from .utils.env import EnvArgs, PythonEnv, PythonEnvs
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub, CfgLOC


# comments are turned into argparse help
class Args(EnvArgs):
    readme: bool = False  # create only the readme
    nobuild: bool = False  # run only nsis, you should have built before
    noinstaller: bool = False  # run only nuitka, do not produce an installer exe
    mingw: bool = False  # build with mingw64
    upgrade: bool = False  # upgrade the environment
    publish: bool = False  # publish it

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
    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub, loc: CfgLOC) -> None:
        self.build = build
        self.args = Args().parse_args()
        self.dist = Dist(build)
        self.nuitka = Nuitka(build, self.args.mingw, self.args.build)
        self.nsis = NSIS(build, loc, self.args.installer)
        self.publisher = Publisher(build, environments, github)
        self.python_envs = PythonEnvs(environments, self.args)

    def build_in(self, python_env: PythonEnv) -> Optional[Path]:
        name = f"{self.build.name} v{self.build.version} {python_env.bitness_str}"
        print(python_env)
        print(Title("Building"), Ok(name))
        if python_env.check():
            if self.args.upgrade:
                Upgrader(python_env).check(eager=True)
            if self.nuitka.run(python_env):
                if built := self.nsis.run(python_env):
                    if self.args.publish:
                        self.publisher.publish(python_env)
                return built
        print(Warn("Build failed"), Ok(name))
        return None

    def build_all(self) -> bool:
        builts = []
        if self.args.build or self.args.installer:
            VirusScan.update()
            print()
            for python_env in self.python_envs.asked:
                if built := self.build_in(python_env):
                    builts.append(built)
                    print()

        not_builts = []
        for python_env in self.python_envs.all:
            if (build := self.dist.installer_exe(python_env)) not in builts:
                not_builts.append(build)
        if not_builts:
            print(Title("Not built"))
            for build in not_builts:
                print(Warn(f". {build}"))
        # has some exe been created ?
        return bool(builts and self.args.installer)
