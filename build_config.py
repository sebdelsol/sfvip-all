from typing import ClassVar


class Splash:
    path: ClassVar = "resources/Sfvip All.png"


class Logo:
    path: ClassVar = "resources/logo.png"
    src: ClassVar = "resources/Sfvip All.png"
    resize: ClassVar = 28, 28


class Translations:
    path: ClassVar = "translations"


class Changelog:
    path: ClassVar = "build/changelog.md"


class Build:
    ico: ClassVar = "resources/Sfvip All.png"
    main: ClassVar = "sfvip_all.py"
    company: ClassVar = "sebdelsol"
    name: ClassVar = "Sfvip All"
    version: ClassVar = "1.4.12.45"
    dir: ClassVar = "build"
    enable_console: ClassVar = False
    logs_dir: ClassVar = "../logs"
    excluded: ClassVar = ("numpy",)
    files: ClassVar = Splash, Logo, Translations, Changelog
    install_finish_page: ClassVar = True
    install_cmd: ClassVar = ()
    uninstall_cmd: ClassVar = ()


class Environments:
    requirements: ClassVar = "requirements.txt", "requirements.dev.txt"
    python: ClassVar = "3.11"

    class X64:
        path: ClassVar = ".sfvip64"
        constraints: ClassVar = ()

    class X86:
        path: ClassVar = ".sfvip86"
        constraints: ClassVar = ()


class Github:
    owner: ClassVar = "sebdelsol"
    repo: ClassVar = "sfvip-all"


class Readme:
    src: ClassVar = "resources/README_template.md"
    dst: ClassVar = "README.md"


class Post:
    src: ClassVar = "resources/post_template.txt"
    dst: ClassVar = f"{Build.dir}/temp/post.txt"


class Templates:
    all: ClassVar = Readme, Post
