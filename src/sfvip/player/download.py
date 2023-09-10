import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.error import ContentTooShortError, HTTPError, URLError

import feedparser
from py7zr import unpack_7zarchive

from src.sfvip.ui import UI

from ..ui import UI, ProgressWindow

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
            self.msg(f"Unpack {archive.name}")
            shutil.unpack_archive(archive, extract_dir=extract_dir, format=archive_format)


class Download:
    _is_64 = sys.maxsize == (2**63) - 1
    _player_bitness = "x64" if _is_64 else "x86"
    _player_update = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{_player_bitness}.zip"
    _libmpv_feed = "https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv"
    _libmpv_bitness = "x86_64-v3" if _is_64 else "i686"
    _libmpv_dev = f"mpv-dev-{_libmpv_bitness}"
    _libmpv_dll_pattern = "libmpv*.dll"
    _exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError

    def __init__(self, player_name: str, ui: UI) -> None:
        current_dir = Path(sys.argv[0]).parent
        self._player_dir = current_dir / f"{player_name.capitalize()} {Download._player_bitness}"
        self._player_exe = self._player_dir / f"{player_name}.exe"
        self._ui = ui

    def _download_libmpv(self, progress: _Progress, temp_dir: Path) -> bool:
        progress.msg("Find lastest libmpv")
        feed = feedparser.parse(Download._libmpv_feed)
        libmpv_urls = (entry.link for entry in feed.entries if Download._libmpv_dev in entry.title)
        if libmpv_url := next(libmpv_urls, None):
            progress.download_and_unpack(libmpv_url, temp_dir / "libmpv", temp_dir)
            dlls = (file for file in temp_dir.glob(Download._libmpv_dll_pattern))
            if dll := next(dlls, None):
                lib = self._player_dir / "lib"
                lib.mkdir(parents=True, exist_ok=True)
                shutil.copy(dll, lib)
                return True
        return False

    def _download_player(self, progress: _Progress, temp_dir: Path) -> bool:
        progress.download_and_unpack(Download._player_update, temp_dir / "player", self._player_dir)
        if self._player_exe.exists():
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
        except Download._exceptions:
            shutil.rmtree(self._player_dir, ignore_errors=True)
        return None
