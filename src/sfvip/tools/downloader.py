import logging
import tkinter as tk
import zipfile
from pathlib import Path
from typing import Callable, Optional

import py7zr
import py7zr.callbacks
import py7zr.exceptions
import requests

from ..localization import LOC
from ..ui.window import ProgressWindow

logger = logging.getLogger(__name__)

TPercentFunc = Callable[[float], None]
TUnpackFunc = Callable[[Path, Path, TPercentFunc], None]
exceptions = (
    tk.TclError,
    OSError,
    ValueError,
    FileNotFoundError,
    FileExistsError,
    PermissionError,
    requests.RequestException,
    py7zr.exceptions.ArchiveError,
    zipfile.BadZipFile,
)


def _unpack_7z(archive: Path, extract_dir: Path, set_percent: TPercentFunc) -> None:
    class _ExtractCallback(py7zr.callbacks.ExtractCallback):
        def __init__(self) -> None:
            self.extracted_size = 0
            self.failed = False

        def report_end(self, _, wrote_bytes) -> None:
            self.extracted_size += int(wrote_bytes)
            try:
                set_percent(100 * self.extracted_size / uncompress_size)
            except tk.TclError:
                self.failed = True

        def report_start_preparation(self) -> None:
            pass

        def report_start(self, *_) -> None:
            pass

        def report_postprocess(self) -> None:
            pass

        def report_warning(self, _) -> None:
            pass

    with py7zr.SevenZipFile(archive) as zf:
        uncompress_size: int = zf.archiveinfo().uncompressed  # type: ignore
        callback = _ExtractCallback()
        zf.extractall(path=extract_dir, callback=callback)
    if callback.failed:
        raise py7zr.exceptions.ArchiveError("progress failed")


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


def _download(url: str, path: Path, timeout: int, set_percent: TPercentFunc) -> Optional[requests.Response]:
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        if total_size := int(response.headers.get("Content-Length", 0)):
            with path.open("wb") as f:
                chunk_size = 1024 * 128
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    set_percent(100 * i * chunk_size / total_size)
                    f.write(chunk)
            return response
    return None


def download_and_unpack(
    url: str, archive: Path, extract_dir: Path, timeout: int, progress: ProgressWindow
) -> bool:
    progress.msg(f"{LOC.Download} {archive.name}")
    logger.info("download %s", archive.name)
    with progress.show_percent() as set_percent:
        if response := _download(url, archive, timeout, set_percent):
            if mimetype := response.headers.get("Content-Type"):
                if unpack_func := _mimeTypes_to_unpack_method.get(mimetype):
                    progress.msg(f"{LOC.Extract} {archive.name}")
                    logger.info("extract %s", archive.name)
                    unpack_func(archive, extract_dir, set_percent)
                    if not progress.destroyed:
                        return True
    return False


def download_to(url: str, path: Path, timeout: int, progress: ProgressWindow) -> bool:
    progress.msg(f"{LOC.Download} {path.name}")
    logger.info("download %s", path.name)
    with progress.show_percent() as set_percent:
        if _download(url, path, timeout, set_percent):
            if not progress.destroyed:
                return True
    return False
