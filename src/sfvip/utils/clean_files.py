import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CleanFilesIn:
    def __init__(self, path: Path) -> None:
        self._path = path

    @staticmethod
    def _unlink(file: Path) -> bool:
        try:
            file.unlink(missing_ok=True)
            return True
        except PermissionError:
            return False

    def keep(self, keep: int, pattern: str) -> None:
        # remove empty files
        files = self._path.glob(pattern)
        files = [file for file in files if file.stat().st_size or not self._unlink(file)]
        # keep only #keep files
        if len(files) > keep:
            logger.info("keep the last %d '%s' files", keep, pattern)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for file in files[keep:]:
                self._unlink(file)
