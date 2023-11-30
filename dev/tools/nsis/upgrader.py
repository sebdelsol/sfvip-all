import re
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple, Optional, Self

import requests

from shared.feed import FeedEntries, FeedEntry
from shared.version import Version

from ..utils.color import Ok, Title, Warn


class NSISSetup(NamedTuple):
    version: Version
    url: str

    setup_find = re.compile(r"nsis-([\d\.]+)-setup.exe").findall

    @classmethod
    def from_entry(cls, entry: FeedEntry) -> Optional[Self]:
        if version := NSISSetup.setup_find(entry.title):
            return cls(Version(version[0]), entry.link)
        return None

    def get(self, temp_dir: str, timeout: int) -> Optional[Path]:
        try:
            with requests.get(self.url, timeout=timeout) as response:
                response.raise_for_status()
                setup_exe = Path(temp_dir) / "setup.exe"
                with setup_exe.open("wb") as f:
                    f.write(response.content)
                return setup_exe
        except requests.RequestException:
            pass
        return None


class NSISUpgrader:
    run_as_admin = (
        "&{{$process=Start-Process '{exe}' -ArgumentList '/S' -Verb RunAs -Wait -PassThru;"
        "exit $process.ExitCode}}"
    )
    feed = "https://sourceforge.net/projects/nsis/rss"
    timeout = 10

    def __init__(self, current_version: Version) -> None:
        self.current_version = current_version

    @staticmethod
    def get_latest() -> Optional[NSISSetup]:
        for entry in FeedEntries.get_from_url(NSISUpgrader.feed, NSISUpgrader.timeout):
            if setup := NSISSetup.from_entry(entry):
                return setup
        return None

    @staticmethod
    def execute(setup_exe: Path) -> bool:
        try:
            if setup_exe.is_file():
                exe = str(setup_exe.resolve())
                process = subprocess.run(
                    ("Powershell", NSISUpgrader.run_as_admin.format(exe=exe)),
                    capture_output=True,
                    check=True,
                )
                return not process.stderr
        except subprocess.CalledProcessError:
            pass
        return False

    def upgrade(self) -> bool:
        print(Title("Check"), Ok("NSIS"), end=" ", flush=True)
        if setup := self.get_latest():
            if setup.version > self.current_version:
                print(Ok(f"New {setup.version}"), Title("Get"), end=" ", flush=True)
                with tempfile.TemporaryDirectory() as temp_dir:
                    if setup_exe := setup.get(temp_dir, NSISUpgrader.timeout):
                        print(Title("& Install"), end=" ", flush=True)
                        print(Ok("OK") if self.execute(setup_exe) else Warn("Failed"))
                        return True
            else:
                print(Ok("up-to-date"))
        else:
            print(Warn("Failed"))
        return False
