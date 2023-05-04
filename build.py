import shutil
from pathlib import Path
from urllib.parse import quote

import PyInstaller.__main__
import pyinstaller_versionfile

import build_config
from sfvip import Player

# pylint: disable=invalid-name
sfvip_player = Player()
if sfvip_player.valid():
    build = build_config.Build
    installer_dir = f"{build.dir}/installer"
    Path(installer_dir).mkdir(parents=True, exist_ok=True)
    version_txt = str(Path(f"{installer_dir}/{build.name} version.txt").resolve())

    pyinstaller_versionfile.create_versionfile(
        output_file=version_txt,
        version=build.version,
        file_description=build.name,
        internal_name=build.name,
        original_filename=f"{build.name}.exe",
        product_name=build.name,
        translations=[0, 1200],
    )

    PyInstaller.__main__.run(
        # fmt: off
        [
            build.main,
            "--noconfirm",
            "--noconsole",
            "--name", build.name,
            "--icon", rf"{sfvip_player.player_path},0",
            "--version-file", version_txt,
            "--distpath", f"{installer_dir}/dist",
            "--workpath", f"{installer_dir}/build",
            "--specpath", installer_dir
        ]
        # fmt: on
    )

    print("Create the archive")
    zip_name = f"{build.dir}/{build.name} {build.version}"
    zip_type = "zip"
    shutil.make_archive(zip_name, zip_type, f"{installer_dir}/dist")

    print("Update README.md")
    readme_template = Path("readme/README_template.md").read_text(encoding="utf-8")
    github = build_config.Github
    github_path = f"{github.owner}/{github.repo}"
    readme_txt = readme_template.format(
        name=build.name,
        version=build.version,
        github_path=github_path,
        zip=quote(f"{zip_name}.{zip_type}"),
    )
    Path("README.md").write_text(readme_txt, encoding="utf-8")
