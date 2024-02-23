import subprocess
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import quote

from .env.envs import PythonEnvs
from .env.python import PythonVersion
from .nsis import MakeNSIS
from .release import ReleaseCreator
from .utils.color import Low, Ok, Title, Warn
from .utils.protocols import (
    CfgBuild,
    CfgEnvironments,
    CfgGithub,
    CfgTemplate,
    CfgTemplates,
)


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


def _get_sloc(path: Path) -> int:
    get_py_files = f"git ls-files -- '{path}/*.py'"
    count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
    sloc = subprocess.run(
        ("PowerShell", f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum"),
        text=True,
        check=False,
        capture_output=True,
    )
    try:
        return int(sloc.stdout)
    except ValueError:
        return 0


def _get_exe_args(build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> Iterator[tuple[str, str]]:
    for installer in ReleaseCreator(build, environments, github).create_all(build.version):
        yield f"exe_{installer.bitness}_release", installer.url
        yield f"exe_{installer.bitness}_engine", installer.scan.engine
        yield f"exe_{installer.bitness}_signature", installer.scan.signature
        yield f"exe_{installer.bitness}_clean", "clean-brightgreen" if installer.scan.clean else "failed-red"


class Templater:
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        python_envs = PythonEnvs(environments)
        python_version = _version_of(python_envs, "Python")
        nuitka_version = _version_of(python_envs, "Nuitka")
        pyinstaller_version = _version_of(python_envs, "PyInstaller")
        mitmproxy_version = _version_of(python_envs, "mitmproxy")
        if python_version and nuitka_version and pyinstaller_version and mitmproxy_version:
            self.template_format = dict(
                dict(arg for arg in _get_exe_args(build, environments, github)),
                py_major_version=str(PythonVersion(python_version).major),
                py_version_compact=python_version.replace(".", ""),
                github_path=f"{github.owner}/{github.repo}",
                pyinstaller_version=pyinstaller_version,
                sloc=_get_sloc(Path(build.main).parent),
                nsis_version=MakeNSIS().get_version(),
                mitmproxy_version=mitmproxy_version,
                script_main=Path(build.main).stem,
                env_x64=environments.X64.path,
                env_x86=environments.X86.path,
                nuitka_version=nuitka_version,
                py_version=python_version,
                ico_link=quote(build.ico),
                github_owner=github.owner,
                github_repo=github.repo,
                version=build.version,
                name=build.name,
            )
        else:
            self.template_format = None

    def create(self, template: CfgTemplate) -> None:
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
            self.create(template)
