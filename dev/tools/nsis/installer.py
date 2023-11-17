from pathlib import Path
from typing import Iterator, NamedTuple, Sequence

import jinja2

from shared.version import Version

from ..utils.dist import Dist, to_ico
from ..utils.env import PythonEnv
from ..utils.protocols import CfgBuild, CfgLOC


def get_cmd(name: str, cmd: Sequence[str]) -> dict[str, str | int]:
    return {
        f"has_{name}_cmd": int(bool(cmd)),
        f"{name}_cmd": cmd[0] if cmd else "",
        f"{name}_cmd_arg": " ".join(cmd[1:]) if cmd else "",
    }


def get_all_languages(loc: CfgLOC, app_name: str) -> Iterator[dict[str, str]]:
    for lang in loc.all_languages:
        loc.set_language(lang)
        yield dict(
            retry=loc.Retry,
            upper=lang.upper(),
            name=lang.capitalize(),
            already_running=loc.AlreadyRunning % app_name,
        )


class NSISInstall(NamedTuple):
    installer: Path
    exe: Path


class NSISInstaller:
    template_path = Path(__file__).parent / "template.nsi"
    installer = "installer.nsi"
    version_length = 4
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, loc: CfgLOC) -> None:
        self.dist = Dist(build)
        with NSISInstaller.template_path.open("r", encoding=NSISInstaller.encoding) as f:
            env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
            self.template = env.from_string(
                f.read(),
                globals=dict(
                    name=build.name,
                    company=build.company,
                    dist=self.dist.dist_dir_name,
                    ico=str(Path(to_ico(build.ico))),
                    has_logs=int(bool(build.logs_dir)),
                    logs_dir=str(Path(build.logs_dir)),
                    finish_page=int(build.install_finish_page),
                    all_languages=tuple(get_all_languages(loc, build.name)),
                    version=str(Version(build.version).force_len(NSISInstaller.version_length)),
                    **get_cmd("install", build.install_cmd),
                    **get_cmd("uninstall", build.uninstall_cmd),
                ),
            )

    def create(self, python_env: PythonEnv) -> NSISInstall:
        exe = self.dist.installer_exe(python_env)
        exe.parent.mkdir(parents=True, exist_ok=True)
        installer = self.dist.build_dir(python_env) / NSISInstaller.installer
        with installer.open("w", encoding=NSISInstaller.encoding) as f:
            f.write(
                self.template.render(
                    dict(
                        is_64=int(python_env.is_64),
                        bitness=python_env.bitness,
                        installer=str(exe.resolve()),
                    )
                )
            )
        return NSISInstall(installer=installer, exe=exe)
