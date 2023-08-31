class Splash:
    path = "ressources/Sfvip All.png"


class Logo:
    path = "ressources/logo.png"
    src = "ressources/Sfvip All.png"
    resize = 28, 28


class Build:
    ico = "ressources/Sfvip All.png"
    main = "sfvip_all.py"
    company = "sebdelsol"
    name = "Sfvip All"
    version = "1.2.4"
    dir = "build"
    nuitka = (
        f"--force-stderr-spec=%PROGRAM%/../{name} - %TIME%.log",
        "--enable-plugin=tk-inter",
        "--disable-console",
    )
    files = Splash, Logo


class Environmentx64:
    path = ".sfvip64"
    requirements = "requirements.txt", "requirements.dev.txt"


class Environmentx86:
    path = ".sfvip86"
    requirements = *Environmentx64.requirements, "requirements.constraints.x86.txt"


class Environments:
    x64 = Environmentx64
    x86 = Environmentx86


class Readme:
    src = "ressources/README_template.md"
    dst = "README.md"


class Post:
    src = "ressources/post_template.txt"
    dst = f"{Build.dir}/{Build.version}/post.txt"


class Templates:
    all = Readme, Post
    owner = "sebdelsol"
    repo = "sfvip-all"
