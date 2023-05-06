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
    version_txt = str(Path(f"{installer_dir}/{build.name} version.txt").resolve())

    Path(installer_dir).mkdir(parents=True, exist_ok=True)
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
            "--specpath", installer_dir,
            "--clean",
        ]
        # fmt: on
    )

    print("Create the archive")
    zip_name = f"{build.dir}/{build.name} {build.version}"
    zip_format = "zip"
    shutil.make_archive(zip_name, zip_format, f"{installer_dir}/dist/{build.name}")

    # build readme.md & a post
    template_format = dict(
        name=build.name,
        version=build.version,
        github_path=f"{build_config.Github.owner}/{build_config.Github.repo}",
        zip_link=quote(f"{zip_name}.{zip_format}"),
    )

    def template_to_file(src: str, dst: str):
        template = Path(src).read_text(encoding="utf-8")
        Path(dst).write_text(template.format(**template_format), encoding="utf-8")

    template_to_file("readme/README_template.md", "README.md")
    template_to_file("forum/post_template.txt", f"forum/post_{build.version}.txt")
