import argparse
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from build_config import Build, Github

from .color import Stl
from .env import PythonEnv, get_bitness_str
from .upgrader import Upgrader


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nobuild", "--readme", action="store_true", help="update readme and post only")
    parser.add_argument("--upgrade", action="store_true", help="upgrade the environment")
    parser.add_argument("--noexe", action="store_true", help="create only a zip (faster)")
    parser.add_argument("--mingw", action="store_true", help="build with mingw64")
    parser.add_argument("--both", action="store_true", help="build x64 and x86 version")
    parser.add_argument("--x86", action="store_true", help="build x86 version")
    parser.add_argument("--x64", action="store_true", help="build x64 version")
    return parser.parse_args()


def _get_dist_name(build: type[Build], is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def _get_dist_temp(build: type[Build], is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"


def _get_env(build: type[Build], is_64: bool) -> PythonEnv:
    return PythonEnv(build.Environment.x64 if is_64 else build.Environment.x86)


class Builder:
    def __init__(self, args: argparse.Namespace, build: type[Build]) -> None:
        self.build = build
        self.compiler = "--mingw64" if args.mingw else "--clang"
        self.onefile = () if args.noexe else ("--onefile",)
        self.noexe = args.noexe
        self.upgrade = args.upgrade
        if args.nobuild:
            self.builds_bitness = ()
        elif args.both:
            self.builds_bitness = True, False
        elif args.x64:
            self.builds_bitness = (True,)
        elif args.x86:
            self.builds_bitness = (False,)
        else:
            self.builds_bitness = (PythonEnv().is_64bit,)

    def _build_bitness(self, python_env: PythonEnv, is_64: bool) -> None:
        dist_name = _get_dist_name(self.build, is_64)
        dist_temp = _get_dist_temp(self.build, is_64)
        logo = self.build.Logo
        subprocess.run(
            [
                *(python_env.exe, "-m", "nuitka"),  # run nuitka
                f"--force-stderr-spec=%PROGRAM%/../{self.build.name} - %TIME%.log",
                f"--include-data-file={logo.path}={logo.path}",
                f"--include-data-file={self.build.splash}={self.build.splash}",
                f"--onefile-tempdir-spec=%CACHE_DIR%/{self.build.name}",
                f"--windows-file-version={self.build.version}",
                f"--windows-company-name={self.build.company}",
                f"--windows-icon-from-ico={self.build.ico}",
                f"--output-filename={self.build.name}.exe",
                f"--output-dir={dist_temp}",
                "--assume-yes-for-downloads",
                # needed for tkinter
                "--enable-plugin=tk-inter",
                "--python-flag=-OO",
                "--disable-console",
                "--standalone",
                self.compiler,
                *self.onefile,
                self.build.main,
            ],
            check=True,
        )
        print(Stl.title("Create"), Stl.high(f"{dist_name}.zip"))
        shutil.make_archive(dist_name, "zip", f"{dist_temp}/{os.path.splitext(self.build.main)[0]}.dist")
        if not self.noexe:
            print(Stl.title("Create"), Stl.high(f"{dist_name}.exe"))
            shutil.copy(f"{dist_temp}/{self.build.name}.exe", f"{dist_name}.exe")

    def build_all(self) -> None:
        for is_64 in self.builds_bitness:
            app_version = f"{self.build.name} v{self.build.version} {get_bitness_str(is_64)}"
            print(Stl.title("Build"), Stl.high(app_version))

            python_env = _get_env(self.build, is_64)
            python_env.print()
            if python_env.check(is_64):
                if self.upgrade:
                    Upgrader(python_env).install_for(*self.build.requirements)
                self._build_bitness(python_env, is_64)
            else:
                print(Stl.warn("Build Failed"))

            print()

        # missing versions
        for missing in set((True, False)) - set(self.builds_bitness):
            dist_name = _get_dist_name(self.build, missing)
            print(Stl.warn("Warning:"), Stl.high(dist_name), Stl.warn("Not updated !"))


def _get_loc() -> int:
    get_py_files = "git ls-files -- '*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    loc = subprocess.run(
        ["powershell", f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum"],
        text=True,
        check=False,
        capture_output=True,
    )
    try:
        return int(loc.stdout)
    except ValueError:
        return 0


class Template:
    def __init__(self, build: type[Build], github: type[Github]) -> None:
        dist_name64 = _get_dist_name(build, is_64=True)
        dist_name32 = _get_dist_name(build, is_64=False)

        python_version = _get_env(build, is_64=True).version
        if python_version != _get_env(build, is_64=False).version:
            print(Stl.warn("x64 and x86 Python versions differ !"))
            print(Stl.low("Use x64 Python version:"), Stl.high(python_version))

        self.template_format = dict(
            py_version_compact=python_version.replace(".", ""),
            github_path=f"{github.owner}/{github.repo}",
            archive64_link=quote(f"{dist_name64}.zip"),
            archive32_link=quote(f"{dist_name32}.zip"),
            exe64_link=quote(f"{dist_name64}.exe"),
            exe32_link=quote(f"{dist_name32}.exe"),
            py_version=python_version,
            ico_link=quote(build.ico),
            version=build.version,
            name=build.name,
            loc=_get_loc(),
        )

    def _apply_template(self, src: str, dst: str | Path) -> None:
        template = Path(src).read_text(encoding="utf-8")
        Path(dst).write_text(template.format(**self.template_format), encoding="utf-8")

    def create_readme(self) -> None:
        print(Stl.title("create"), Stl.high("readme"))
        self._apply_template("ressources/README_template.md", "README.md")

    def create_post(self) -> None:
        print(Stl.title("create"), Stl.high("post"))
        self._apply_template("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt")


def create_logo(logo: type[Build.Logo]) -> None:
    print(Stl.title("Create"), Stl.high("logo"))
    Image.open(logo.use).resize(logo.size).save(logo.path)
