# pylint: disable=c-extension-no-member
import gzip
import logging
import multiprocessing
import re
import tempfile
from contextlib import contextmanager
from enum import Enum, auto, member
from pathlib import Path
from typing import (
    IO,
    Callable,
    Container,
    Iterator,
    NamedTuple,
    Optional,
    Self,
)
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
    for sub, repl in ("+", "plus"), ("*", "star"):
        name = name.replace(sub, repl)
    for char in ".|()[]-":
        name = name.replace(char, " ")
    name = re.sub(r"\s+", " ", name).strip()  # remove extra white spaces
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
    normalized: dict[str, str] = {}
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
                    if not (norm_channel_id := normalized.get(channel_id)):
                        norm_channel_id = normalized[channel_id] = _normalize(channel_id)
                    if norm_channel_id != current_channel_id:
                        if current_channel_id and current_programmes:
                            yield NamedProgrammes(tuple(current_programmes), current_channel_id)
                        current_programmes = {}
                        current_channel_id = norm_channel_id
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


class FuzzResult(NamedTuple):
    name: str
    score: float

    @classmethod
    def from_result(cls, result: tuple) -> Self:
        return cls(*result[:2])


class Scorer(Enum):
    RATIO = member(fuzz.ratio)
    PARTIAL_RATIO = member(fuzz.partial_ratio)
    TOKEN_SET_RATIO = member(fuzz.token_set_ratio)
    TOKEN_SORT_RATIO = member(fuzz.token_sort_ratio)
    PARTIAL_TOKEN_SET_RATIO = member(fuzz.partial_token_set_ratio)
    PARTIAL_TOKEN_SORT_RATIO = member(fuzz.partial_token_sort_ratio)


class FuzzBest:
    _scorers = (
        # used for cuttoff and overall score
        (Scorer.TOKEN_SET_RATIO, 0.5),
        # used overal score
        (Scorer.TOKEN_SORT_RATIO, 1),
        (Scorer.PARTIAL_TOKEN_SORT_RATIO, 0.5),
        (Scorer.RATIO, 1),
    )
    _limit = 5

    def __init__(self, choices: Container[str]) -> None:
        self._choices = choices

    @staticmethod
    def _extract(query: str, choices: Container[str], scorer: Scorer, cutoff: int = 0) -> list[FuzzResult]:
        results = process.extractBests(
            query, choices, limit=FuzzBest._limit, scorer=scorer.value, score_cutoff=cutoff
        )
        return [FuzzResult.from_result(result) for result in results]

    def _best(self, query: str, confidence: int) -> Optional[FuzzResult]:
        # cutoff using the 1st scorer
        scorer, weight = FuzzBest._scorers[0]
        if results := self._extract(query, self._choices, scorer=scorer, cutoff=100 - confidence):
            # print(f"{query=}")
            # print("found", results)
            if len(results) == 1:
                return results[0]
            # get the accumulated score with weight
            scores = {result.name: result.score for result in results}
            accumulated_scores = {name: score * weight for name, score in scores.items()}
            for scorer, weight in FuzzBest._scorers[1:]:
                for result in self._extract(query, scores.keys(), scorer=scorer):
                    accumulated_scores[result.name] += result.score * weight
            # print(accumulated_scores)
            best = sorted(
                (FuzzResult(name, score) for name, score in accumulated_scores.items()),
                key=lambda result: result.score,
                reverse=True,
            )[0]
            return FuzzResult(best.name, scores[best.name])
        return None

    def get(self, query: str, confidence: int) -> Optional[FuzzResult]:
        if query in self._choices:
            return FuzzResult(query, 100)
        return self._best(query, confidence)


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
            if found := FuzzBest(self.programmes.all_names).get(_normalize(epg_id), confidence):
                if programmes := self.programmes.get_programmes(found.name):
                    logger.info(
                        "Found Epg '%s' for %s with confidence %s%% (cut off @%s%%)",
                        found.name,
                        epg_id,
                        found.score,
                        100 - confidence,
                    )
                    return FoundProgammes(programmes, int(found.score))
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
