class Build:
    ico = "ressources/Sfvip All.png"
    main = "sfvip_all.py"
    company = "sebdelsol"
    name = "Sfvip All"
    version = "1.2.4"
    dir = "build"


class Nuitka:
    args = [
        f"--force-stderr-spec=%PROGRAM%/../{Build.name} - %TIME%.log",
        "--enable-plugin=tk-inter",
        "--disable-console",
    ]


class Templates:
    list = [
        ("ressources/README_template.md", "README.md"),
        ("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt"),
    ]


class Environments:
    requirements = ["requirements.txt", "requirements.dev.txt"]
    x86 = ".sfvip32"
    x64 = ".sfvip"


class Splash:
    path = "ressources/Sfvip All.png"
    src = None


class Logo:
    path = "ressources/logo.png"
    src = "ressources/Sfvip All.png", 28


class Github:
    owner = "sebdelsol"
    repo = "sfvip-all"
