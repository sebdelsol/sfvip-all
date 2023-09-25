import json
import sys
from pathlib import Path
from urllib.parse import quote

from src.sfvip.app_updater import AppUpdate
from src.sfvip.exe_tools import compute_md5, is64_exe

from .tools.color import Ok, Title, Warn
from .tools.dist import get_dist_name, get_dist_name_from_version
from .tools.env import EnvArgs, get_bitness_str
from .tools.protocols import CfgBuild, CfgGithub


# comments are automatically turned into argparse help
class Args(EnvArgs):
    version: str = ""  # version published (current if none)
    info: bool = False  # info about what's been published


class Publisher:
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, github: CfgGithub) -> None:
        self.build = build
        self.github_path = f"{github.owner}/{github.repo}"

    def _update_path(self, is_64: bool) -> Path:
        return Path(self.build.dir) / self.build.update.format(bitness=get_bitness_str(is_64))

    def publish(self, is_64: bool) -> None:
        if self.build.update:
            exe_name = f"{get_dist_name(self.build, is_64=is_64)}.exe"
            exe_path = Path(exe_name)
            if exe_path.exists() and is_64 == is64_exe(exe_path):
                update_path = self._update_path(is_64)
                with update_path.open(mode="w", encoding=Publisher.encoding) as f:
                    update = AppUpdate(
                        url=f"https://github.com/{self.github_path}/raw/master/{quote(exe_name)}",
                        md5=compute_md5(exe_path),
                        version=self.build.version,
                    )
                    json.dump(update._asdict(), f, indent=2)
                print(Title("Publish update"), Ok(exe_name))
            else:
                print(Warn("Publish update failed"), Ok(exe_name))

    def publish_all(self) -> None:
        args = Args().parse_args()
        if not args.info:
            if args.version:
                self.build.version = args.version
            for is_64 in args.get_bitness():
                if is_64 is None:
                    is_64 = sys.maxsize == (2**63) - 1
                self.publish(is_64)
        self.show_published_version()

    def show_published_version(self) -> None:
        print(Title("Published update:"))
        published = False
        if self.build.update:
            for is_64 in True, False:
                update_path = self._update_path(is_64)
                if update_path.exists():
                    with update_path.open(mode="r", encoding=Publisher.encoding) as f:
                        if update := AppUpdate.from_json(json.load(f)):
                            exe = Path(f"{get_dist_name_from_version(self.build, is_64, update.version)}.exe")
                            if exe.exists() and compute_md5(exe) == update.md5:
                                print(Ok(f". {self.build.name} v{update.version} {get_bitness_str(is_64)}"))
                                published = True
        if not published:
            print(Warn(". None"))
