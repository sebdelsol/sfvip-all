from typing import ClassVar

from build_config import Environments as MasterEnvironments


class Build:
    main: ClassVar = "user_proxy_cmd/cmd.py"
    ico: ClassVar = "resources/Sfvip All.png"
    dir: ClassVar = "user_proxy_cmd/build"
    name: ClassVar = "SfvipUserProxy"
    company: ClassVar = "sebdelsol"
    version: ClassVar = "0.4"
    logs_dir: ClassVar = ""
    enable_console: ClassVar = True
    files: ClassVar = ()
    excluded: ClassVar = ()
    install_finish_page: ClassVar = False
    install_cmd: ClassVar = f"{name}.exe", "install"
    uninstall_cmd: ClassVar = f"{name}.exe", "uninstall"


class Readme:
    src: ClassVar = "user_proxy_cmd/resources/README_template.md"
    dst: ClassVar = "user_proxy_cmd/README.md"


class Post:
    src: ClassVar = "user_proxy_cmd/resources/post_template.txt"
    dst: ClassVar = f"{Build.dir}/temp/post.txt"


class Templates:
    all: ClassVar = Readme, Post


class Environments(MasterEnvironments):
    requirements: ClassVar = ()
