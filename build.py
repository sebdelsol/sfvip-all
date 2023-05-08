import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from build_config import Build, Github

nuitka = sys.executable, "-m", "nuitka"
installer_dir = f"{Build.dir}/installer"
subprocess.run(
    [
        *nuitka,
        f"--windows-file-version={Build.version}",
        f"--windows-icon-from-ico={Build.ico}",
        f"--output-filename={Build.name}.exe",
        f"--output-dir={installer_dir}",
        "--assume-yes-for-downloads",  # download dependency walker, ccache, and gcc
        "--enable-plugin=tk-inter",  # needed for tkinter
        "--disable-console",
        "--follow-imports",
        "--standalone",
        "--onefile",
        Build.main,
    ],
    check=True,
)

print("Create archive & exe")
built_name = f"{Build.dir}/{Build.version}/{Build.name}"
shutil.make_archive(built_name, "zip", f"{installer_dir}/{Build.main[:-3]}.dist")
shutil.copy(f"{installer_dir}/{Build.name}.exe", f"{built_name}.exe")

print("Create readme.md & a forum post")
template_format = dict(
    github_path=f"{Github.owner}/{Github.repo}",
    archive_link=quote(f"{built_name}.zip"),
    exe_link=quote(f"{built_name}.exe"),
    ico_link=quote(Build.ico),
    version=Build.version,
    name=Build.name,
)


def template_to_file(src: str, dst: str):
    template = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(template.format(**template_format), encoding="utf-8")


template_to_file("ressources/README_template.md", "README.md")
template_to_file("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt")
