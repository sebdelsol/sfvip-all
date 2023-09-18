import logging
import shutil
import tkinter as tk
import urllib.request
from pathlib import Path
from typing import Optional

from py7zr import unpack_7zarchive

from ..ui.progress import ProgressWindow

logger = logging.getLogger(__name__)

MimeTypes_to_archive_format = {
    "application/x-tar": "tar",
    "application/zip": "zip",
    "application/x-7z-compressed": "7zip",
}

shutil.register_unpack_format("7zip", [".7z"], unpack_7zarchive)


class Progress(ProgressWindow):
    def _set_progress(self, block_num: int, block_size: int, total_size: int) -> None:
        self.set_percent_progress(100 * block_num * block_size / total_size)

    def _download_archive(self, url: str, path: Path) -> Optional[str]:
        _, headers = urllib.request.urlretrieve(url, path, self._set_progress)
        if mimetype := headers.get("Content-Type"):
            return MimeTypes_to_archive_format.get(mimetype)
        return None

    def download_and_unpack(self, url: str, archive: Path, extract_dir: Path) -> None:
        self.msg(f"Download {archive.name}")
        logger.info("download %s", archive.name)
        if archive_format := self._download_archive(url, archive):
            self.msg(f"Extract {archive.name}")
            logger.info("extract %s", archive.name)
            shutil.unpack_archive(archive, extract_dir=extract_dir, format=archive_format)
            if self._destroyed:  # TODO better ?
                raise tk.TclError()
