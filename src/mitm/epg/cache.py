import logging
import os
import pickle
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator, KeysView, Literal, NamedTuple, Optional, Sequence

from shared.md5 import compute_md5

from ...winapi import mutex
from ..cache_cleaner import CacheCleaner
from .programme import InternalProgramme

logger = logging.getLogger(__name__)
ChannelsT = dict[str, list[InternalProgramme]]
ProgrammesT = Sequence[InternalProgramme]


class NamedProgrammes(NamedTuple):
    programmes: ProgrammesT
    name: str


class FilePosition(NamedTuple):
    seek: int
    length: int


PositionsT = dict[str, list[FilePosition]]


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

    @property
    def number(self) -> int:
        return len(self.positions.keys())

    def get_programmes(self, epg_id: str) -> ProgrammesT:
        if positions := self.positions.get(epg_id):
            try:
                with self.cache_file.open("rb") as f:
                    if f:
                        all_programmes: list[InternalProgramme] = []
                        for position in positions:
                            f.seek(position.seek)
                            pickle_str = f.read(position.length)
                            programmes = pickle.loads(pickle_str)
                            if isinstance(programmes, tuple) and all(
                                isinstance(programme, InternalProgramme) for programme in programmes
                            ):
                                all_programmes.extend(programmes)
                        return all_programmes
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
    def valid_position(position: FilePosition, length: int) -> bool:
        return 0 <= position.seek <= length and 0 <= position.seek + position.length <= length

    @staticmethod
    def length(f: IO[bytes]) -> int:
        f.seek(0, os.SEEK_END)
        return f.tell()


class ChannelsCache:
    chunk_size = 1024

    def __init__(self, roaming: Path) -> None:
        self.roaming = roaming

    def load(self, xml: Path, url: str) -> Optional[ChannelProgrammes]:
        epg = EPGCacheFile(self.roaming, url)
        prg = PRGCacheFile(self.roaming, url)
        with epg.open("rb") as f_epg, prg.open("rb") as f_prg:
            if f_epg and f_prg:
                if positions := self.pickle_load(f_epg, f_prg, xml):
                    return ChannelProgrammes(prg, positions)
        return None

    def save(
        self, xml: Path, url: str, channels: Iterator[Optional[NamedProgrammes]]
    ) -> Optional[ChannelProgrammes]:
        epg = EPGCacheFile(self.roaming, url)
        prg = PRGCacheFile(self.roaming, url)
        with epg.open("wb") as f_epg, prg.open("wb") as f_prg:
            if f_epg and f_prg:
                if positions := self.pickle_dump(f_epg, f_prg, xml, channels):
                    return ChannelProgrammes(prg, positions)
                f_epg.truncate(0)  # clear
                f_prg.truncate(0)  # clear
        return None

    @staticmethod
    def pickle_dump(
        f_epg: IO[bytes], f_prg: IO[bytes], xml: Path, channels: Iterator[Optional[NamedProgrammes]]
    ) -> Optional[PositionsT]:
        try:
            all_positions: PositionsT = {}
            for channel in channels:
                if not channel:
                    return None
                position = ChannelProgrammes.add_programmes(f_prg, channel.programmes)
                all_positions.setdefault(channel.name, []).append(position)
            pickle.dump(compute_md5(xml), f_epg)
            pickle.dump(len(all_positions), f_epg)
            pickle.dump(all_positions, f_epg)
            return all_positions
        except pickle.PickleError:
            return None

    @staticmethod
    def pickle_load(f_epg: IO[bytes], f_prg: IO[bytes], xml: Path) -> Optional[PositionsT]:
        try:
            md5 = pickle.load(f_epg)
            if isinstance(md5, str) and md5 == compute_md5(xml):
                length_prg = ChannelProgrammes.length(f_prg)
                n_all_positions = pickle.load(f_epg)
                all_positions = pickle.load(f_epg)
                if (
                    isinstance(all_positions, dict)
                    and isinstance(n_all_positions, int)
                    and n_all_positions == len(all_positions)
                    and all(
                        isinstance(name, str)
                        and isinstance(position, FilePosition)
                        and ChannelProgrammes.valid_position(position, length_prg)
                        for name, positions in all_positions.items()
                        for position in positions
                    )
                ):
                    return all_positions
            return None
        except (pickle.PickleError, EOFError):
            return None
