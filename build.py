import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from build_config import Build, Github
from sfvip_all_config import DefaultAppConfig

parser = argparse.ArgumentParser()
parser.add_argument("--nobuild", "--readme", action="store_true", help="update readme and post only")
parser.add_argument("--noexe", action="store_true", help="create only a zip (faster)")
parser.add_argument("--clang", action="store_true", help="build with clang")
args = parser.parse_args()

dist_temp = f"{Build.dir}/temp"
dist_name = f"{Build.dir}/{Build.version}/{Build.name}"

if not args.nobuild:
    compiler = "--clang" if args.clang else "--mingw64"  # pylint: disable=invalid-name
    onefile = () if args.noexe else ("--onefile",)  # pylint: disable=invalid-name
    cache_dir = f"%CACHE_DIR%/{Build.name} {Build.version}"
    subprocess.run(
        [
            *(sys.executable, "-m", "nuitka"),  # run nuitka
            f"--include-data-file={Build.splash}={Build.splash}",
            f"--force-stderr-spec={cache_dir}/__ERROR.log",
            f"--force-stdout-spec={cache_dir}/__LOG.log",
            f"--windows-file-version={Build.version}",
            f"--windows-icon-from-ico={Build.ico}",
            f"--onefile-tempdir-spec={cache_dir}",
            f"--output-filename={Build.name}.exe",
            f"--output-dir={dist_temp}",
            "--assume-yes-for-downloads",  # download dependency walker, ccache, and gcc
            "--enable-plugin=tk-inter",  # needed for tkinter
            "--python-flag=-OO",
            "--disable-console",
            "--standalone",
            compiler,
            *onefile,
            Build.main,
        ],
        check=True,
    )
    print(f"Compress {Build.name}.zip")
    shutil.make_archive(dist_name, "zip", f"{dist_temp}/{os.path.splitext(Build.main)[0]}.dist")
    if not args.noexe:
        print(f"Update {Build.name}.exe")
        shutil.copy(f"{dist_temp}/{Build.name}.exe", f"{dist_name}.exe")

print("Create readme & forum post")
template_format = dict(
    inject=" and ".join(f"_{what.capitalize()}_" for what in DefaultAppConfig.all_cat.inject),
    github_path=f"{Github.owner}/{Github.repo}",
    archive_link=quote(f"{dist_name}.zip"),
    exe_link=quote(f"{dist_name}.exe"),
    ico_link=quote(Build.ico),
    version=Build.version,
    name=Build.name,
    all=DefaultAppConfig.all_cat.name,
)


def template_to_file(src: str, dst: str):
    template = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(template.format(**template_format), encoding="utf-8")


template_to_file("ressources/README_template.md", "README.md")
template_to_file("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt")
