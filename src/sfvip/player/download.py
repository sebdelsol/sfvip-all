import logging
import platform
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Iterator, NamedTuple, Optional, Protocol
from urllib.error import ContentTooShortError, HTTPError, URLError

import feedparser
from cpuinfo.cpuinfo import _get_cpu_info_from_cpuid
from py7zr import unpack_7zarchive

from ..ui.progress import ProgressWindow

logger = logging.getLogger(__name__)


class _Cpu:
    class Spec(NamedTuple):
        is64: bool
        v3: bool = False

    # https://en.wikipedia.org/wiki/X86-64#Microarchitecture_levels
    _x86_64_v3_flags = {"avx", "avx2", "bmi1", "bmi2", "fma", "movbe", "osxsave", "f16c"}
    is64 = platform.machine().endswith("64")

    @staticmethod
    def spec() -> Spec:
        # it takes ~2s to check v3 microarchitecture
        if _Cpu.is64 and (cpu_info := _get_cpu_info_from_cpuid()):
            cpu_flags = set(cpu_info.get("flags", []))
            x86_64_v3 = _Cpu._x86_64_v3_flags.issubset(cpu_flags)
        else:
            x86_64_v3 = False
        return _Cpu.Spec(_Cpu.is64, x86_64_v3)


MimeTypes_to_archive_format = {
    "application/x-tar": "tar",
    "application/zip": "zip",
    "application/x-7z-compressed": "7zip",
}


class _Progress(ProgressWindow):
    def __init__(self, title: str, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(title, width, *exceptions)
        shutil.register_unpack_format("7zip", [".7z"], unpack_7zarchive)

    def _set_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        self.set_percent_progress(100 * block_num * block_size / total_size)

    def _download_archive(self, url: str, path: Path) -> Optional[str]:
        _, headers = urllib.request.urlretrieve(url, path, self._set_progress)
        if mimetype := headers.get("Content-Type"):
            return MimeTypes_to_archive_format.get(mimetype)
        return None

    def download_and_unpack(self, url: str, archive: Path, extract_dir: Path) -> None:
        self.msg(f"Download {archive.name}")
        if archive_format := self._download_archive(url, archive):
            logger.info("%s downloaded", archive.name)
            self.msg(f"Unpack {archive.name}")
            shutil.unpack_archive(archive, extract_dir=extract_dir, format=archive_format)
            logger.info("%s unpacked", archive.name)


class _PlayerUpdate:
    bitness = "x64" if _Cpu.is64 else "x86"
    _url = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"

    @staticmethod
    def download(player_exe: Path, temp_dir: Path, progress: _Progress) -> bool:
        archive = temp_dir / "player update"
        progress.download_and_unpack(_PlayerUpdate._url, archive, player_exe.parent)
        if player_exe.exists():
            logger.info("player exe found")
            return True
        return False


class _FeedEntries(Protocol):
    class _Entry(Protocol):
        title: str
        link: str

    entries: list[_Entry]
    status: int
    bozo: bool


class _Libmpv:
    _feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _versions = {
        _Cpu.Spec(is64=True, v3=True): "x86_64-v3",
        _Cpu.Spec(is64=True, v3=False): "x86_64",
        _Cpu.Spec(is64=False): "i686",
    }
    _name = "libmpv/mpv-dev-{version}"
    _dll = "libmpv*.dll"

    @staticmethod
    def _find_url() -> Optional[str]:
        feed: _FeedEntries = feedparser.parse(_Libmpv._feed)
        if feed.status in (200, 302) and not feed.bozo and feed.entries:
            version = _Libmpv._versions[_Cpu.spec()]
            libmpv = _Libmpv._name.format(version=version)
            logger.info("search %s", libmpv)
            libmpv_urls = (entry.link for entry in feed.entries if libmpv in entry.title)
            return next(libmpv_urls, None)
        return None

    @staticmethod
    def _find_dll_in(path: Path) -> Optional[Path]:
        dlls = (file for file in path.glob(_Libmpv._dll))
        return next(dlls, None)

    @staticmethod
    def download(lib_dir: Path, temp_dir: Path, progress: _Progress) -> bool:
        progress.msg("Search libmpv")
        if libmpv_url := _Libmpv._find_url():
            logger.info("libmpv url found")
            archive = temp_dir / "libmpv"
            progress.download_and_unpack(libmpv_url, archive, temp_dir)
            if dll := _Libmpv._find_dll_in(temp_dir):
                lib_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(dll, lib_dir)
                logger.info("libmpv dll found")
                return True
        return False


def download_player(player_name: str, _) -> Iterator[str]:
    def run() -> Optional[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            player_exe = player_dir / f"{player_name}.exe"
            if _PlayerUpdate.download(player_exe, temp_dir, progress):
                lib_dir = player_dir / "lib"
                if _Libmpv.download(lib_dir, temp_dir, progress):
                    return str(player_exe)
        return None

    exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError
    exe_dir = Path(sys.argv[0]).parent
    player_dir = exe_dir / f"{player_name.capitalize()} {_PlayerUpdate.bitness}"
    progress = _Progress(f"Download {player_dir.name}", 400, *exceptions)
    try:
        yield progress.run_in_thread(run, *exceptions)
    except exceptions as err:
        logger.warning("player download exception %s", err)
    shutil.rmtree(player_dir, ignore_errors=True)
    logger.warning("player download failed")
