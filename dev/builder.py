from typing import Sequence

from .nsis import NSIS
from .nuitka import Nuitka
from .publisher import Publisher
from .tools.color import Low, Ok, Title, Warn
from .tools.dist import get_bitness_str, get_dist_name
from .tools.env import EnvArgs, PythonEnv
from .tools.protocols import CfgBuild, CfgEnvironments, CfgGithub
from .upgrader import Upgrader


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
    with_nuitka = Low("with"), Ok("Nuitka")
    with_NSIS = Low("with"), Ok("NSIS")

    def __init__(
        self,
        build: CfgBuild,
        environments: CfgEnvironments,
        github: CfgGithub,
        all_languages: Sequence[str],
    ) -> None:
        self.build = build
        self.args = Args().parse_args()
        self.nsis = NSIS(build, all_languages, self.args.installer)
        self.publisher = Publisher(build, github)
        self.nuitka = Nuitka(build, self.args.mingw, self.args.build)
        self.python_envs = self.args.get_python_envs(environments)

    def build_in(self, python_env: PythonEnv) -> str:
        name = f"{self.build.name} v{self.build.version} {get_bitness_str(python_env.is_64)}"
        print(python_env)
        print(Title("Building"), Ok(name))
        if python_env.check():
            if self.args.upgrade:
                Upgrader(python_env).check(eager=True)
            if self.nuitka.run(python_env):
                if dist := self.nsis.run(python_env):
                    if self.args.publish:
                        self.publisher.publish(python_env.is_64)
                return dist
        print(Warn("Build failed"), Ok(name))
        return ""

    def build_all(self) -> bool:
        if self.args.build or self.args.installer:
            builts = [built for python_env in self.python_envs if (built := self.build_in(python_env))]
        else:
            builts = []
        # missing built versions
        for is_64 in True, False:
            build = f"{get_dist_name(self.build, is_64)}.exe"
            if build not in builts:
                print(Warn("Not built"), Ok(build))
        return self.args.installer
