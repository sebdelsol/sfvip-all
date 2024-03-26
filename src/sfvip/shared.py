import json
import logging
import os
from pathlib import Path
from typing import Optional

import psutil

from ..winapi import mutex
from .utils.retry import RetryIfException

logger = logging.getLogger(__name__)


class SharedProxiesToRestore(dict[str, dict[str, str]]):
    """dict of proxies to restore by pid, shared by all instances of the app"""

    def __init__(self, app_roaming: Path) -> None:
        self._path = app_roaming / "ProxiesToRestore.json"
        self._lock = mutex.SystemWideMutex(f"file lock for {self._path}")
        logger.info("Shared proxies to restore is '%s'", self._path)
        super().__init__()

    @RetryIfException(json.JSONDecodeError, PermissionError, FileNotFoundError, TypeError, timeout=1)
    def _load(self) -> None:
        with self._path.open("r", encoding="utf-8") as f:
            self |= json.load(f)

    @RetryIfException(json.JSONDecodeError, PermissionError, timeout=1)
    def _save(self) -> None:
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self, f, indent=2)

    def _clean_pids(self, pid_to_remove: Optional[str]) -> None:
        clean_pids = [pid for pid in self if not psutil.pid_exists(int(pid)) or pid == pid_to_remove]
        for pid in clean_pids:
            del self[pid]

    def _update_file(self, pid_to_remove: Optional[str] = None) -> None:
        with self._lock:
            self._load()
            self._clean_pids(pid_to_remove)
            self._save()

    def add(self, restore: dict[str, str]) -> None:
        self[str(os.getpid())] = restore
        self._update_file()

    @property
    def all(self) -> dict[str, str]:
        """get the flatten dict of proxies to restore"""
        self._update_file()
        return {k: v for restore in self.values() for k, v in restore.items()}

    def clean(self) -> None:
        self._update_file(pid_to_remove=str(os.getpid()))


class SharedEventTime:
    """time of an event shared by all instances of the app"""

    def __init__(self, path: Path, name: str) -> None:
        self._path = path
        self._lock = mutex.SystemWideMutex(f"file lock for {self._path}")
        logger.info("Shared %s event is '%s'", name, self._path)

    def set(self) -> None:
        with self._lock:
            self._path.touch(exist_ok=True)

    @property
    def time(self) -> float:
        with self._lock:
            if not self._path.exists():
                self.set()
            return self._path.stat().st_mtime
