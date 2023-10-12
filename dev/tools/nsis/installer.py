from pathlib import Path
from typing import NamedTuple, Sequence

from ..utils.dist import Dist, to_ico
from ..utils.env import PythonEnv
from ..utils.protocols import CfgBuild, CfgLOC


def get_cmd(name: str, cmd: Sequence[str]) -> dict[str, str | int]:
    return {
        f"has_{name}_cmd": int(bool(cmd)),
        f"{name}_cmd": cmd[0] if cmd else "",
        f"{name}_cmd_arg": " ".join(cmd[1:]) if cmd else "",
    }


def get_languages(loc: CfgLOC) -> str:
    lang_macro = '!insertmacro MUI_LANGUAGE "%s"'
    lang_macros = (lang_macro % lang.capitalize() for lang in loc.all_languages)
    return "\n".join(("languages", *lang_macros))  # 1st line is a comment


def get_already_running(loc: CfgLOC, name: str) -> str:
    lang_string = 'LangString already_running ${LANG_%s} "%s"'
    lang_strings = []
    for lang in loc.all_languages:
        loc.set_language(lang)
        lang_strings.append(lang_string % (lang.upper(), loc.AlreadyRunning % name))
    return "\n".join(("already running", *lang_strings))  # 1st line is a comment


def get_version(version: str, length: int) -> str:
    versions = version.split(".")
    if len(versions) < length:
        versions.extend((["0"] * (length - len(versions))))
    return ".".join(versions[:length])


class NSISInstall(NamedTuple):
    script: Path
    exe: Path


class NSISInstaller:
    template = Path(__file__).parent / "template.nsi"
    template_args_markers = ("[[", "{"), ("]]", "}")
    nsis_markers = ("{", "<<<"), ("}", ">>>")
    script = "installer.nsi"
    version_length = 4
    encoding = "utf-8"

    def __init__(self, build: CfgBuild, loc: CfgLOC) -> None:
        self.dist = Dist(build)
        self.template_args = dict(
            finish_page=int(build.install_finish_page),
            **get_cmd("install", build.install_cmd),
            **get_cmd("uninstall", build.uninstall_cmd),
            has_logs=int(bool(build.logs_dir)),
            logs_dir=str(Path(build.logs_dir)),
            name=build.name,
            version=get_version(build.version, NSISInstaller.version_length),
            company=build.company,
            ico=str(Path(to_ico(build.ico))),
            languages=get_languages(loc),
            already_running=get_already_running(loc, build.name),
            dist=self.dist.dist_dir_name,
        )

    def create(self, python_env: PythonEnv) -> NSISInstall:
        with NSISInstaller.template.open("r", encoding=NSISInstaller.encoding) as f:
            template = f.read()
        for old, new in *NSISInstaller.nsis_markers, *NSISInstaller.template_args_markers:
            template = template.replace(old, new)
        exe = self.dist.installer_exe(python_env)
        exe.parent.mkdir(parents=True, exist_ok=True)
        code = template.format(
            bitness=python_env.bitness_str,
            installer=str(exe.resolve()),
            **self.template_args,
        )
        for old, new in NSISInstaller.nsis_markers:
            code = code.replace(new, old)
        script = self.dist.build_dir(python_env) / NSISInstaller.script
        with script.open("w", encoding=NSISInstaller.encoding) as f:
            f.write(code)
        return NSISInstall(script=script, exe=exe)
