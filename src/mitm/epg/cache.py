import logging
import math
import os
import pickle
from contextlib import contextmanager
from enum import Enum, auto
from itertools import islice
from pathlib import Path
from typing import IO, Callable, Iterator, KeysView, Literal, NamedTuple, Optional

from shared.md5 import compute_md5

from ...winapi import mutex
from ..cache_cleaner import CacheCleaner
from .programme import InternalProgramme

logger = logging.getLogger(__name__)
ChannelsT = dict[str, list[InternalProgramme]]
ProgrammesT = tuple[InternalProgramme, ...]


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


class FilePosition(NamedTuple):
    seek: int
    length: int


PositionsT = dict[str, FilePosition]


class CacheFile(CacheCleaner):
    clean_after_days = 5
    suffix = ""

    def __init__(self, roaming: Path, url: str) -> None:
        super().__init__(roaming, CacheFile.clean_after_days, self.suffix)
        self.roaming = roaming
        for repl in ("://", "/"):
            url = url.replace(repl, ".")
        self.path = self.cache_dir / f"{url}.{self.suffix}"
        self.mutex = mutex.SystemWideMutex(f"file lock for {self.path}")

    @contextmanager
    def open(self, mode: Literal["rb", "wb"]) -> Iterator[Optional[IO[bytes]]]:
        with self.mutex:
            try:
                with self.path.open(mode=mode) as f:
                    yield f
            except (PermissionError, FileNotFoundError, OSError):
                yield None


class EPGCacheFile(CacheFile):
    suffix = "epg"


class PRGCacheFile(CacheFile):
    suffix = "prg"


class ChannelProgrammes:
    def __init__(self, cache_file: CacheFile, positions: PositionsT) -> None:
        self.cache_file = cache_file
        self.positions: PositionsT = positions

    @property
    def all_names(self) -> KeysView[str]:
        return self.positions.keys()

    def get_programmes(self, epg_id: str) -> ProgrammesT:
        if position := self.positions.get(epg_id):
            try:
                with self.cache_file.open("rb") as f:
                    if f:
                        f.seek(position.seek)
                        pickle_str = f.read(position.length)
                        programmes = pickle.loads(pickle_str)
                        if isinstance(programmes, tuple) and all(
                            isinstance(programme, InternalProgramme) for programme in programmes
                        ):
                            return programmes
            except (pickle.PickleError, EOFError, OverflowError, ValueError):
                pass
        return ()

    @staticmethod
    def add_programmes(f: IO[bytes], programmes: ProgrammesT) -> FilePosition:
        seek = f.tell()
        pickle.dump(programmes, f)
        length = f.tell() - seek
        return FilePosition(seek, length)

    @staticmethod
    def is_valid_position(position: FilePosition, length: int) -> bool:
        return 0 <= position.seek <= length and 0 <= position.seek + position.length <= length

    @staticmethod
    def length(f: IO[bytes]) -> int:
        f.seek(0, os.SEEK_END)
        return f.tell()


class ChannelsCache:
    chunk_size = 1024

    def __init__(self, roaming: Path, epg_process: EPGProcess) -> None:
        self.roaming = roaming
        self.epg_process = epg_process

    def load(self, xml: Path, url: str) -> Optional[ChannelProgrammes]:
        epg = EPGCacheFile(self.roaming, url)
        prg = PRGCacheFile(self.roaming, url)
        with epg.open("rb") as f_epg, prg.open("rb") as f_prg:
            if f_epg and f_prg:
                if positions := self.pickle_load(f_epg, f_prg, xml):
                    return ChannelProgrammes(prg, positions)
        return None

    def save(self, xml: Path, url: str, channels: ChannelsT) -> Optional[ChannelProgrammes]:
        epg = EPGCacheFile(self.roaming, url)
        prg = PRGCacheFile(self.roaming, url)
        with epg.open("wb") as f_epg, prg.open("wb") as f_prg:
            if f_epg and f_prg:
                if positions := self.pickle_dump(f_epg, f_prg, xml, channels):
                    return ChannelProgrammes(prg, positions)
                f_epg.truncate(0)  # clear
                f_prg.truncate(0)  # clear
        return None

    def pickle_dump(
        self, f_epg: IO[bytes], f_prg: IO[bytes], xml: Path, channels: ChannelsT
    ) -> Optional[PositionsT]:
        try:
            self.epg_process.update_status(EPGProgress(EPGstatus.SAVE_CACHE))
            n_chunks = math.ceil(len(channels) / ChannelsCache.chunk_size)
            pickle.dump(compute_md5(xml), f_epg)
            pickle.dump(n_chunks, f_epg)
            visited: dict[ProgrammesT, FilePosition] = {}
            positions: PositionsT = {}
            channels_iterator = iter(channels)

            def handle_chunk() -> bool:
                chunk: dict[str, FilePosition] = {}
                for name in islice(channels_iterator, ChannelsCache.chunk_size):
                    programmes = tuple(channels[name])
                    if not (position := visited.get(programmes)):
                        position = ChannelProgrammes.add_programmes(f_prg, programmes)
                    chunk[name] = visited[programmes] = position
                pickle.dump(chunk, f_epg)
                positions.update(chunk)
                return True

            if self.handle_chunks(n_chunks, handle_chunk, EPGstatus.SAVE_CACHE):
                return positions
        except pickle.PickleError:
            return None
        return None

    def pickle_load(self, f_epg: IO[bytes], f_prg: IO[bytes], xml: Path) -> Optional[PositionsT]:
        try:
            self.epg_process.update_status(EPGProgress(EPGstatus.LOAD_CACHE))
            md5 = pickle.load(f_epg)
            n_chunks = pickle.load(f_epg)
            if isinstance(md5, str) and md5 == compute_md5(xml) and isinstance(n_chunks, int):
                positions: dict[str, FilePosition] = {}
                length_prg = ChannelProgrammes.length(f_prg)

                def handle_chunk() -> bool:
                    chunk = pickle.load(f_epg)
                    if not isinstance(chunk, dict) or not all(
                        isinstance(name, str)
                        and isinstance(position, FilePosition)
                        and ChannelProgrammes.is_valid_position(position, length_prg)
                        for name, position in chunk.items()
                    ):
                        return False
                    positions.update(chunk)
                    return True

                if self.handle_chunks(n_chunks, handle_chunk, EPGstatus.LOAD_CACHE):
                    return positions
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
