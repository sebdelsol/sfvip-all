from build_config import Environments, Github
from builder import Builder, CreateTemplates, Datas


class Build:
    main = "sfvip_user_proxy/sfvip_user_proxy.py"
    ico = "ressources/Sfvip All.png"
    dir = "sfvip_user_proxy/build"
    name = "SfvipUserProxy"
    company = "sebdelsol"
    version = "0.2"


class Nuitka:
    args = ["--enable-console"]


class Templates:
    list = [
        ("sfvip_user_proxy/README_template.md", "sfvip_user_proxy/README.md"),
        ("sfvip_user_proxy/post_template.txt", f"{Build.dir}/{Build.version}/post.txt"),
    ]


class UserProxyEnvironements:
    requirements = []
    x86 = Environments.x86
    x64 = Environments.x64


if __name__ == "__main__":
    Builder(Build, UserProxyEnvironements, Nuitka, Datas()).build_all()
    CreateTemplates(Build, UserProxyEnvironements, Templates, Github).create_all()
