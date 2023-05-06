import shutil
from pathlib import Path
from urllib.parse import quote

import PyInstaller.__main__
import pyinstaller_versionfile

from build_config import Build, Github


def _get_absolute(path: str) -> str:
    return str(Path(path).resolve())


installer_dir = f"{Build.dir}/installer"
Path(installer_dir).mkdir(parents=True, exist_ok=True)

VERSIONFILE = _get_absolute(f"{installer_dir}/{Build.name} version.txt")
pyinstaller_versionfile.create_versionfile(output_file=VERSIONFILE, version=Build.version)

PyInstaller.__main__.run(
    # fmt: off
    [
        Build.main,
        "--noconfirm",
        "--noconsole",
        "--name", Build.name,
        "--icon", _get_absolute(Build.ico),
        "--version-file", VERSIONFILE,
        "--distpath", f"{installer_dir}/dist",
        "--workpath", f"{installer_dir}/build",
        "--specpath", installer_dir,
        "--clean",
    ]
    # fmt: on
)

print("Create the archive")
archive = f"{Build.dir}/{Build.name} {Build.version}", "zip"
shutil.make_archive(*archive, f"{installer_dir}/dist/{Build.name}")

# create readme.md & a post
template_format = dict(
    name=Build.name,
    version=Build.version,
    github_path=f"{Github.owner}/{Github.repo}",
    archive_link=quote(".".join(archive)),
    ico_link=quote(Build.ico),
)


def template_to_file(src: str, dst: str):
    template = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(template.format(**template_format), encoding="utf-8")


template_to_file("ressources/README_template.md", "README.md")
template_to_file("ressources/post_template.txt", f"{Build.dir}/post {Build.version}.txt")

# cmd = [
#     f'"{sys.executable}"',
#     "-m",
#     "nuitka",
#     "--enable-plugin=tk-inter",
#     "--disable-console",
#     "--standalone",
#     "--onefile",
#     "--follow-imports",
#     f'--windows-icon-from-ico="{Build.ico}"',
#     f'--windows-file-version="{Build.version}"',
#     "-o",
#     f'"{Build.name} {Build.version}.exe"',
#     f'--output-dir="{installer_dir}"',
#     Build.name,
# ]
