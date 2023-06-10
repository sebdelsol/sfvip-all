import sys


class Github:
    owner = "sebdelsol"
    repo = "sfvip-all"


class Build:
    splash = "ressources/Sfvip All.png"
    ico = "ressources/Sfvip All.png"
    main = "sfvip_all.py"
    company = "sebdelsol"
    name = "Sfvip All"
    version = "1.1.8"
    dir = "build"

    class Logo:
        use = "ressources/Sfvip All.png"
        path = "ressources/logo.png"
        size = 28, 28

    class Python:
        version = sys.version.split(" ", maxsplit=1)[0]
        bitness = "x64" if sys.maxsize == (2**63) - 1 else "x86"
