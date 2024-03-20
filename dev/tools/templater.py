import ast
import inspect
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from .env.envs import PythonEnvs
from .env.python import PythonVersion
from .nsis import MakeNSIS
from .publisher import Publisher
from .scanner.file import ScanFile
from .utils.color import Low, Ok, Title, Warn
from .utils.dist import human_format, repr_size
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub, CfgTemplate, CfgTemplates


def _version_of(python_envs: PythonEnvs, name: str) -> Optional[str]:
    env_versions = {
        python_env: python_env.python_version if name == "Python" else python_env.package_version(name.lower())
        for python_env in python_envs.all
    }
    versions = set(env_versions.values())
    if len(versions) > 1:
        print(Title(name), Warn("versions differ"))
        for python_env, version in env_versions.items():
            print(".", Ok(python_env.bitness), Title(f"{name} is"), Warn(version))
        return None
    return versions.pop()


def _get_sloc(path: Path) -> str:
    get_py_files = f"git ls-files -- '{path}/*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    sloc = subprocess.run(
        ("PowerShell", f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum"),
        text=True,
        check=False,
        capture_output=True,
    )
    try:
        return human_format(int(sloc.stdout))
    except ValueError:
        return "unknown"


def _get_attr_link(obj: Any, attr: str) -> str:
    lines, start = inspect.getsourcelines(obj)
    for node in ast.walk(ast.parse(textwrap.dedent("".join(lines)))):
        if isinstance(node, ast.AnnAssign) and isinstance(target := node.target, ast.Name) and target.id == attr:
            path = inspect.getfile(obj).replace(str(Path().resolve()), "").replace("\\", "/")
            return f"{path}#L{node.lineno + start - 1}"
    return ""


def _get_exe_kwargs(build: CfgBuild, python_envs: PythonEnvs, publisher: Publisher) -> dict[str, str]:
    kwargs = {}
    local_versions = {local_version.bitness: local_version for local_version in publisher.get_local_versions()}
    for python_env in python_envs.all:
        bitness = python_env.bitness
        local_version = local_versions.get(bitness)
        scan = ScanFile(local_version.exe) if local_version else ScanFile
        if local_version:
            version_color = Ok if local_version.version == build.version else Warn
            print(
                Ok(f". {build.name}"),
                version_color(f"{local_version.version} {bitness}"),
                Low(f"- {repr_size(local_version.exe)}"),
            )
        else:
            print(Warn(f". No {build.name} {bitness} version"))
        kwargs |= {
            f"version_{bitness}": local_version.version if local_version else "0",
            f"exe_{bitness}_release": local_version.url if local_version else "",
            f"exe_{bitness}_engine": scan.engine,
            f"exe_{bitness}_signature": scan.signature,
            f"exe_{bitness}_clean": "clean-brightgreen" if scan.clean else "failed-red",
        }
    return kwargs


def get_env_kwargs(python_envs: PythonEnvs) -> dict[str, str]:
    kwargs = {}
    for bitness, environment in python_envs.declarations.items():
        kwargs |= {
            f"{bitness}_env_link": _get_attr_link(environment, "path"),
            f"env_{bitness}": environment.path,
        }
    return kwargs


class Templater:
    encoding = "utf-8"
    h_download = 35
    h_github = 25

    def __init__(
        self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub, publisher: Publisher
    ) -> None:
        python_envs = PythonEnvs(environments)
        if (
            (python_version := _version_of(python_envs, "Python"))
            and (nuitka_version := _version_of(python_envs, "Nuitka"))
            and (mitmproxy_version := _version_of(python_envs, "mitmproxy"))
            and (pyinstaller_version := _version_of(python_envs, "PyInstaller"))
        ):
            print(Title("Build"), Ok("template"))
            self.template_format = dict(
                py_major_version=str(PythonVersion(python_version).major),
                build_version_link=_get_attr_link(build, "version"),
                py_version_compact=python_version.replace(".", ""),
                **_get_exe_kwargs(build, python_envs, publisher),
                github_path=f"{github.owner}/{github.repo}",
                pyinstaller_version=pyinstaller_version,
                sloc=_get_sloc(Path(build.main).parent),
                nsis_version=MakeNSIS().get_version(),
                mitmproxy_version=mitmproxy_version,
                script_main=Path(build.main).stem,
                h_download=Templater.h_download,
                h_github=Templater.h_github,
                **get_env_kwargs(python_envs),
                nuitka_version=nuitka_version,
                build_version=build.version,
                py_version=python_version,
                ico_link=quote(build.ico),
                github_owner=github.owner,
                github_repo=github.repo,
                name=build.name,
            )
        else:
            self.template_format = None

    def _create(self, template: CfgTemplate) -> None:
        src, dst = Path(template.src), Path(template.dst)
        if self.template_format:
            print(Title("Create"), Ok(dst.as_posix()), Low(f"from {src.as_posix()}"))
            text = src.read_text(encoding=Templater.encoding).format(**self.template_format)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding=Templater.encoding)
        else:
            print(Warn("Not created:"), Ok(dst.as_posix()), Low(f"from {src.as_posix()}"))

    def create_all(self, templates: CfgTemplates) -> None:
        for template in templates.all:
            self._create(template)

    def create(self, templates: CfgTemplates, name: str) -> None:
        if template := {template.__name__: template for template in templates.all}.get(name):
            self._create(template)
