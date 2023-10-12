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
    version = "1.4.0"
    dir = "build"
    enable_console = False
    logs_dir = "../logs"
    nuitka_plugins = ("tk-inter",)
    nuitka_plugin_dirs = ("mitmproxy_windows",)
    files = Splash, Logo, Translations
    update = "update_{bitness}.json"
    install_finish_page = True
    install_cmd = ()
    uninstall_cmd = ()


class Environments:
    class X64:
        path = ".sfvip64"
        requirements = "requirements.txt", "requirements.dev.txt"

    class X86:
        path = ".sfvip86"
        requirements = "requirements.txt", "requirements.dev.txt", "requirements.x86.txt"


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
