import calendar
import logging
import shutil
import tempfile
import time
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import NamedTuple, Optional, Protocol, Self
from urllib.error import ContentTooShortError, HTTPError, URLError

import feedparser

from ...config import ConfigLoader
from .cpu import Cpu
from .progress import Progress

logger = logging.getLogger(__name__)


class FeedEntries(Protocol):
    class _Entry(Protocol):
        title: str
        link: str
        updated_parsed: time.struct_time

    entries: list[_Entry]
    status: int
    bozo: bool


def _version(cpu_spec: Optional[Cpu.Spec], timestamp: Optional[int]) -> str:
    if cpu_spec and timestamp:
        date = datetime.utcfromtimestamp(timestamp).strftime(r"%Y%m%d")
        return f"{LibmpvLatest.cpu_spec_to_str[cpu_spec]}-{date}"
    return ""


class Libmpv(NamedTuple):
    cpu_spec: Cpu.Spec
    timestamp: int
    url: str

    @classmethod
    def from_entry(cls, cpu_spec: Cpu.Spec, entry: FeedEntries._Entry) -> Self:
        return cls(cpu_spec, calendar.timegm(entry.updated_parsed), entry.link)

    def get_version(self):
        return _version(self.cpu_spec, self.timestamp)


class LibmpvVersion(ConfigLoader):
    is64: bool | None = None
    v3: bool | None = None
    timestamp: int | None = None

    def update_from(self, libmpv: Libmpv) -> None:
        self.update_field("is64", libmpv.cpu_spec.is64)
        self.update_field("v3", libmpv.cpu_spec.v3)
        self.update_field("timestamp", libmpv.timestamp)

    def get_cpu_spec(self) -> Optional[Cpu.Spec]:
        return None if self.is64 is None or self.v3 is None else Cpu.Spec(self.is64, self.v3)

    def get_version(self):
        return _version(self.get_cpu_spec(), self.timestamp)


class LibmpvLatest:
    cpu_spec_to_str = {
        Cpu.Spec(is64=True, v3=True): "x86_64-v3",
        Cpu.Spec(is64=True, v3=False): "x86_64",
        Cpu.Spec(is64=False): "i686",
    }
    _feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _name = "libmpv/mpv-dev-{cpu_spec_str}"

    @staticmethod
    def get(player_exe: Path, latest_version: Optional["LibmpvVersion"] = None) -> Optional["Libmpv"]:
        logger.info("check lastest libmpv")
        feed: FeedEntries = feedparser.parse(LibmpvLatest._feed)
        if feed.status in (200, 302) and not feed.bozo and feed.entries:
            cpu_spec = (latest_version and latest_version.get_cpu_spec()) or Cpu.spec(player_exe)
            if cpu_spec:
                cpu_spec_str = LibmpvLatest.cpu_spec_to_str[cpu_spec]
                libmpv_name = LibmpvLatest._name.format(cpu_spec_str=cpu_spec_str)
                libmpvs = (
                    Libmpv.from_entry(cpu_spec, entry) for entry in feed.entries if libmpv_name in entry.title
                )
                if libmpv := next(libmpvs, None):
                    timestamp = (latest_version and latest_version.timestamp) or 0
                    if libmpv.timestamp > timestamp:
                        logger.info("new libmpv found")
                        return libmpv
        logger.info("no new libmpv found")
        return None


class LibmpvDll:
    pattern = "*mpv*.dll"

    def __init__(self, player_exe: Path) -> None:
        self._player_exe = player_exe
        self._libdir = player_exe.parent / "lib"
        self._version = LibmpvVersion(self._libdir / "libmpv.json")

    def get_version(self) -> str:
        self._version.update()
        return self._version.get_version()

    @staticmethod
    def _find_dll_in(path: Path) -> Optional[Path]:
        dlls = (file for file in path.glob(LibmpvDll.pattern))
        return next(dlls, None)

    def download(self, libmpv: Libmpv, progress: Progress) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            archive = temp_dir / "libmpv"
            progress.download_and_unpack(libmpv.url, archive, temp_dir)
            if dll := LibmpvDll._find_dll_in(temp_dir):
                self._libdir.mkdir(parents=True, exist_ok=True)
                shutil.copy(dll, self._libdir)
                logger.info("libmpv dll found")
                self._version.update_from(libmpv)
                return True
            return False

    def check(self) -> Optional[Libmpv]:
        self._version.update()
        return LibmpvLatest.get(self._player_exe, self._version)

    # TODO factorize with update.download_player
    # TODO position progress window next to logo window ?
    def progress_download(self, libmpv: Libmpv) -> bool:
        def run() -> bool:
            return self.download(libmpv, progress)

        exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError
        progress = Progress("Update Libmpv", 400, *exceptions)
        old_dlls = _OldDlls(self._libdir)
        old_dlls.move()
        try:
            if progress.run_in_thread(run, *exceptions, mainloop=False):
                return True
        except exceptions as err:
            logger.warning("libmpv download exception %s", err)
        old_dlls.restore()
        return False


class _OldDlls:
    _pattern = LibmpvDll.pattern

    def __init__(self, libdir: Path) -> None:
        self._libdir = libdir
        self._moved_dlls: list[tuple[Path, Path]] = []

    def move(self) -> None:
        old_dir = self._libdir / "old"
        old_dir.mkdir(parents=True, exist_ok=True)
        for dll in (file for file in self._libdir.glob(_OldDlls._pattern)):
            for i in count(start=1):
                dst = old_dir / f"{dll.name}.{i}"
                if not dst.exists():  # TODO check md5, if equal overwrite
                    shutil.move(dll, dst)
                    self._moved_dlls.append((dll, dst))
                    break

    def restore(self) -> None:
        for dll, dst in self._moved_dlls:
            shutil.move(dst, dll)
        self._moved_dlls = []
