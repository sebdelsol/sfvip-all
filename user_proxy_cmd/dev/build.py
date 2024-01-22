from build_config import Environments as MasterEnvironments
from dev.build import do_build


class Build:
    main = "user_proxy_cmd/cmd.py"
    ico = "resources/Sfvip All.png"
    dir = "user_proxy_cmd/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.4"
    logs_dir = ""
    enable_console = True
    files = ()
    excluded = ()
    install_finish_page = False
    install_cmd = f"{name}.exe", "install"
    uninstall_cmd = f"{name}.exe", "uninstall"


class Readme:
    src = "user_proxy_cmd/resources/README_template.md"
    dst = "user_proxy_cmd/README.md"


class Post:
    src = "user_proxy_cmd/resources/post_template.txt"
    dst = f"{Build.dir}/{Build.version}/post.txt"


class Templates:
    all = Readme, Post


class Environments(MasterEnvironments):
    requirements = ()


if __name__ == "__main__":
    do_build(Build, Environments, Templates, Readme)
