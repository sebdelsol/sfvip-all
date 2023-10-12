from pathlib import Path

from .publisher import Publisher
from .tools.color import Ok, Title, Warn
from .tools.env import get_bitness_str
from .tools.protocols import CfgBuild, CfgGithub, CfgTemplate

UNAVAILABLE = """This version is not longer available.
Please get the lastest version HERE:

https://github.com/{github_path}/tree/master/{readme_dir}#download
"""


def clean_old_build(build: CfgBuild, github: CfgGithub, readme: CfgTemplate):
    suffixes = ".zip", ".exe"
    print(Title("Clean Old"), Ok("builts"))
    unavailable = UNAVAILABLE.format(
        github_path=f"{github.owner}/{github.repo}",
        readme_dir=str(Path(readme.dst).parent),
    )
    publisheds = tuple(Publisher(build, github).get_local_versions())
    kept = False
    for file in Path(build.dir).rglob(f"{build.name}.*"):
        if file.suffix in suffixes:
            if "temp" in file.parts:
                continue
            if build.version in file.parts or any(
                published.version in file.parts and get_bitness_str(published.is_64) in file.parts
                for published in publisheds
            ):
                print(Title(". Keep"), Ok(str(file.as_posix())))
                kept = True
                continue
            file.write_text(unavailable)
    if not kept:
        print(Title(". Kept"), Warn("nothing"))
