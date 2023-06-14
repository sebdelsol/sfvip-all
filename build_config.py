class Github:
    owner = "sebdelsol"
    repo = "sfvip-all"


class Build:
    requirements = "requirements.txt", "requirements.dev.txt"
    splash = "ressources/Sfvip All.png"
    ico = "ressources/Sfvip All.png"
    main = "sfvip_all.py"
    company = "sebdelsol"
    name = "Sfvip All"
    version = "1.1.9"
    dir = "build"

    class Environment:
        x86 = ".sfvip32"
        x64 = ".sfvip"

    class Logo:
        use = "ressources/Sfvip All.png"
        path = "ressources/logo.png"
        size = 28, 28
