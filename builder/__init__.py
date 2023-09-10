import ast
import inspect
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Sequence
from urllib.parse import quote

from PIL import Image

from .color import Stl
from .command import CommandMonitor
from .env import EnvArgs, PythonEnv, get_bitness_str
from .protocols import CfgBuild, CfgEnvironments, CfgFile, CfgFileResize, CfgTemplates
from .upgrader import Upgrader


# comments are automatically turned into argparse help
class Args(EnvArgs):
    nobuild: bool = False  # update readme and post only
    readme: bool = False  # update readme and post only
    upgrade: bool = False  # upgrade the environment
    noexe: bool = False  # create only a zip (faster)
    nozip: bool = False  # create only a exe
    mingw: bool = False  # build with mingw64

    def process_args(self) -> None:
        super().process_args()
        self.nobuild |= self.readme


class IncludeFiles:
    def __init__(self, files: Sequence[CfgFile | CfgFileResize]) -> None:
        self._files = files

    def _create_all(self) -> None:
        if self._files:
            for file in self._files:
                if isinstance(file, CfgFileResize):
                    Image.open(file.src).resize(file.resize).save(file.path)
                print(Stl.title("Include"), Stl.high(file.path))

    @property
    def all(self) -> Iterator[str]:
        self._create_all()
        return (f"--include-data-file={file.path}={file.path}" for file in self._files)


def _dist_name(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def _dist_temp(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"


class Builder:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments) -> None:
        args = Args().parse_args()
        self.python_envs = args.get_python_envs(environments)
        self.build_exe = not (args.noexe or args.nobuild)
        self.build_zip = not (args.nozip or args.nobuild)
        self.upgrade = args.upgrade
        self.build = build
        self.nuitka_args = (
            f"--onefile-tempdir-spec=%CACHE_DIR%/{build.name}",
            *(("--onefile",) if self.build_exe else ()),
            f"--windows-file-version={build.version}",
            f"--windows-company-name={build.company}",
            "--mingw64" if args.mingw else "--clang",
            f"--windows-icon-from-ico={build.ico}",
            f"--output-filename={build.name}.exe",
            *IncludeFiles(build.files).all,
            "--assume-yes-for-downloads",
            "--python-flag=-OO",
            *build.nuitka_args,
            "--standalone",
            build.main,
        )

    def _build(self, python_env: PythonEnv) -> Iterator[str]:
        def _built(ext: Literal["exe", "zip"]) -> str:
            size = Path(f"{dist_name}.{ext}").stat().st_size / 1024
            print(Stl.title("Built"), Stl.high(f"{dist_name}.{ext}"), Stl.low(f"{size:.0f} KB"))
            return f"{dist_name}.{ext}"

        name = f"{self.build.name} v{self.build.version} {get_bitness_str(python_env.is_64)}"
        python_env.print()
        print(Stl.title("Building"), Stl.high(name))
        if python_env.check():
            if self.upgrade:
                Upgrader(python_env).check(eager=True)
            dist_name = _dist_name(self.build, python_env.is_64)
            dist_temp = _dist_temp(self.build, python_env.is_64)
            nuitka = CommandMonitor(python_env.exe, "-m", "nuitka", f"--output-dir={dist_temp}", *self.nuitka_args)
            if nuitka.run(out=Stl.title):
                Path(dist_name).parent.mkdir(parents=True, exist_ok=True)
                if self.build_zip:
                    shutil.make_archive(dist_name, "zip", f"{dist_temp}/{Path(self.build.main).stem}.dist")
                    yield _built("zip")
                if self.build_exe:
                    shutil.copy(f"{dist_temp}/{self.build.name}.exe", f"{dist_name}.exe")
                    yield _built("exe")
                return
        print(Stl.warn("Build failed"), Stl.high(name))

    def build_all(self) -> None:
        builts = []
        if self.build_exe or self.build_zip:
            for python_env in self.python_envs:
                for built in self._build(python_env):
                    builts.append(built)
        # missing versions
        for is_64 in True, False:
            for ext in "exe", "zip":
                build = f"{_dist_name(self.build, is_64)}.{ext}"
                if build not in builts:
                    print(Stl.warn("Not built"), Stl.high(build))


def _get_version_of(environments: CfgEnvironments, name: str, get_version: Callable[[PythonEnv], str]) -> str:
    versions = {is_64: get_version(PythonEnv(environments, is_64)) for is_64 in (True, False)}
    if versions[True] != versions[False]:
        print(Stl.high("x64"), Stl.warn("and"), Stl.high("x86"), Stl.warn(f"{name} versions differ !"))
        for is_64 in (True, False):
            print(" ", Stl.high(get_bitness_str(is_64)), Stl.title(f"{name} is"), Stl.high(versions[is_64]))
    return versions[True]


def _get_python_version(environments: CfgEnvironments) -> str:
    return _get_version_of(environments, "Python", lambda environment: environment.python_version)


def _get_nuitka_version(environments: CfgEnvironments) -> str:
    return _get_version_of(environments, "Nuitka", lambda environment: environment.package_version("nuitka"))


def _get_sloc(path: Path) -> int:
    get_py_files = f"git ls-files -- '{path}/*.py'"
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


def _get_attr_link(obj: Any, attr: str) -> str:
    lines, start = inspect.getsourcelines(obj)
    for node in ast.walk(ast.parse(textwrap.dedent("".join(lines)))):
        if isinstance(node, ast.Assign) and isinstance(target := node.targets[0], ast.Name) and target.id == attr:
            path = inspect.getfile(obj).replace(str(Path().resolve()), "").replace("\\", "/")
            return f"[`{obj.__qualname__}.{attr}`]({path}#L{node.lineno + start - 1})"
    return ""


class Templater:
    _encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, templates: CfgTemplates) -> None:
        self.templates = templates.all
        python_version = _get_python_version(environments)
        dist_name32 = _dist_name(build, is_64=False)
        dist_name64 = _dist_name(build, is_64=True)
        self.template_format = dict(
            github_path=f"{templates.Github.owner}/{templates.Github.repo}",
            env_x64_decl=_get_attr_link(environments.X64, "path"),
            env_x86_decl=_get_attr_link(environments.X86, "path"),
            py_version_compact=python_version.replace(".", ""),
            nuitka_version=_get_nuitka_version(environments),
            archive64_link=quote(f"{dist_name64}.zip"),
            archive32_link=quote(f"{dist_name32}.zip"),
            sloc=_get_sloc(Path(build.main).parent),
            exe64_link=quote(f"{dist_name64}.exe"),
            exe32_link=quote(f"{dist_name32}.exe"),
            script_main=Path(build.main).stem,
            env_x64=environments.X64.path,
            env_x86=environments.X86.path,
            py_version=python_version,
            ico_link=quote(build.ico),
            version=build.version,
            name=build.name,
        )

    def _apply_template(self, src: Path, dst: Path) -> None:
        print(Stl.title("Create"), Stl.high(dst.as_posix()))
        template_text = src.read_text(encoding=Templater._encoding).format(**self.template_format)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(template_text, encoding=Templater._encoding)

    def create_all(self) -> None:
        if self.templates:
            for template in self.templates:
                self._apply_template(Path(template.src), Path(template.dst))
