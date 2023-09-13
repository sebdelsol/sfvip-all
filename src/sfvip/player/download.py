import logging
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Optional, Protocol
from urllib.error import ContentTooShortError, HTTPError, URLError

import feedparser
from py7zr import unpack_7zarchive

from src.sfvip.ui import UI

from ..ui import UI, ProgressWindow

# https://en.wikipedia.org/wiki/X86-64#Microarchitecture_levels
X86_64_V3 = True
logger = logging.getLogger(__name__)
shutil.register_unpack_format("7zip", [".7z"], unpack_7zarchive)


MimeTypes_to_archive_format = {
    "application/x-tar": "tar",
    "application/zip": "zip",
    "application/x-7z-compressed": "7zip",
}


class _Progress(ProgressWindow):
    def __init__(self, ui: UI, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(ui, width, *exceptions)
        self.register_action_with_progress(self.download_archive)

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
    _is_64 = sys.maxsize == (2**63) - 1
    _player_bitness = "x64" if _is_64 else "x86"
    _player_update = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{_player_bitness}.zip"
    _libmpv_feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _libmpv_bitness = f"x86_64{'-v3' if X86_64_V3 else ''}" if _is_64 else "i686"
    _libmpv = f"mpv-dev-{_libmpv_bitness}"
    _libmpv_dll = "libmpv*.dll"
    _exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError

    def __init__(self, player_name: str, ui: UI) -> None:
        current_dir = Path(sys.argv[0]).parent
        self._player_dir = current_dir / f"{player_name.capitalize()} {Download._player_bitness}"
        self._player_exe = self._player_dir / f"{player_name}.exe"
        self._ui = ui

    def _download_libmpv(self, progress: _Progress, temp_dir: Path) -> bool:
        feed: _FeedEntries = feedparser.parse(Download._libmpv_feed)
        if feed.status in (200, 302) and not feed.bozo and feed.entries:
            logger.info("search in libmpv feed")
            libmpvs = (entry.link for entry in feed.entries if Download._libmpv in entry.title)
            if libmpv := next(libmpvs, None):
                logger.info("libmpv url found")
                progress.download_and_unpack(libmpv, temp_dir / "libmpv", temp_dir)
                dlls = (file for file in temp_dir.glob(Download._libmpv_dll))
                if dll := next(dlls, None):
                    lib = self._player_dir / "lib"
                    lib.mkdir(parents=True, exist_ok=True)
                    shutil.copy(dll, lib)
                    logger.info("libmpv dll found")
                    return True
        return False

    def _download_player(self, progress: _Progress, temp_dir: Path) -> bool:
        progress.download_and_unpack(Download._player_update, temp_dir / "player update", self._player_dir)
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
