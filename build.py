import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from build_config import Build, Github

installer_dir = f"{Build.dir}/installer"
nuitka_cmd = [
    f"{sys.executable}",
    "-m",
    "nuitka",
    "--enable-plugin=tk-inter",
    "--disable-console",
    "--standalone",
    "--onefile",
    "--follow-imports",
    f"--windows-icon-from-ico={Build.ico}",
    f"--windows-file-version={Build.version}",
    f"--output-dir={installer_dir}",
    "-o",
    f"{Build.name}.exe",
    Build.main,
]
subprocess.run(nuitka_cmd, check=False)

print("Create the archive")
built_name = f"{Build.dir}/{Build.version}/{Build.name}"
shutil.make_archive(built_name, "zip", f"{installer_dir}/{Build.main[:-3]}.dist")
shutil.copy(f"{installer_dir}/{Build.name}.exe", f"{built_name}.exe")

# create readme.md & a post
template_format = dict(
    name=Build.name,
    version=Build.version,
    github_path=f"{Github.owner}/{Github.repo}",
    archive_link=quote(f"{built_name}.zip"),
    exe_link=quote(f"{built_name}.exe"),
    ico_link=quote(Build.ico),
)


def template_to_file(src: str, dst: str):
    template = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(template.format(**template_format), encoding="utf-8")


template_to_file("ressources/README_template.md", "README.md")
template_to_file("ressources/post_template.txt", f"{Build.dir}/{Build.version}/post.txt")
