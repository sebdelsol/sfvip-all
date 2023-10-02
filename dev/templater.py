import ast
import inspect
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from .tools.color import Ok, Title, Warn
from .tools.dist import get_dist_name
from .tools.env import PythonEnv, get_bitness_str
from .tools.protocols import (
    CfgBuild,
    CfgEnvironments,
    CfgGithub,
    CfgTemplate,
    CfgTemplates,
)


def _get_version_of(environments: CfgEnvironments, name: str, get_version: Callable[[PythonEnv], str]) -> str:
    versions = {is_64: get_version(PythonEnv(environments, is_64)) for is_64 in (True, False)}
    if versions[True] != versions[False]:
        print(Ok("x64"), Warn("and"), Ok("x86"), Warn(f"{name} versions differ !"))
        for is_64 in (True, False):
            print(" ", Ok(get_bitness_str(is_64)), Title(f"{name} is"), Ok(versions[is_64]))
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
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        python_version = _get_python_version(environments)
        dist_name32 = get_dist_name(build, is_64=False)
        dist_name64 = get_dist_name(build, is_64=True)
        self.template_format = dict(
            env_x64_decl=_get_attr_link(environments.X64, "path"),
            env_x86_decl=_get_attr_link(environments.X86, "path"),
            py_version_compact=python_version.replace(".", ""),
            nuitka_version=_get_nuitka_version(environments),
            github_path=f"{github.owner}/{github.repo}",
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

    def create(self, template: CfgTemplate) -> None:
        src, dst = Path(template.src), Path(template.dst)
        print(Title("Create"), Ok(dst.as_posix()))
        text = src.read_text(encoding=Templater.encoding).format(**self.template_format)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding=Templater.encoding)

    def create_all(self, templates: CfgTemplates) -> None:
        for template in templates.all:
            self.create(template)
