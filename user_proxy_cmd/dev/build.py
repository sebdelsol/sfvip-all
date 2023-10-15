from pathlib import Path

from build_config import Environments, Github, Templates, Translations
from dev.tools.builder import Builder
from dev.tools.cleaner import clean_old_build
from dev.tools.templater import Templater
from src.sfvip.localization import LOC


class Build:
    main = "user_proxy_cmd/cmd.py"
    ico = "resources/Sfvip All.png"
    dir = "user_proxy_cmd/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.4"
    logs_dir = ""
    enable_console = True
    nuitka_plugins = ()
    nuitka_plugin_dirs = ()
    files = ()
    update = ""
    install_finish_page = False
    install_cmd = f"{name}.exe", "install"
    uninstall_cmd = f"{name}.exe", "uninstall"


class Readme:
    src = "user_proxy_cmd/resources/README_template.md"
    dst = "user_proxy_cmd/README.md"


class Post:
    src = "user_proxy_cmd/resources/post_template.txt"
    dst = f"{Build.dir}/{Build.version}/post.txt"


Templates.all = Readme, Post  # type: ignore
Environments().requirements = ()  # type: ignore
Environments.X64.constraints = ()  # type: ignore
Environments.X86.constraints = ()  # type: ignore

if __name__ == "__main__":
    LOC.set_tranlastions(Path(Translations.path))
    if Builder(Build, Environments, Github, LOC).build_all():
        Templater(Build, Environments, Github).create_all(Templates)
        clean_old_build(Build, Environments, Github, Readme)
    else:
        Templater(Build, Environments, Github).create(Readme)
