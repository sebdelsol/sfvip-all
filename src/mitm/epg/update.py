# pylint: disable=c-extension-no-member
import gzip
import logging
import multiprocessing
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Callable, Iterator, NamedTuple, Optional, Self
from urllib.parse import urlparse

import lxml.etree as ET
import requests
from thefuzz import fuzz, process

from shared.job_runner import JobRunner

from ..utils import ProgressStep
from .cache import (
    ChannelsCache,
    ChannelsT,
    EPGProcess,
    EPGProgress,
    EPGstatus,
    UpdateStatusT,
)
from .programme import InternalProgramme

logger = logging.getLogger(__name__)


def _normalize(name: str) -> str:
    name = re.sub(r"(\.)([\d]+)", r"\2", name)  # turn channel.2 into channel2
    for sub, repl in (".+", "plus"), ("+", "plus"), ("*", "star"):
        name = name.replace(sub, repl)
    return name


def _valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc and result.scheme in ("http", "https"))
    except ValueError:
        return False


def parse_programme(
    file_obj: IO[bytes] | gzip.GzipFile,
    handle_channel: Callable[[str, str], None],
    handle_programme: Callable[[str, InternalProgramme], None],
) -> Iterator[None]:
    display_name: Optional[str] = None
    elem: ET.ElementBase
    title: str = ""
    desc: str = ""
    for _, elem in ET.iterparse(
        file_obj,
        events=("end",),
        tag=("channel", "display-name", "programme", "title", "desc"),
        remove_blank_text=True,
        remove_comments=True,
        remove_pis=True,
    ):
        match elem.tag:
            case "display-name":  # child of <channel>
                display_name = elem.text
            case "channel":
                if display_name and (channel_id := elem.get("id", None)):
                    handle_channel(channel_id, display_name)
                display_name = None
            case "title":  # child of <programme>
                title = elem.text or ""
            case "desc":  # child of <programme>
                desc = elem.text or ""
            case "programme":
                if channel_id := elem.get("channel", None):
                    handle_programme(
                        channel_id,
                        InternalProgramme(
                            start=elem.get("start", ""),
                            stop=elem.get("stop", ""),
                            title=title or "",
                            desc=desc or "",
                        ),
                    )
                title = ""
                desc = ""
        elem.clear(False)
        yield


class FoundProgammes(NamedTuple):
    list: list[InternalProgramme]
    confidence: int


class EPGupdate(NamedTuple):
    _chunk_size = 1024 * 128
    url: str
    status: EPGstatus
    channels: ChannelsT = {}

    @contextmanager
    @staticmethod
    def _load_xml(url: str, epg_process: EPGProcess, timeout: int) -> Iterator[Optional[Path]]:
        epg_process.update_status(EPGProgress(EPGstatus.LOADING))
        with tempfile.TemporaryDirectory() as temp_dir:
            with requests.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                xml = Path(temp_dir) / "xml"
                with xml.open(mode="wb") as f:
                    total_size = int(response.headers.get("Content-Length", 0))
                    progress_step = ProgressStep(total=total_size) if total_size else None
                    for i, chunk in enumerate(response.iter_content(chunk_size=EPGupdate._chunk_size)):
                        if epg_process.stopping():
                            yield None
                            return
                        if progress_step and (progress := progress_step.progress(i * EPGupdate._chunk_size)):
                            epg_process.update_status(EPGProgress(EPGstatus.LOADING, progress))
                        f.write(chunk)
                yield xml

    @classmethod
    def _process(cls, xml: Path, url: str, epg_process: EPGProcess) -> Optional[ChannelsT]:
        epg_process.update_status(EPGProgress(EPGstatus.PROCESSING))
        with gzip.GzipFile(xml) if url.endswith(".gz") else xml.open("rb") as f:
            channels: ChannelsT = {}
            display_names: dict[str, str] = {}
            normalized: dict[str, str] = {}
            progress_step = ProgressStep()

            def handle_channel(channel_id: str, display_name: str) -> None:
                progress_step.increment_total(1)
                display_names[channel_id] = display_name

            def handle_programme(channel_id: str, programme: InternalProgramme) -> None:
                if channel_id not in normalized:
                    normalized[channel_id] = _normalize(channel_id)
                channel = normalized[channel_id]
                if channel not in channels:
                    channels[channel] = []
                    if display_name := display_names.get(channel_id):
                        if display_name not in channels:
                            channels[_normalize(display_name)] = channels[channel]
                    if progress := progress_step.increment_progress(1):
                        epg_process.update_status(EPGProgress(EPGstatus.PROCESSING, progress))
                channels[channel].append(programme)

            for _ in parse_programme(f, handle_channel, handle_programme):
                if epg_process.stopping():
                    return None
            logger.info("%s Epg channels found from '%s'", progress_step.total, url)
            return channels

    @classmethod
    def _get(cls, url: str, cache: ChannelsCache, epg_process: EPGProcess, timeout: int) -> Optional[ChannelsT]:
        try:
            if Path(url).is_file():  # for debug purpose
                return cls._process(Path(url), url, epg_process)
            with cls._load_xml(url, epg_process, timeout) as xml:
                if not xml:
                    return None
                epg_process.update_status(EPGProgress(EPGstatus.LOAD_CACHE))
                if channels := cache.load(xml, url):
                    logger.info("Epg channels from '%s' found in cache", url)
                    return channels
                if channels := cls._process(xml, url, epg_process):
                    epg_process.update_status(EPGProgress(EPGstatus.SAVE_CACHE))
                    cache.save(xml, url, channels)
                    return channels
        except (requests.RequestException, gzip.BadGzipFile, ET.ParseError, EOFError, BufferError) as error:
            logger.error("%s: %s", error.__class__.__name__, error)
        return None

    @classmethod
    def from_url(cls, url: str, cache: ChannelsCache, epg_process: EPGProcess, timeout: int) -> Optional[Self]:
        if url:
            if _valid_url(url) or Path(url).is_file():
                logger.info("Load epg channels from '%s'", url)
                if (channels := cls._get(url, cache, epg_process, timeout)) is not None:
                    epg_process.update_status(EPGProgress(EPGstatus.READY))
                    return cls(url, EPGstatus.READY, channels)
                epg_process.update_status(EPGProgress(EPGstatus.FAILED))
                return cls(url, EPGstatus.FAILED)
            epg_process.update_status(EPGProgress(EPGstatus.INVALID_URL))
            return cls(url, EPGstatus.INVALID_URL)
        epg_process.update_status(EPGProgress(EPGstatus.NO_EPG))
        return cls(url, EPGstatus.NO_EPG)

    def get_programmes(self, epg_id: str, confidence: int) -> Optional[FoundProgammes]:
        if self.channels:
            normalized_epg_id = _normalize(epg_id)
            if result := process.extractOne(
                normalized_epg_id,
                self.channels.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=100 - confidence,
            ):
                normalized_epg_id, score = result[:2]
                logger.info(
                    "Found Epg %s for %s with confidence %s%% (cut off @%s%%)",
                    normalized_epg_id,
                    epg_id,
                    score,
                    100 - confidence,
                )
                if programmes := self.channels.get(normalized_epg_id):
                    return FoundProgammes(programmes, int(score))
        return None


class EPGupdater(JobRunner[str]):
    def __init__(self, roaming: Path, update_status: UpdateStatusT, timeout: int) -> None:
        self.epg_process = EPGProcess(update_status, self.stopping)
        self._cache = ChannelsCache(roaming, self.epg_process)
        self._update_lock = multiprocessing.Lock()
        self._update: Optional[EPGupdate] = None
        self._timeout = timeout
        super().__init__(self._updating, "Epg updater", check_new=False)

    def _updating(self, url: str) -> None:
        with self._update_lock:
            current_update = self._update
        # update only if url is different or last update failed
        if not current_update or current_update.url != url or current_update.status == EPGstatus.FAILED:
            if update := EPGupdate.from_url(url, self._cache, self.epg_process, self._timeout):
                with self._update_lock:
                    self._update = update

    @property
    def update(self) -> Optional[EPGupdate]:
        with self._update_lock:
            return self._update
