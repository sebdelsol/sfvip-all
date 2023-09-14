import logging
import platform
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple, Optional, Protocol
from urllib.error import ContentTooShortError, HTTPError, URLError

import feedparser
from cpuinfo.cpuinfo import _get_cpu_info_from_cpuid
from py7zr import unpack_7zarchive

from src.sfvip.ui import UI

from ..ui import UI, ProgressWindow

logger = logging.getLogger(__name__)


class Cpu:
    class Spec(NamedTuple):
        is64: bool
        v3: bool = False

    # https://en.wikipedia.org/wiki/X86-64#Microarchitecture_levels
    _x86_64_v3_flags = {"avx", "avx2", "bmi1", "bmi2", "fma", "movbe", "osxsave", "f16c"}
    is64 = platform.machine().endswith("64")

    @staticmethod
    def spec() -> Spec:
        # it takes ~2s to check v3 microarchitecture
        if Cpu.is64 and (cpu_info := _get_cpu_info_from_cpuid()):
            cpu_flags = set(cpu_info.get("flags", []))
            x86_64_v3 = Cpu._x86_64_v3_flags.issubset(cpu_flags)
        else:
            x86_64_v3 = False
        return Cpu.Spec(Cpu.is64, x86_64_v3)


class _Player:
    bitness = "x64" if Cpu.is64 else "x86"
    update_url = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"


class _Libmpv:
    feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _versions = {
        Cpu.Spec(is64=True, v3=True): "x86_64-v3",
        Cpu.Spec(is64=True, v3=False): "x86_64",
        Cpu.Spec(is64=False): "i686",
    }
    _name = "libmpv/mpv-dev-{version}"
    dll = "libmpv*.dll"

    @staticmethod
    def name_from_cpu() -> str:
        # to be done only once, since it takes time to get Cpu.spec()
        version = _Libmpv._versions[Cpu.spec()]
        return _Libmpv._name.format(version=version)


MimeTypes_to_archive_format = {
    "application/x-tar": "tar",
    "application/zip": "zip",
    "application/x-7z-compressed": "7zip",
}


class _Progress(ProgressWindow):
    def __init__(self, ui: UI, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(ui, width, *exceptions)
        self.register_action_with_progress(self.download_archive)
        shutil.register_unpack_format("7zip", [".7z"], unpack_7zarchive)

    def _set_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        self.set_percent_progress(100 * block_num * block_size / total_size)

    def download_archive(self, url: str, path: Path) -> Optional[str]:
        _, headers = urllib.request.urlretrieve(url, path, self._set_progress)
        if mimetype := headers.get("Content-Type"):
            return MimeTypes_to_archive_format.get(mimetype)
        return None

    def download_and_unpack(self, url: str, archive: Path, extract_dir: Path) -> None:
        self.msg(f"Download {archive.name}")
        if archive_format := self.download_archive(url, archive):
            logger.info("%s downloaded", archive.name)
            self.msg(f"Unpack {archive.name}")
            shutil.unpack_archive(archive, extract_dir=extract_dir, format=archive_format)
            logger.info("%s unpacked", archive.name)


class _FeedEntries(Protocol):
    class _Entry(Protocol):
        title: Any
        link: Any

    entries: list[_Entry]
    status: int
    bozo: bool


class Download:
    _exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError

    def __init__(self, player_name: str, ui: UI) -> None:
        current_dir = Path(sys.argv[0]).parent
        self._player_dir = current_dir / f"{player_name.capitalize()} {_Player.bitness}"
        self._player_exe = self._player_dir / f"{player_name}.exe"
        self._ui = ui

    def _download_libmpv(self, progress: _Progress, temp_dir: Path) -> bool:
        progress.msg("Search libmpv")
        feed: _FeedEntries = feedparser.parse(_Libmpv.feed)
        if feed.status in (200, 302) and not feed.bozo and feed.entries:
            libmpv = _Libmpv.name_from_cpu()
            logger.info("search %s", libmpv)
            libmpv_urls = (entry.link for entry in feed.entries if libmpv in entry.title)
            if libmpv_url := next(libmpv_urls, None):
                logger.info("libmpv url found")
                progress.download_and_unpack(libmpv_url, temp_dir / "libmpv", temp_dir)
                dlls = (file for file in temp_dir.glob(_Libmpv.dll))
                if dll := next(dlls, None):
                    lib = self._player_dir / "lib"
                    lib.mkdir(parents=True, exist_ok=True)
                    shutil.copy(dll, lib)
                    logger.info("libmpv dll found")
                    return True
        return False

    def _download_player(self, progress: _Progress, temp_dir: Path) -> bool:
        progress.download_and_unpack(_Player.update_url, temp_dir / "player update", self._player_dir)
        if self._player_exe.exists():
            logger.info("player exe found")
            return True
        return False

    def get(self) -> Optional[str]:
        try:
            with _Progress(self._ui, 300, *Download._exceptions) as progress:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_dir = Path(temp_dir)
                    if self._download_player(progress, temp_dir):
                        if self._download_libmpv(progress, temp_dir):
                            return str(self._player_exe)
        except Download._exceptions as err:
            shutil.rmtree(self._player_dir, ignore_errors=True)
            logger.warning("player download exception %s", err)
        logger.warning("player download aborted")
        return None
