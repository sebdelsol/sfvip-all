# pylint: disable=c-extension-no-member
import gzip
import logging
import multiprocessing
import re
import tempfile
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from typing import IO, Callable, Iterator, NamedTuple, Optional, Self
from urllib.parse import urlparse

import lxml.etree as ET
import requests
from thefuzz import fuzz, process

from shared.job_runner import JobRunner

from ..utils import ProgressStep
from .cache import ChannelProgrammes, ChannelsCache, NamedProgrammes, ProgrammesT
from .programme import InternalProgramme

logger = logging.getLogger(__name__)


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


def parse_programme(file_obj: IO[bytes] | gzip.GzipFile, epg_process: EPGProcess) -> Iterator[NamedProgrammes]:
    current_programmes: dict[InternalProgramme, bool] = {}
    current_channel_id: Optional[str] = None
    progress_step = ProgressStep()
    elem: ET.ElementBase
    title: str = ""
    desc: str = ""
    for _, elem in ET.iterparse(
        file_obj,
        events=("end",),
        tag=("channel", "programme", "title", "desc"),
        remove_blank_text=True,
        remove_comments=True,
        remove_pis=True,
    ):
        match elem.tag:
            case "channel":
                if channel_id := elem.get("id", None):
                    progress_step.increment_total(1)
            case "title":  # child of <programme>
                title = elem.text or ""
            case "desc":  # child of <programme>
                desc = elem.text or ""
            case "programme":
                if channel_id := elem.get("channel", None):
                    channel_id = _normalize(channel_id)
                    if channel_id != current_channel_id:
                        if current_channel_id and current_programmes:
                            yield NamedProgrammes(tuple(current_programmes), current_channel_id)
                        current_programmes = {}
                        current_channel_id = channel_id
                        if progress := progress_step.increment_progress(1):
                            epg_process.update_status(EPGProgress(EPGstatus.PROCESSING, progress))
                    start = elem.get("start", "")
                    stop = elem.get("stop", "")
                    programme = InternalProgramme(start=start, stop=stop, title=title, desc=desc)
                    current_programmes[programme] = True
                title = ""
                desc = ""
        elem.clear(False)
    if current_channel_id and current_programmes:
        yield NamedProgrammes(tuple(current_programmes), current_channel_id)


class FoundProgammes(NamedTuple):
    list: ProgrammesT
    confidence: int


class EPGupdate(NamedTuple):
    _chunk_size = 1024 * 128
    url: str
    status: EPGstatus
    programmes: Optional[ChannelProgrammes] = None

    @contextmanager
    @staticmethod
    def _load_xml(url: str, epg_process: EPGProcess, timeout: int) -> Iterator[Optional[Path]]:
        epg_process.update_status(EPGProgress(EPGstatus.LOADING))
        if (xml := Path(url)).is_file():  # for debug purpose
            yield xml
            return
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
    def _process(cls, xml: Path, url: str, epg_process: EPGProcess) -> Iterator[Optional[NamedProgrammes]]:
        stopped = False
        epg_process.update_status(EPGProgress(EPGstatus.PROCESSING))
        with gzip.GzipFile(xml) if url.endswith(".gz") else xml.open("rb") as f:
            for named_programmes in parse_programme(f, epg_process):
                if epg_process.stopping():
                    stopped = True
                    break
                yield named_programmes
        if stopped:
            yield None  # we're sure xml is freed before yielding the stop

    @classmethod
    def _get(
        cls, url: str, cache: ChannelsCache, epg_process: EPGProcess, timeout: int
    ) -> Optional[ChannelProgrammes]:
        try:
            with cls._load_xml(url, epg_process, timeout) as xml:
                if not xml:
                    return None
                epg_process.update_status(EPGProgress(EPGstatus.LOAD_CACHE))
                if programmes := cache.load(xml, url):
                    logger.info("%s Epg channels from '%s' loaded in cache", programmes.number, url)
                    return programmes
                if channels := cls._process(xml, url, epg_process):
                    epg_process.update_status(EPGProgress(EPGstatus.SAVE_CACHE))
                    if programmes := cache.save(xml, url, channels):
                        logger.info("%s Epg channels from '%s' saved in cache", programmes.number, url)
                        return programmes
        except (
            requests.RequestException,
            ConnectionError,
            gzip.BadGzipFile,
            ET.ParseError,
            EOFError,
            BufferError,
        ) as error:
            logger.error("%s: %s", error.__class__.__name__, error)
        return None

    @classmethod
    def from_url(cls, url: str, cache: ChannelsCache, epg_process: EPGProcess, timeout: int) -> Optional[Self]:
        if url:
            if _valid_url(url) or Path(url).is_file():
                logger.info("Load epg channels from '%s'", url)
                if (programmes := cls._get(url, cache, epg_process, timeout)) is not None:
                    epg_process.update_status(EPGProgress(EPGstatus.READY))
                    return cls(url, EPGstatus.READY, programmes)
                epg_process.update_status(EPGProgress(EPGstatus.FAILED))
                return cls(url, EPGstatus.FAILED)
            epg_process.update_status(EPGProgress(EPGstatus.INVALID_URL))
            return cls(url, EPGstatus.INVALID_URL)
        epg_process.update_status(EPGProgress(EPGstatus.NO_EPG))
        return cls(url, EPGstatus.NO_EPG)

    def get_programmes(self, epg_id: str, confidence: int) -> Optional[FoundProgammes]:
        if self.programmes:
            normalized_epg_id = _normalize(epg_id)
            if result := process.extractOne(
                normalized_epg_id,
                self.programmes.all_names,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=100 - confidence,
            ):
                normalized_epg_id, score = result[:2]
                if programmes := self.programmes.get_programmes(normalized_epg_id):
                    logger.info(
                        "Found Epg %s for %s with confidence %s%% (cut off @%s%%)",
                        normalized_epg_id,
                        epg_id,
                        score,
                        100 - confidence,
                    )
                    return FoundProgammes(programmes, int(score))
        return None


class EPGupdater(JobRunner[str]):
    def __init__(self, roaming: Path, update_status: UpdateStatusT, timeout: int) -> None:
        self.epg_process = EPGProcess(update_status, self.stopping)
        self._update_has_failed = multiprocessing.Event()
        self._update_lock = multiprocessing.Lock()
        self._update: Optional[EPGupdate] = None
        self._cache = ChannelsCache(roaming)
        self._timeout = timeout
        super().__init__(self._updating, "Epg updater", check_new=self._check_new)

    def _check_new(self, url: str, last_url: Optional[str]) -> bool:
        with self._update_lock:
            return last_url != url or self._update_has_failed.is_set()

    def _updating(self, url: str) -> None:
        self._update_has_failed.clear()
        if update := EPGupdate.from_url(url, self._cache, self.epg_process, self._timeout):
            with self._update_lock:
                self._update = update
                if update.status == EPGstatus.FAILED:
                    self._update_has_failed.set()
                else:
                    self._update_has_failed.clear()

    @property
    def update(self) -> Optional[EPGupdate]:
        with self._update_lock:
            return self._update
