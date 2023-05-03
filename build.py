import PyInstaller.__main__

from sfvip import Player
from sfvip.config import CONFIG

sfvip_player = Player(CONFIG)
if sfvip_player.valid():
    PyInstaller.__main__.run(
        [
            "sfvip_all.py",
            "--noconfirm",
            "--noconsole",
            "-i",
            rf"{sfvip_player.player},0",
        ]
    )
