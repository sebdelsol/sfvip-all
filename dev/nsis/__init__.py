import shutil
import winreg
from pathlib import Path
from typing import Sequence

from ..tools.color import Low, Ok, Title, Warn
from ..tools.command import CommandMonitor
from ..tools.dist import get_bitness_str, get_dist_name, get_dist_temp, to_ico
from ..tools.env import PythonEnv
from ..tools.protocols import CfgBuild
from .virus_scan import VirusScan


def get_cmd(name: str, cmd: Sequence[str]) -> dict[str, str | int]:
    return {
        f"has_{name}_cmd": int(bool(cmd)),
        f"{name}_cmd": cmd[0] if cmd else "",
        f"{name}_cmd_arg": " ".join(cmd[1:]) if cmd else "",
    }


def get_languages(all_languages: Sequence[str]) -> str:
    lang_macro = '!insertmacro MUI_LANGUAGE "%s"'
    lang_macros = (lang_macro % lang.capitalize() for lang in all_languages)
    return "\n".join(("languages", *lang_macros))  # 1st line is a comment


def get_version(version: str, length: int) -> str:
    versions = version.split(".")
    if len(versions) < length:
        versions.extend((["0"] * (length - len(versions))))
    return ".".join(versions[:length])


class NSIS:
    regkey64 = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\NSIS"
    regkey = winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NSIS"
    template = Path(__file__).parent / "installer_template.nsi"
    exe = "makensis.exe"
    nsis_arg = "/V4"
    encoding = "utf-8"
    version_length = 4

    def __init__(self, build: CfgBuild, all_languages: Sequence[str], do_run: bool) -> None:
        self.build = build
        self.do_run = do_run
        self.virus_scan = VirusScan()
        self.format = dict(
            finish_page=int(build.install_finish_page),
            **get_cmd("install", build.install_cmd),
            **get_cmd("uninstall", build.uninstall_cmd),
            name=build.name,
            version=get_version(build.version, NSIS.version_length),
            company=build.company,
            ico=to_ico(build.ico),
            languages=get_languages(all_languages),
            dist=f"{Path(build.main).stem}.dist",
        )

    @property
    def nsis_path(self) -> Path:
        try:
            nsis_dir = winreg.QueryValue(*NSIS.regkey)
        except OSError:
            nsis_dir = winreg.QueryValue(*NSIS.regkey64)
        return Path(nsis_dir) / NSIS.exe

    def create_script(self, python_env: PythonEnv) -> str:
        dist_temp = get_dist_temp(self.build, python_env.is_64)
        with NSIS.template.open("r", encoding=NSIS.encoding) as f:
            template = f.read()
        code = template.format(bitness=get_bitness_str(python_env.is_64), **self.format)
        script = Path(dist_temp) / "installer.nsi"
        with script.open("w", encoding=NSIS.encoding) as f:
            f.write(code)
        return str(script.resolve())

    def create_dist(self, python_env: PythonEnv) -> str:
        dist_temp = get_dist_temp(self.build, python_env.is_64)
        dist_name = get_dist_name(self.build, python_env.is_64)
        Path(dist_name).parent.mkdir(parents=True, exist_ok=True)
        exe = f"{dist_name}.exe"
        shutil.copy(f"{dist_temp}/{self.build.name}.exe", exe)
        size = Path(exe).stat().st_size / 1024
        print(Title("Built"), Ok(exe), Low(f"{size:.0f} KB"))
        return exe

    def run(self, python_env: PythonEnv) -> str:
        if self.do_run:
            print(Title("Installer by NSIS"))
            script = self.create_script(python_env)
            nsis = CommandMonitor(self.nsis_path, NSIS.nsis_arg, script)
            if nsis.run(out=Title, err=Warn):
                dist_temp = get_dist_temp(self.build, python_env.is_64)
                if self.virus_scan.run_on(Path(dist_temp)):
                    return self.create_dist(python_env)
        else:
            print(Warn("Skip Installer by NSIS"))
        return ""
