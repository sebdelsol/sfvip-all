import logging
import tkinter as tk
import zipfile
from pathlib import Path
from typing import Callable, Optional

import py7zr
import py7zr.callbacks
import py7zr.exceptions
import requests

from ..ui.progress import ProgressWindow
from ..ui.thread import ThreadUI

logger = logging.getLogger(__name__)

TPercentFunc = Callable[[float], None]
TUnpackFunc = Callable[[Path, Path, TPercentFunc], None]


def _unpack_7z(archive: Path, extract_dir: Path, set_percent: TPercentFunc) -> None:
    class _ExtractCallback(py7zr.callbacks.ExtractCallback):
        def __init__(self):
            self._extracted_size = 0

        def report_end(self, _, wrote_bytes):
            self._extracted_size += int(wrote_bytes)
            set_percent(100 * self._extracted_size / uncompress_size)

        def report_start_preparation(self):
            pass

        def report_start(self, *_):
            pass

        def report_postprocess(self):
            pass

        def report_warning(self, _):
            pass

    with py7zr.SevenZipFile(archive) as zf:
        uncompress_size: int = zf.archiveinfo().uncompressed  # type: ignore
        zf.extractall(path=extract_dir, callback=_ExtractCallback())


def _unpack_zip(archive: Path, extract_dir: Path, set_percent: TPercentFunc) -> None:
    with zipfile.ZipFile(archive) as zf:
        extracted_size = 0
        uncompress_size = sum((file.file_size for file in zf.infolist()))
        for file in zf.infolist():
            extracted_size += file.file_size
            zf.extract(file, path=extract_dir)
            set_percent(100 * extracted_size / uncompress_size)


_mimeTypes_to_unpack_method = {
    "application/zip": _unpack_zip,
    "application/x-7z-compressed": _unpack_7z,
}


def _download_archive(url: str, archive: Path, set_percent: TPercentFunc) -> Optional[TUnpackFunc]:
    with requests.get(url, stream=True, timeout=3) as response:
        response.raise_for_status()
        mimetype = response.headers.get("Content-Type")
        total_size = int(response.headers.get("Content-Length", 0))
        if mimetype and total_size:
            if unpack_func := _mimeTypes_to_unpack_method.get(mimetype):
                with archive.open("wb") as f:
                    chunk_size = 1024 * 8
                    for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                        set_percent(100 * i * chunk_size / total_size)
                        f.write(chunk)
                return unpack_func
    return None


def download_and_unpack(url: str, archive: Path, extract_dir: Path, progress: ProgressWindow) -> bool:
    progress.msg(f"Download {archive.name}")
    logger.info("download %s", archive.name)
    with progress.show_percent() as set_percent:
        if unpack_func := _download_archive(url, archive, set_percent):
            progress.msg(f"Extract {archive.name}")
            logger.info("extract %s", archive.name)
            unpack_func(archive, extract_dir, set_percent)
            if not progress.destroyed:
                return True
    return False


def download_in_thread(title: str, download_func: Callable[[ProgressWindow], bool], create_mainloop: bool) -> bool:
    exceptions = (
        tk.TclError,
        OSError,
        ValueError,
        FileNotFoundError,
        PermissionError,
        requests.RequestException,
        py7zr.exceptions.ArchiveError,
        zipfile.BadZipFile,
    )
    with ProgressWindow(title, 400, *exceptions) as progress:
        try:
            if ThreadUI(progress, *exceptions, create_mainloop=create_mainloop).start(download_func, progress):
                return True
        except exceptions as err:
            logger.warning("%s %s %s", title, type(err).__name__, err)
    return False
