class Splash:
    path = "resources/Sfvip All.png"


class Logo:
    path = "resources/logo.png"
    src = "resources/Sfvip All.png"
    resize = 28, 28


class Translations:
    path = "translations"


class Build:
    ico = "resources/Sfvip All.png"
    main = "sfvip_all.py"
    company = "sebdelsol"
    name = "Sfvip All"
    version = "1.4.5"
    dir = "build"
    enable_console = False
    logs_dir = "../logs"
    files = Splash, Logo, Translations
    install_finish_page = True
    install_cmd = ()
    uninstall_cmd = ()


class Environments:
    requirements = "requirements.txt", "requirements.dev.txt"

    class X64:
        path = ".sfvip64"
        constraints = ()

    class X86:
        path = ".sfvip86"
        constraints = ("constraints.x86.txt",)


class Readme:
    src = "resources/README_template.md"
    dst = "README.md"


class Post:
    src = "resources/post_template.txt"
    dst = f"{Build.dir}/{Build.version}/post.txt"


class Github:
    owner = "sebdelsol"
    repo = "sfvip-all"


class Templates:
    all = Readme, Post
