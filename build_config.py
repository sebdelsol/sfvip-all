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
    version = "1.3.11"
    dir = "build"
    nuitka_args = (
        "--include-plugin-directory={python_env}/Lib/site-packages/mitmproxy_windows",
        f"--force-stderr-spec=%PROGRAM%/../{name} - %TIME%.log",
        "--enable-plugin=tk-inter",
        "--disable-console",
    )
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
