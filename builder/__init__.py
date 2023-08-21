import argparse
import inspect
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterator, NamedTuple, Optional, Protocol
from urllib.parse import quote

from PIL import Image

from .color import Stl
from .env import PythonEnv, get_bitness_str
from .upgrader import Upgrader


class Data(Protocol):
    @property
    def path(self) -> str:
        ...

    @property
    def src(self) -> Optional[tuple[str, int]]:
        ...


class Build(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str


class Nuitka(Protocol):
    args: list[str]


class Templates(Protocol):
    list: list[str]


class Environments(Protocol):
    requirements: list[str]
    x86: str
    x64: str


class Github(Protocol):
    owner: str
    repo: str


class Datas:
    def __init__(self, *datas: type[Data]) -> None:
        self._datas = tuple(data() for data in datas)

    def create_all(self) -> None:
        for data in self._datas:
            if data.src:
                src_path, size = data.src
                Image.open(src_path).resize((size, size)).save(data.path)
                print(Stl.title("Create"), Stl.high(data.__class__.__name__))

    @property
    def include_datas(self) -> tuple[str]:
        return tuple(f"--include-data-file={data.path}={data.path}" for data in self._datas)


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nobuild", "--readme", action="store_true", help="update readme and post only")
    parser.add_argument("--upgrade", action="store_true", help="upgrade the environment")
    parser.add_argument("--noexe", action="store_true", help="create only a zip (faster)")
    parser.add_argument("--mingw", action="store_true", help="build with mingw64")
    parser.add_argument("--both", action="store_true", help="build x64 and x86 version")
    parser.add_argument("--x86", action="store_true", help="build x86 version")
    parser.add_argument("--x64", action="store_true", help="build x64 version")
    return parser.parse_args()


def _get_dist_name(build: Build, is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def _get_dist_temp(build: Build, is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"


def _get_env(environments: Environments, is_64: bool) -> PythonEnv:
    return PythonEnv(environments.x64 if is_64 else environments.x86)


def _get_python_version(environments: Environments) -> str:
    python_version64 = _get_env(environments, is_64=True).version
    python_version32 = _get_env(environments, is_64=False).version
    if python_version64 != python_version32:
        print(Stl.warn("x64 and x86 Python versions differ !"))
        print(Stl.high(get_bitness_str(True)), Stl.title("Python is"), Stl.high(python_version64))
        print(Stl.high(get_bitness_str(False)), Stl.title("Python is"), Stl.high(python_version32))
    return python_version64


def _get_builds_bitness(args: argparse.Namespace) -> Iterator[bool]:
    if args.nobuild:
        return
        yield
    if args.x64 or args.x86 or args.both:
        if args.x64 or args.both:
            yield True
        if args.x86 or args.both:
            yield False
    else:
        yield PythonEnv().is_64bit


def _print_size(path: str) -> None:
    size = Path(path).stat().st_size / 1024
    print(Stl.title(f"{size:.0f}"), Stl.low("KB"))


class Builder:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, build: Build, environments: Environments, nuitka: Nuitka, datas: Datas) -> None:
        self.build = build
        self.environments = environments
        self.nuitka = nuitka
        args = _get_args()
        self.compiler = "--mingw64" if args.mingw else "--clang"
        self.builds_bitness = list(_get_builds_bitness(args))
        self.onefile = () if args.noexe else ("--onefile",)
        self.upgrade = args.upgrade
        datas.create_all()
        self.include_datas = datas.include_datas

    def _build_bitness(self, python_env: PythonEnv, is_64: bool) -> None:
        dist_name = _get_dist_name(self.build, is_64)
        dist_temp = _get_dist_temp(self.build, is_64)
        subprocess.run(
            (
                *(python_env.exe, "-m", "nuitka"),
                *self.nuitka.args,
                f"--onefile-tempdir-spec=%CACHE_DIR%/{self.build.name}",
                f"--windows-file-version={self.build.version}",
                f"--windows-company-name={self.build.company}",
                f"--windows-icon-from-ico={self.build.ico}",
                f"--output-filename={self.build.name}.exe",
                f"--output-dir={dist_temp}",
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                "--standalone",
                self.compiler,
                *self.onefile,
                *self.include_datas,
                self.build.main,
            ),
            check=True,
        )
        print(Stl.title("Create"), Stl.high(f"{dist_name}.zip"), end=" ")
        shutil.make_archive(dist_name, "zip", f"{dist_temp}/{Path(self.build.main).stem}.dist")
        _print_size(f"{dist_name}.zip")
        if self.onefile:
            print(Stl.title("Create"), Stl.high(f"{dist_name}.exe"), end=" ")
            shutil.copy(f"{dist_temp}/{self.build.name}.exe", f"{dist_name}.exe")
            _print_size(f"{dist_name}.exe")
        else:
            print(Stl.warn("Warning:"), Stl.high(f"{dist_name}.exe"), Stl.warn("not created !"))

    def build_all(self) -> None:
        for is_64 in self.builds_bitness:
            app_version = f"{self.build.name} v{self.build.version} {get_bitness_str(is_64)}"
            print(Stl.title("Build"), Stl.high(app_version))

            python_env = _get_env(self.environments, is_64)
            python_env.print()
            if python_env.check(is_64):
                if self.upgrade:
                    Upgrader(python_env).install_for(*self.environments.requirements)
                self._build_bitness(python_env, is_64)
            else:
                print(Stl.warn("Build Failed"))

            print()

        # missing versions
        for missing in set((True, False)) - set(self.builds_bitness):
            dist_name = _get_dist_name(self.build, missing)
            print(Stl.warn("Warning:"), Stl.high(dist_name), Stl.warn("not updated !"))


def _get_loc() -> int:
    get_py_files = "git ls-files -- '*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    loc = subprocess.run(
        ("powershell", f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum"),
        text=True,
        check=False,
        capture_output=True,
    )
    try:
        return int(loc.stdout)
    except ValueError:
        return 0


def _get_line_of_attr(obj: Any, name: str) -> int:
    lines, start = inspect.getsourcelines(obj)
    for i, line in enumerate(lines):
        if name in line.split("=")[0]:
            return start + i
    return 0


class Template(NamedTuple):
    src: str
    dst: str


class CreateTemplates:
    def __init__(self, build: Build, environments: Environments, templates: Templates, github: Github) -> None:
        self.build = build
        self.templates = templates
        dist_name64 = _get_dist_name(build, is_64=True)
        dist_name32 = _get_dist_name(build, is_64=False)
        python_version = _get_python_version(environments)
        self.template_format = dict(
            line_of_x86=_get_line_of_attr(environments, "x86"),
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
        template_txt = Path(src).read_text(encoding="utf-8")
        Path(dst).write_text(template_txt.format(**self.template_format), encoding="utf-8")

    def create_all(self) -> None:
        for template in self.templates.list:
            template = Template(*template)
            print(Stl.title("create"), Stl.high(template.dst))
            self._apply_template(template.src, template.dst)
