import calendar
import filecmp
import logging
import shutil
import tempfile
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import NamedTuple, Optional, Self

from shared.feed import FeedEntries, FeedEntry
from translations.loc import LOC

from ...config_loader import ConfigLoader
from ..ui.window import AskWindow, ProgressWindow
from ..utils.downloader import download_and_unpack, exceptions
from .cpu import Cpu

logger = logging.getLogger(__name__)


class Libmpv(NamedTuple):
    cpu_spec: Cpu.Spec
    timestamp: int
    url: str

    @classmethod
    def from_entry(cls, cpu_spec: Cpu.Spec, entry: FeedEntry) -> Self:
        return cls(cpu_spec, calendar.timegm(entry.updated_parsed), entry.link)

    def get_version(self) -> Optional[str]:
        return _LibmpvLatest.version(self.cpu_spec, self.timestamp)


class LibmpvVersion(ConfigLoader):
    is64: bool | None = None
    v3: bool | None = None
    timestamp: int | None = None

    def _get_cpu_spec(self) -> Optional[Cpu.Spec]:
        return None if self.is64 is None or self.v3 is None else Cpu.Spec(self.is64, self.v3)

    def update_cpu_spec(self, player_exe: Path) -> Optional[Cpu.Spec]:
        cpu_spec = self._get_cpu_spec() or Cpu.spec(player_exe)
        if cpu_spec is None or self.is64 != cpu_spec.is64 or self.v3 != cpu_spec.v3:
            self.timestamp = None
        if cpu_spec:
            self.is64 = cpu_spec.is64
            self.v3 = cpu_spec.v3
        return cpu_spec

    def update_from(self, libmpv: Libmpv) -> None:
        self.is64 = libmpv.cpu_spec.is64
        self.v3 = libmpv.cpu_spec.v3
        self.timestamp = libmpv.timestamp

    def get_version(self) -> Optional[str]:
        return _LibmpvLatest.version(self._get_cpu_spec(), self.timestamp)


class _LibmpvLatest:
    _cpu_spec_to_str = {
        Cpu.Spec(is64=True, v3=True): "x86_64-v3",
        Cpu.Spec(is64=True, v3=False): "x86_64",
        Cpu.Spec(is64=False): "i686",
    }
    _feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _name = "libmpv/mpv-dev-{cpu_spec_str}"

    def __init__(self, timeout: int) -> None:
        self._timeout = timeout

    @staticmethod
    def version(cpu_spec: Optional[Cpu.Spec], timestamp: Optional[int]) -> Optional[str]:
        if cpu_spec and timestamp:
            date = datetime.utcfromtimestamp(timestamp).strftime(r"%Y%m%d")
            return f"{_LibmpvLatest._cpu_spec_to_str[cpu_spec]}-{date}"
        return None

    def get(self, cpu_spec: Cpu.Spec) -> Optional[Libmpv]:
        if feed_entries := FeedEntries.get_from_url(_LibmpvLatest._feed, self._timeout):
            cpu_spec_str = _LibmpvLatest._cpu_spec_to_str[cpu_spec]
            name = _LibmpvLatest._name.format(cpu_spec_str=cpu_spec_str)
            libmpvs = (Libmpv.from_entry(cpu_spec, entry) for entry in feed_entries if name in entry.title)
            if libmpv := next(libmpvs, None):
                return libmpv
        return None


class LibmpvDll:
    pattern = "*mpv*.dll"

    def __init__(self, player_exe: Path, timeout: int) -> None:
        self._timeout = timeout
        self._player_exe = player_exe
        self._libdir = player_exe.parent / "lib"
        self._libmpv_latest = _LibmpvLatest(timeout)
        self._version = LibmpvVersion(self._libdir / "libmpv.json").update()

    def get_version(self) -> Optional[str]:
        return self._version.get_version()

    def is_new(self, libmpv: Libmpv) -> bool:
        return libmpv.timestamp > (self._version.timestamp or 0)

    def get_latest_libmpv(self) -> Optional[Libmpv]:
        logger.info("get lastest libmpv")
        if cpu_spec := self._version.update_cpu_spec(self._player_exe):
            if libmpv := self._libmpv_latest.get(cpu_spec):
                logger.info("found update libmpv %s", libmpv.get_version())
                return libmpv
        logger.warning("get latest libmpv failed")
        return None

    def _download(self, libmpv: Libmpv, progress: ProgressWindow) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            archive = temp_dir / "libmpv"
            if download_and_unpack(libmpv.url, archive, temp_dir, self._timeout, progress):
                dlls = (file for file in temp_dir.glob(LibmpvDll.pattern))
                if dll := next(dlls, None):
                    self._libdir.mkdir(parents=True, exist_ok=True)
                    shutil.copy(dll, self._libdir)
                    logger.info("libmpv dll found")
                    self._version.update_from(libmpv)
                    return True
            return False

    def download_latest(self, progress: ProgressWindow) -> bool:
        progress.msg(LOC.CheckLastestLibmpv)
        if libmpv := self.get_latest_libmpv():
            return self._download(libmpv, progress)
        return False

    def download(self, libmpv: Libmpv) -> bool:
        def _download() -> bool:
            return self._download(libmpv, progress)

        old_dlls = _OldDlls(self._libdir)
        old_dlls.move()
        progress = ProgressWindow(f"{LOC.Update} Libmpv")
        if progress.run_in_thread(_download, *exceptions):
            return True
        old_dlls.restore()
        return False

    @staticmethod
    def ask_restart() -> bool:
        def _ask_restart() -> bool:
            ask_win.wait_window()
            return bool(ask_win.ok)

        ask_win = AskWindow(f"{LOC.Install} Libmpv", LOC.RestartInstall % "Libmpv", LOC.Restart, LOC.Cancel)
        return bool(ask_win.run_in_thread(_ask_restart, *exceptions))


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
                if not dst.exists() or filecmp.cmp(dll, dst):
                    shutil.move(dll, dst)
                    self._moved_dlls.append((dll, dst))
                    break

    def restore(self) -> None:
        for dll, dst in self._moved_dlls:
            shutil.move(dst, dll)
        self._moved_dlls = []
