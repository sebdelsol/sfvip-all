import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from build_config import Build, Github

# pylint: disable=invalid-name
parser = argparse.ArgumentParser()
parser.add_argument("--nobuild", "--readme", action="store_true", help="update readme and post only")
parser.add_argument("--noexe", action="store_true", help="create only a zip (faster)")
parser.add_argument("--clang", action="store_true", help="build with clang")
args = parser.parse_args()

dist_temp = f"{Build.dir}/temp"
dist_name = f"{Build.dir}/{Build.version}/{Build.name}"

if not args.nobuild:
    compiler = "--clang" if args.clang else "--mingw64"
    onefile = () if args.noexe else ("--onefile",)
    # need a development version of Nuitka because of https://github.com/Nuitka/Nuitka/issues/2234
    subprocess.run(
        [
            *(sys.executable, "-m", "nuitka"),  # run nuitka
            f"--force-stderr-spec=%PROGRAM%/../{Build.name} - %TIME%.log",
            f"--include-data-file={Build.splash}={Build.splash}",
            f"--onefile-tempdir-spec=%CACHE_DIR%/{Build.name}",
            f"--windows-file-version={Build.version}",
            f"--windows-icon-from-ico={Build.ico}",
            f"--output-filename={Build.name}.exe",
            f"--output-dir={dist_temp}",
            "--assume-yes-for-downloads",
            # needed for tkinter
            "--enable-plugin=tk-inter",
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
get_py_files = "git ls-files -- '*.py'"
count_non_blank_lines = "%{ ((Get-Content -Path $_) -notmatch '^\\s*$').Length }"
loc = subprocess.run(
    [
        "powershell",
        f"({get_py_files} | {count_non_blank_lines} | measure -Sum).Sum",
    ],
    text=True,
    check=False,
    capture_output=True,
)

template_format = dict(
    github_path=f"{Github.owner}/{Github.repo}",
    archive_link=quote(f"{dist_name}.zip"),
    exe_link=quote(f"{dist_name}.exe"),
    ico_link=quote(Build.ico),
    version=Build.version,
    loc=int(loc.stdout),
    name=Build.name,
)


def template_to_file(src: str, dst: str | Path, **kwargs: str) -> None:
    template = Path(src).read_text(encoding="utf-8")
    _template_format = template_format | kwargs
    Path(dst).write_text(template.format(**_template_format), encoding="utf-8")


template_to_file("ressources/README_template.md", "README.md")
template_to_file("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt")

# print("create redirection for older versions")
# for file in Path(Build.dir).rglob("*.[ze][ix][pe]"):
#     if Path(dist_temp) not in file.parents:
#         if not (".actual" in file.stem or Build.version in str(file.parent)):
#             actual = file.with_stem(f"{file.stem}.actual")
#             if not actual.exists():
#                 shutil.copy(file, actual)
#             version = re.findall(r"(\d+(\.\d+)*)", str(file))
#             if version:
#                 print(file, version)
#                 template_to_file(
#                     "ressources/redirection_template.md",
#                     file,
#                     actual_type=actual.suffix[1:].capitalize(),
#                     actual_version=version[0][0],
#                     actual_file=str(actual.parent).replace("\\", "/") + quote(actual.name),
#                 )
