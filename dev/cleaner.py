from pathlib import Path

from .publisher import Publisher
from .tools.color import Low, Ok, Title, Warn
from .tools.env import get_bitness_str
from .tools.protocols import CfgBuild, CfgGithub

UNAVAILABLE = """This version is not longer available.
Please get the lastest version HERE:

https://github.com/{github_path}#download
"""


def clean_old_build(build: CfgBuild, github: CfgGithub):
    suffixes = ".zip", ".exe"
    print(Title("Clean Old"), Low(" and ").join(Ok(f"{build.name}{suffix}") for suffix in suffixes))
    unavailable = UNAVAILABLE.format(github_path=f"{github.owner}/{github.repo}")
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
                print(Title(". Keep"), Ok(str(file)))
                kept = True
                continue
            file.write_text(unavailable)
    if not kept:
        print(Title(". Kept"), Warn("nothing"))
