from build_config import Environments, Github
from builder import Builder, CreateTemplates, Datas


class Build:
    main = "user_proxy_cmd/cmd.py"
    ico = "ressources/Sfvip All.png"
    dir = "user_proxy_cmd/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.2"


class Nuitka:
    args = ["--enable-console"]


class Templates:
    list = [
        ("user_proxy_cmd/ressources/README_template.md", "user_proxy_cmd/README.md"),
        ("user_proxy_cmd/ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt"),
    ]


class UserProxyEnvironements:
    requirements = []
    x86 = Environments.x86
    x64 = Environments.x64


if __name__ == "__main__":
    Builder(Build, UserProxyEnvironements, Nuitka, Datas()).build_all()
    CreateTemplates(Build, UserProxyEnvironements, Templates, Github).create_all()
