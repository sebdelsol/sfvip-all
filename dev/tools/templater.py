import ast
import inspect
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote

from .nsis import MakeNSIS
from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist
from .utils.env import PythonEnv, PythonEnvs
from .utils.protocols import (
    CfgBuild,
    CfgEnvironments,
    CfgGithub,
    CfgTemplate,
    CfgTemplates,
)


def _version_of(python_envs: PythonEnvs, name: str, get_version: Callable[[PythonEnv], str]) -> Optional[str]:
    versions = {python_env: get_version(python_env) for python_env in python_envs.all}
    versions_set = set(versions.values())
    if len(versions_set) > 1:
        print(Warn(f"{name} versions differ"))
        for python_env, version in versions.items():
            print(".", Ok(python_env.bitness), Title(f"{name} is"), Warn(version))
        return None
    return versions_set.pop()


def _python_version(python_envs: PythonEnvs) -> Optional[str]:
    return _version_of(python_envs, "Python", lambda python_env: python_env.python_version)


def _nuitka_version(python_envs: PythonEnvs) -> Optional[str]:
    return _version_of(python_envs, "Nuitka", lambda python_env: python_env.package_version("nuitka"))


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


def _get_requirements(python_env: PythonEnv) -> str:
    requirements = (f"-r {requirements}" for requirements in python_env.requirements)
    constraints = (f"-c {constraints}" for constraints in python_env.constraints)
    return " ".join((*requirements, *constraints))


class Templater:
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        python_envs = PythonEnvs(environments)
        python_version = _python_version(python_envs)
        nuitka_version = _nuitka_version(python_envs)
        if python_version and nuitka_version:
            dist = Dist(build)
            self.template_format = dict(
                exe64_link=quote(str(dist.installer_exe(python_envs.x64).as_posix())),
                exe32_link=quote(str(dist.installer_exe(python_envs.x86).as_posix())),
                env_x64_decl=_get_attr_link(environments.X64, "path"),
                env_x86_decl=_get_attr_link(environments.X86, "path"),
                requirements_x64=_get_requirements(python_envs.x64),
                requirements_x86=_get_requirements(python_envs.x86),
                py_version_compact=python_version.replace(".", ""),
                github_path=f"{github.owner}/{github.repo}",
                sloc=_get_sloc(Path(build.main).parent),
                nsis_version=MakeNSIS().get_version(),
                script_main=Path(build.main).stem,
                env_x64=environments.X64.path,
                env_x86=environments.X86.path,
                nuitka_version=nuitka_version,
                py_version=python_version,
                ico_link=quote(build.ico),
                version=build.version,
                name=build.name,
            )
        else:
            self.template_format = None

    def create(self, template: CfgTemplate) -> None:
        if self.template_format:
            src, dst = Path(template.src), Path(template.dst)
            print(Title("Create"), Ok(dst.as_posix()), Low(f"from {src.as_posix()}"))
            text = src.read_text(encoding=Templater.encoding).format(**self.template_format)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding=Templater.encoding)

    def create_all(self, templates: CfgTemplates) -> None:
        for template in templates.all:
            self.create(template)
