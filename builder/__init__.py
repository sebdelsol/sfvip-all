import inspect
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Self
from urllib.parse import quote

from PIL import Image
from tap import Tap

from .color import Stl
from .env import PythonEnv, get_bitness_str
from .protocols import Build, Data, Environments, Github, Nuitka, Templates
from .upgrader import Upgrader


class Datas:
    def __init__(self, *datas: type[Data]) -> None:
        self._datas = tuple(data() for data in datas)

    def create_all(self) -> Self:
        for data in self._datas:
            if data.src:
                src_path, size = data.src
                Image.open(src_path).resize((size, size)).save(data.path)
                print(Stl.title("Create"), Stl.high(data.__class__.__name__))
        return self

    @property
    def include_datas(self) -> tuple[str]:
        return tuple(f"--include-data-file={data.path}={data.path}" for data in self._datas)


class Args(Tap):
    readme: bool = False  # update readme and post only
    upgrade: bool = False  # upgrade the environment
    noexe: bool = False  # create only a zip (faster)
    mingw: bool = False  # build with mingw64
    both: bool = False  # build x64 and x86 versions
    x86: bool = False  # build x86 version
    x64: bool = False  # build x64 version


def _get_dist_name(build: Build, is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def _get_dist_temp(build: Build, is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"


def _get_python_env(environments: Environments, is_64: bool) -> PythonEnv:
    return PythonEnv(environments.x64 if is_64 else environments.x86)


def _get_version_of(environments: Environments, name: str, get_version: Callable[[PythonEnv], str]) -> str:
    versions = {is_64: get_version(_get_python_env(environments, is_64=is_64)) for is_64 in (True, False)}
    if versions[True] != versions[False]:
        print(Stl.high("x64"), Stl.warn("and"), Stl.high(f"x86 {name}"), Stl.warn("versions differ !"))
        for is_64 in (True, False):
            print(Stl.high(get_bitness_str(is_64)), Stl.title(f"{name} is"), Stl.high(versions[is_64]))
    return versions[True]


def _get_python_version(environments: Environments) -> str:
    return _get_version_of(environments, "Python", lambda environment: environment.python_version)


def _get_nuitka_version(environments: Environments) -> str:
    return _get_version_of(environments, "Nuitka", lambda environment: environment.package_version("nuitka"))


def _are_builds_64bits(args: Args) -> set[bool]:
    if args.readme:
        return set()
    if args.both or (args.x64 and args.x86):
        return {True, False}
    if args.x64:
        return {True}
    if args.x86:
        return {False}
    return {PythonEnv().is_64bit}


def _print_filename_size(path: str) -> None:
    size = Path(path).stat().st_size / 1024
    print(Stl.title(f"{size:.0f}"), Stl.low("KB"))


class Builder:
    def __init__(self, build: Build, environments: Environments, nuitka: Nuitka, datas: Datas) -> None:
        args = Args().parse_args()
        self.build = build
        self.environments = environments
        self.are_builds_64bits = _are_builds_64bits(args)
        self.onefile = not args.noexe
        self.upgrade = args.upgrade
        self.nuitka_args = (
            "--mingw64" if args.mingw else "--clang",
            *datas.create_all().include_datas,
            *nuitka.args,
        )
        if self.onefile:
            self.nuitka_args = *self.nuitka_args, "--onefile"

    def _build_bitness(self, python_env: PythonEnv, is_64: bool) -> None:
        dist_name = _get_dist_name(self.build, is_64)
        dist_temp = _get_dist_temp(self.build, is_64)
        subprocess.run(
            (
                *(python_env.exe, "-m", "nuitka"),
                f"--onefile-tempdir-spec=%CACHE_DIR%/{self.build.name}",
                f"--windows-file-version={self.build.version}",
                f"--windows-company-name={self.build.company}",
                f"--windows-icon-from-ico={self.build.ico}",
                f"--output-filename={self.build.name}.exe",
                f"--output-dir={dist_temp}",
                "--assume-yes-for-downloads",
                "--python-flag=-OO",
                "--standalone",
                *self.nuitka_args,
                self.build.main,
            ),
            check=True,
        )
        print(Stl.title("Create"), Stl.high(f"{dist_name}.zip"), end=" ")
        shutil.make_archive(dist_name, "zip", f"{dist_temp}/{Path(self.build.main).stem}.dist")
        _print_filename_size(f"{dist_name}.zip")
        if self.onefile:
            print(Stl.title("Create"), Stl.high(f"{dist_name}.exe"), end=" ")
            shutil.copy(f"{dist_temp}/{self.build.name}.exe", f"{dist_name}.exe")
            _print_filename_size(f"{dist_name}.exe")
        else:
            print(Stl.warn("Warning:"), Stl.high(f"{dist_name}.exe"), Stl.warn("not created !"))

    def build_all(self) -> None:
        for is_64 in self.are_builds_64bits:
            app_version = f"{self.build.name} v{self.build.version} {get_bitness_str(is_64)}"
            print(Stl.title("Build"), Stl.high(app_version))

            python_env = _get_python_env(self.environments, is_64)
            python_env.print()
            if python_env.check(is_64):
                if self.upgrade:
                    Upgrader(python_env).install_for(*self.environments.requirements, eager=False)
                self._build_bitness(python_env, is_64)
            else:
                print(Stl.warn("Build Failed"))

            print()

        # missing versions
        for missing in set((True, False)) - set(self.are_builds_64bits):
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


class Templater:
    _encoding = "utf-8"

    def __init__(self, build: Build, environments: Environments, templates: Templates, github: Github) -> None:
        self.build = build
        self.templates = templates
        dist_name64 = _get_dist_name(build, is_64=True)
        dist_name32 = _get_dist_name(build, is_64=False)
        python_version = _get_python_version(environments)
        nuitka_version = _get_nuitka_version(environments)
        self.template_format = dict(
            line_of_x86=_get_line_of_attr(environments, "x86"),
            py_version_compact=python_version.replace(".", ""),
            github_path=f"{github.owner}/{github.repo}",
            archive64_link=quote(f"{dist_name64}.zip"),
            archive32_link=quote(f"{dist_name32}.zip"),
            exe64_link=quote(f"{dist_name64}.exe"),
            exe32_link=quote(f"{dist_name32}.exe"),
            py_version=python_version,
            nuitka_version=nuitka_version,
            ico_link=quote(build.ico),
            version=build.version,
            name=build.name,
            loc=_get_loc(),
        )

    def _apply_template(self, src: Path, dst: Path) -> None:
        print(Stl.title("create"), Stl.high(dst.as_posix()))
        template = src.read_text(encoding=Templater._encoding).format(**self.template_format)
        dst.write_text(template, encoding=Templater._encoding)

    def create_all(self) -> None:
        for src, dst in self.templates.list:
            self._apply_template(Path(src), Path(dst))
