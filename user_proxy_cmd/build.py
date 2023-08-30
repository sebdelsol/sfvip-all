from build_config import Environments, Github
from builder import Builder, Datas, Templater


class Build:
    main = "user_proxy_cmd/cmd.py"
    ico = "ressources/Sfvip All.png"
    dir = "user_proxy_cmd/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.3"


class Nuitka:
    args = ["--enable-console"]


class Templates:
    all = (
        ("user_proxy_cmd/ressources/README_template.md", "user_proxy_cmd/README.md"),
        ("user_proxy_cmd/ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt"),
    )


Environments.x64.requirements = ()  # type: ignore
Environments.x86.requirements = ()  # type: ignore


if __name__ == "__main__":
    Builder(Build, Environments, Nuitka, Datas()).build_all()
    Templater(Build, Environments, Templates, Github).create_all()
