import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Self

import requests

from shared.feed import FeedEntries
from shared.version import Version

from ..utils.color import Ok, Title, Warn
from ..utils.command import flushed_input
from . import PythonEnv


class PythonVersion(Version):
    feed = "https://github.com/python/cpython/tags.atom"
    timeout = 10

    def __init__(self, version: str | None) -> None:
        super().__init__(version)
        self.major = Version(str(self), 2)

    def new_minor(self) -> Optional[Self]:
        for entry in FeedEntries.get_from_url(PythonVersion.feed, PythonVersion.timeout):
            version = self.__class__(entry.title[1:])
            if version.major == self.major and version > self:
                return version
        return None


class PythonInstaller:
    urls = (
        "https://www.python.org/ftp/python/{version}/python-{version}{bitness}.exe",
        "https://github.com/adang1345/PythonWindows/raw/master/{version}/python-{version}{bitness}-full.exe",
    )
    bitness = {True: "-amd64", False: ""}
    timeout = 10

    def __init__(self, python_env: PythonEnv, version: Version) -> None:
        self.python_env = python_env
        self.version = version
        self.exe = None

    def download(self, temp_dir: str) -> bool:
        bitness = PythonInstaller.bitness[self.python_env.is_64]
        for url in PythonInstaller.urls:
            url = url.format(version=str(self.version), bitness=bitness)
            try:
                with requests.get(url, timeout=PythonInstaller.timeout) as response:
                    response.raise_for_status()
                    self.exe = Path(temp_dir) / "python.exe"
                    with self.exe.open("wb") as f:
                        f.write(response.content)
                    return True
            except requests.RequestException:
                pass
        return False

    def install(self) -> bool:
        try:
            if self.exe and self.exe.is_file():
                args = str(self.exe.resolve()), f"TargetDir={self.python_env.home.resolve()}", "/passive"
                process = subprocess.run(args, capture_output=True, check=True)
                if not process.stderr:
                    return self.python_env.upgrade_python()
        except subprocess.CalledProcessError:
            pass
        return False


def upgrade_python(python_env: PythonEnv) -> None:
    print(Title("Check"), Ok("Python"), end=" ", flush=True)
    if new_minor := PythonVersion(python_env.python_version).new_minor():
        print(Ok(f"New {new_minor}"))
        if flushed_input(Title("> Install : y"), Ok("es ? ")) == "y":
            print(Title("Get"), Ok(f"Python {new_minor}"), end=" ", flush=True)
            installer = PythonInstaller(python_env, new_minor)
            with tempfile.TemporaryDirectory() as temp_dir:
                if installer.download(temp_dir):
                    print(Title("& Install"), end=" ", flush=True)
                    if installer.install():
                        print(Ok("OK"))
                        return
            print(Warn("Failed"))
        else:
            print(Warn("Skip"), Ok(f"Python {new_minor} install"))
    else:
        print(Ok("up-to-date"))
