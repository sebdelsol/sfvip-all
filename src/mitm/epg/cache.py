import logging
import math
import pickle
from contextlib import contextmanager
from enum import Enum, auto
from itertools import islice
from pathlib import Path
from typing import IO, Callable, Iterator, Literal, NamedTuple, Optional

from shared.md5 import compute_md5

from ...winapi import mutex
from ..cache_cleaner import CacheCleaner
from .programme import InternalProgramme

logger = logging.getLogger(__name__)
ChannelsT = dict[str, list[InternalProgramme]]


class EPGstatus(Enum):
    LOADING = auto()
    LOAD_CACHE = auto()
    SAVE_CACHE = auto()
    PROCESSING = auto()
    READY = auto()
    FAILED = auto()
    NO_EPG = auto()
    INVALID_URL = auto()


class EPGProgress(NamedTuple):
    status: EPGstatus
    progress: Optional[float] = None


UpdateStatusT = Callable[[EPGProgress], None]
StoppingT = Callable[[], bool]


class EPGProcess(NamedTuple):
    update_status: UpdateStatusT
    stopping: StoppingT


class ChannelsCache(CacheCleaner):
    chunk_size = 1024
    suffixes = ("epg",)
    clean_after_days = 5

    def __init__(self, roaming: Path, epg_process: EPGProcess) -> None:
        self.epg_process = epg_process
        super().__init__(roaming)

    def file_path(self, url: str) -> Path:
        for repl in ("://", "/"):
            url = url.replace(repl, ".")
        return self.cache_dir / f"{url}.{ChannelsCache.suffixes[0]}"

    @contextmanager
    def open(self, url: str, mode: Literal["rb", "wb"]) -> Iterator[Optional[IO[bytes]]]:
        path = self.file_path(url)
        with mutex.SystemWideMutex(f"file lock for {path}"):
            try:
                with path.open(mode=mode) as f:
                    yield f
            except (PermissionError, FileNotFoundError, OSError):
                yield None

    def load(self, xml: Path, url: str) -> Optional[ChannelsT]:
        with self.open(url, "rb") as f:
            return self.pickle_load(f, xml) if f else None

    def save(self, xml: Path, url: str, channels: ChannelsT) -> None:
        with self.open(url, "wb") as f:
            if f:
                if not self.pickle_dump(f, xml, channels):
                    f.truncate(0)  # clear

    def pickle_dump(self, f: IO[bytes], xml: Path, channels: ChannelsT) -> bool:
        try:
            self.epg_process.update_status(EPGProgress(EPGstatus.SAVE_CACHE))
            n_chunks = math.ceil(len(channels) / ChannelsCache.chunk_size)
            pickle.dump(compute_md5(xml), f)
            pickle.dump(n_chunks, f)
            it = iter(channels)

            def handle_chunk() -> bool:
                chunk = {k: channels[k] for k in islice(it, ChannelsCache.chunk_size)}
                pickle.dump(chunk, f)
                return True

            if self.handle_chunks(n_chunks, handle_chunk, EPGstatus.SAVE_CACHE):
                return True
        except pickle.PickleError:
            return False
        return False

    def pickle_load(self, f: IO[bytes], xml: Path) -> Optional[ChannelsT]:
        try:
            self.epg_process.update_status(EPGProgress(EPGstatus.LOAD_CACHE))
            md5 = pickle.load(f)
            n_chunks = pickle.load(f)
            if isinstance(md5, str) and md5 == compute_md5(xml) and isinstance(n_chunks, int):
                channels = {}

                def handle_chunk() -> bool:
                    chunk = pickle.load(f)
                    if not isinstance(chunk, dict):
                        return False
                    channels.update(chunk)
                    return True

                if self.handle_chunks(n_chunks, handle_chunk, EPGstatus.LOAD_CACHE):
                    return channels
        except (pickle.PickleError, EOFError):
            return None
        return None

    def handle_chunks(self, n_chunks: int, handle_chunk: Callable[[], bool], status: EPGstatus) -> bool:
        if not n_chunks:
            return False
        for i in range(n_chunks):
            if self.epg_process.stopping():
                return False
            self.epg_process.update_status(EPGProgress(status, i / n_chunks))
            if not handle_chunk():
                return False
        return True
