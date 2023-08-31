import ast
import inspect
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import quote

from PIL import Image

from .color import Stl
from .env import EnvArgs, PythonEnv, get_bitness_str
from .protocols import CfgBuild, CfgEnvironments, CfgFile, CfgFileResize, CfgTemplates
from .upgrader import Upgrader


# comments are automatically turned into argparse help
class Args(EnvArgs):
    readme: bool = False  # update readme and post only
    upgrade: bool = False  # upgrade the environment
    noexe: bool = False  # create only a zip (faster)
    mingw: bool = False  # build with mingw64


class IncludeFiles:
    def __init__(self, files: Sequence[CfgFile | CfgFileResize]) -> None:
        self._files = files

    def _create_all(self) -> None:
        for file in self._files:
            if isinstance(file, CfgFileResize):
                Image.open(file.src).resize(file.resize).save(file.path)
                print(Stl.title("Create"), Stl.high(file.path))

    @property
    def all(self) -> list[str]:
        self._create_all()
        return [f"--include-data-file={file.path}={file.path}" for file in self._files]


def _get_dist_name(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def _get_dist_temp(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"


def _get_version_of(environments: CfgEnvironments, name: str, get_version: Callable[[PythonEnv], str]) -> str:
    versions = {is_64: get_version(PythonEnv(environments, is_64)) for is_64 in (True, False)}
    if versions[True] != versions[False]:
        print(Stl.high("x64"), Stl.warn("and"), Stl.high("x86"), Stl.warn(f"{name} versions differ !"))
        for is_64 in (True, False):
            print(Stl.high(get_bitness_str(is_64)), Stl.title(f"{name} is"), Stl.high(versions[is_64]))
    return versions[True]


def _get_python_version(environments: CfgEnvironments) -> str:
    return _get_version_of(environments, "Python", lambda environment: environment.python_version)


def _get_nuitka_version(environments: CfgEnvironments) -> str:
    return _get_version_of(environments, "Nuitka", lambda environment: environment.package_version("nuitka"))


def _print_filename_size(path: str) -> None:
    size = Path(path).stat().st_size / 1024
    print(Stl.title(f"{size:.0f}"), Stl.low("KB"))


class Builder:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments) -> None:
        args = Args().parse_args()
        self.python_envs = set() if args.readme else args.get_python_envs(environments)
        self.onefile = not args.noexe
        self.upgrade = args.upgrade
        self.build = build
        self.nuitka_args = (
            "--mingw64" if args.mingw else "--clang",
            *IncludeFiles(build.files).all,
            *build.nuitka,
        )
        if self.onefile:
            self.nuitka_args = *self.nuitka_args, "--onefile"

    def _build_in_env(self, python_env: PythonEnv) -> None:
        dist_name = _get_dist_name(self.build, python_env.is_64)
        dist_temp = _get_dist_temp(self.build, python_env.is_64)
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
        builds = set()
        for python_env in self.python_envs:
            app_version = f"{self.build.name} v{self.build.version} {get_bitness_str(python_env.is_64)}"
            print(Stl.title("Build"), Stl.high(app_version))
            python_env.print()
            if python_env.check():
                if self.upgrade:
                    Upgrader(python_env).check(eager=False)
                self._build_in_env(python_env)
                builds.add(python_env.is_64)
            else:
                print(Stl.warn("Build Failed"))
            print()
        # missing versions
        for missing in {True, False} - builds:
            dist_name = _get_dist_name(self.build, missing)
            print(Stl.warn("Warning:"), Stl.high(dist_name), Stl.warn("not build !"))


def _get_sloc() -> int:
    get_py_files = "git ls-files -- '*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    sloc = subprocess.run(
        ("powershell", f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum"),
        text=True,
        check=False,
        capture_output=True,
    )
    try:
        return int(sloc.stdout)
    except ValueError:
        return 0


def _get_attr_lineno(obj: Any, name: str) -> int:
    lines, start = inspect.getsourcelines(obj)
    for node in ast.walk(ast.parse("".join(lines))):
        if isinstance(node, ast.Assign) and isinstance(target := node.targets[0], ast.Name) and target.id == name:
            return node.lineno + start - 1
    return 0


class Templater:
    _encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, templates: CfgTemplates) -> None:
        self.templates = templates
        python_version = _get_python_version(environments)
        dist_name32 = _get_dist_name(build, is_64=False)
        dist_name64 = _get_dist_name(build, is_64=True)
        self.template_format = dict(
            py_version_compact=python_version.replace(".", ""),
            line_of_x64=_get_attr_lineno(environments.x64, "path"),
            line_of_x86=_get_attr_lineno(environments.x86, "path"),
            nuitka_version=_get_nuitka_version(environments),
            github_path=f"{templates.owner}/{templates.repo}",
            archive64_link=quote(f"{dist_name64}.zip"),
            archive32_link=quote(f"{dist_name32}.zip"),
            exe64_link=quote(f"{dist_name64}.exe"),
            exe32_link=quote(f"{dist_name32}.exe"),
            py_version=python_version,
            ico_link=quote(build.ico),
            version=build.version,
            name=build.name,
            sloc=_get_sloc(),
        )

    def _apply_template(self, src: Path, dst: Path) -> None:
        print(Stl.title("create"), Stl.high(dst.as_posix()))
        template_text = src.read_text(encoding=Templater._encoding).format(**self.template_format)
        dst.write_text(template_text, encoding=Templater._encoding)

    def create_all(self) -> None:
        for template in self.templates.all:
            self._apply_template(Path(template.src), Path(template.dst))
