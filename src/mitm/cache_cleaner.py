import logging
import time
from abc import ABC
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheCleaner(ABC):
    clean_after_days: int
    suffixes: tuple[str, ...]

    def __init__(self, roaming: Path) -> None:
        self.cache_dir = Path(roaming) / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("%s is in '%s'", self.__class__.__name__, self.cache_dir)
        self.clean()

    def clean(self):
        for file in self.cache_dir.iterdir():
            if file.suffix.replace(".", "") in self.suffixes:
                last_accessed_days = (time.time() - file.stat().st_atime) / (3600 * 24)
                if last_accessed_days >= self.clean_after_days:
                    try:
                        file.unlink(missing_ok=True)
                    except PermissionError:
                        logger.warning("Can't remove %s", file)
