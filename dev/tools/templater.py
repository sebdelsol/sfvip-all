import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from .env.envs import PythonEnv, PythonEnvs
from .env.python import PythonVersion
from .nsis import MakeNSIS
from .scanner.file import ScanFile
from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist
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


def _get_exe_args(dist: Dist, python_env: PythonEnv) -> dict[str, str]:
    exe = dist.installer_exe(python_env)
    scan_file = ScanFile(exe)
    return {
        f"exe_{python_env.bitness}_link": quote(str(exe.as_posix())),
        f"exe_{python_env.bitness}_engine": scan_file.engine,
        f"exe_{python_env.bitness}_signature": scan_file.signature,
        f"exe_{python_env.bitness}_clean": "Clean-brightgreen" if scan_file.clean else "Failed-red",
    }


class Templater:
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        python_envs = PythonEnvs(environments)
        python_version = _version_of(python_envs, "Python")
        nuitka_version = _version_of(python_envs, "Nuitka")
        pyinstaller_version = _version_of(python_envs, "PyInstaller")
        if python_version and nuitka_version and pyinstaller_version:
            dist = Dist(build)
            self.template_format = dict(
                **_get_exe_args(dist, python_envs.x64),
                **_get_exe_args(dist, python_envs.x86),
                py_major_version=str(PythonVersion(python_version).major),
                py_version_compact=python_version.replace(".", ""),
                github_path=f"{github.owner}/{github.repo}",
                sloc=_get_sloc(Path(build.main).parent),
                nsis_version=MakeNSIS().get_version(),
                script_main=Path(build.main).stem,
                env_x64=environments.X64.path,
                env_x86=environments.X86.path,
                pyinstaller_version=pyinstaller_version,
                nuitka_version=nuitka_version,
                py_version=python_version,
                ico_link=quote(build.ico),
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
