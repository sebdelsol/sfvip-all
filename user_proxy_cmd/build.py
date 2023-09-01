from build_config import Environments, Templates
from builder import Builder, Templater


class Build:
    main = "user_proxy_cmd/cmd.py"
    ico = "ressources/Sfvip All.png"
    dir = "user_proxy_cmd/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.3"
    nuitka_args = ["--enable-console"]
    files = []


class Readme:
    src = "user_proxy_cmd/ressources/README_template.md"
    dst = "user_proxy_cmd/README.md"


class Post:
    src = "user_proxy_cmd/ressources/post_template.txt"
    dst = f"{Build.dir}/{Build.version}/post.txt"


Templates.all = Readme, Post  # type: ignore
Environments.X64.requirements = []  # type: ignore
Environments.X86.requirements = []  # type: ignore


if __name__ == "__main__":
    Builder(Build, Environments).build_all()
    Templater(Build, Environments, Templates).create_all()
