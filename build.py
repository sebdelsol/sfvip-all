import shutil

import PyInstaller.__main__

from sfvip import Player
from sfvip.config import CONFIG

NAME = "sfvip_all"
sfvip_player = Player(CONFIG)
if sfvip_player.valid():
    PyInstaller.__main__.run(
        [
            f"{NAME}.py",
            "--noconfirm",
            "--noconsole",
            "-i",
            rf"{sfvip_player.player},0",
        ]
    )
    print("create the zip archive")
    shutil.make_archive(NAME, "zip", f"./dist/{NAME}")
