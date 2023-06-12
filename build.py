import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from PIL import Image

from build_config import Build, Github
from color import Stl
from src.sfvip.ui import get_bitness_str
from upgrade import Upgrader


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nobuild", "--readme", action="store_true", help="update readme and post only")
    parser.add_argument("--noexe", action="store_true", help="create only a zip (faster)")
    parser.add_argument("--clang", action="store_true", help="build with clang")
    parser.add_argument("--both", action="store_true", help="build x64 and x86 version")
    parser.add_argument("--x86", action="store_true", help="build x86 version")
    parser.add_argument("--x64", action="store_true", help="build x64 version")
    return parser.parse_args()


def create_logo() -> None:
    print(Stl.title("Create"), Stl.high("logo"))
    Image.open(Build.Logo.use).resize(Build.Logo.size).save(Build.Logo.path)


def get_dist_name(is_64: bool) -> str:
    return f"{Build.dir}/{Build.version}/{get_bitness_str(is_64)}/{Build.name}"


def get_dist_temp(is_64: bool) -> str:
    return f"{Build.dir}/temp/{get_bitness_str(is_64)}"


def get_builds_64bitness(args: argparse.Namespace) -> Iterator[bool]:
    if args.both:
        yield True
        yield False
    elif args.x64:
        yield True
    elif args.x86:
        yield False
    else:
        yield Build.Python.is_64bit


def build() -> None:
    args = get_args()
    if not args.nobuild:
        compiler = "--clang" if args.clang else "--mingw64"
        onefile = () if args.noexe else ("--onefile",)

        for is_64 in get_builds_64bitness(args):
            env = Path(Build.Environment.x64 if is_64 else Build.Environment.x86)
            python_executable = env / "scripts" / "python.exe"
            if not python_executable.exists():
                print(Stl.warn("No Python found:"), Stl.high(str(str(python_executable.resolve()))))
                continue
            Upgrader(python_executable).install_for("requirements.txt", "requirements.dev.txt")
            dist_name = get_dist_name(is_64)
            dist_temp = get_dist_temp(is_64)
            print()
            print(
                Stl.title("Build "),
                Stl.high(f"{Build.name} v{Build.version} {get_bitness_str(is_64)}"),
                Stl.title(" in environment "),
                Stl.low(str(env.resolve())),
                Stl.low("\\"),
                Stl.high(str(env.name)),
                sep="",
            )
            subprocess.run(
                [
                    *(python_executable, "-m", "nuitka"),  # run nuitka
                    f"--force-stderr-spec=%PROGRAM%/../{Build.name} - %TIME%.log",
                    f"--include-data-file={Build.Logo.path}={Build.Logo.path}",
                    f"--include-data-file={Build.splash}={Build.splash}",
                    f"--onefile-tempdir-spec=%CACHE_DIR%/{Build.name}",
                    f"--windows-file-version={Build.version}",
                    f"--windows-company-name={Build.company}",
                    f"--windows-icon-from-ico={Build.ico}",
                    f"--output-filename={Build.name}.exe",
                    f"--output-dir={dist_temp}",
                    "--assume-yes-for-downloads",
                    # needed for tkinter
                    "--enable-plugin=tk-inter",
                    "--python-flag=-OO",
                    "--disable-console",
                    "--standalone",
                    compiler,
                    *onefile,
                    Build.main,
                ],
                check=True,
            )
            print(Stl.title("Create"), Stl.high(f"{dist_name}.zip"))
            shutil.make_archive(dist_name, "zip", f"{dist_temp}/{os.path.splitext(Build.main)[0]}.dist")
            if not args.noexe:
                print(Stl.title("Create"), Stl.high(f"{dist_name}.exe"))
                shutil.copy(f"{dist_temp}/{Build.name}.exe", f"{dist_name}.exe")

        for missing in set((True, False)) - set(get_builds_64bitness(args)):
            print(Stl.warn("Warning:"), Stl.high(f"{get_dist_name(missing)}"), Stl.warn("NOT UPDATED !"))


def get_loc() -> int:
    get_py_files = "git ls-files -- '*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    loc = subprocess.run(
        [
            "powershell",
            f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum",
        ],
        text=True,
        check=False,
        capture_output=True,
    )
    return int(loc.stdout)


def template_to_file(src: str, dst: str | Path, template_format: dict[str, str | int]) -> None:
    template = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(template.format(**template_format), encoding="utf-8")


def create_readme() -> None:
    dist_name64 = get_dist_name(is_64=True)
    dist_name32 = get_dist_name(is_64=False)
    template = dict(
        py_version_compact=Build.Python.version.replace(".", ""),
        github_path=f"{Github.owner}/{Github.repo}",
        archive64_link=quote(f"{dist_name64}.zip"),
        archive32_link=quote(f"{dist_name32}.zip"),
        exe64_link=quote(f"{dist_name64}.exe"),
        exe32_link=quote(f"{dist_name32}.exe"),
        py_version=Build.Python.version,
        ico_link=quote(Build.ico),
        version=Build.version,
        name=Build.name,
        loc=get_loc(),
    )
    print(Stl.title("create"), Stl.high("readme & forum post"))
    template_to_file("ressources/README_template.md", "README.md", template)
    template_to_file("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt", template)


if __name__ == "__main__":
    create_logo()
    build()
    create_readme()
