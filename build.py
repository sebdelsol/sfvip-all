import shutil

import PyInstaller.__main__
import pyinstaller_versionfile

from sfvip import Player
from sfvip.config import CONFIG

sfvip_player = Player(CONFIG)
if sfvip_player.valid():
    NAME = "sfvip_all"
    VERSION = "1.0"

    pyinstaller_versionfile.create_versionfile(
        output_file=f"{NAME}version.txt",
        version=VERSION,
        company_name="-",
        file_description=NAME,
        internal_name=NAME,
        legal_copyright="-",
        original_filename=f"{NAME}.exe",
        product_name=NAME,
        translations=[0, 1200],
    )

    PyInstaller.__main__.run(
        [
            f"{NAME}.py",
            "--noconfirm",
            "--noconsole",
            "-i",
            rf"{sfvip_player.player},0",
            "--version-file",
            f"{NAME}version.txt",
        ]
    )
    print("create the zip archive")
    shutil.make_archive(NAME, "zip", f"./dist/{NAME}")
