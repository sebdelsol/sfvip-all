# pylint: disable=c-extension-no-member
import gzip
import logging
import multiprocessing
import re
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import IO, Callable, Iterator, NamedTuple, Optional, Self
from urllib.parse import urlparse

import lxml.etree as ET
import requests
from thefuzz import fuzz, process

from shared.job_runner import JobRunner

from ..utils import ProgressStep
from .programme import InternalProgramme

logger = logging.getLogger(__name__)


class EPGstatus(Enum):
    LOADING = auto()
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
    channels: dict[str, list[InternalProgramme]] = {}

    @classmethod
    def _get(cls, url: str, update_status: UpdateStatusT, stopping: StoppingT, timeout: int) -> Optional[Self]:
        try:
            if Path(url).is_file():  # for debug purpose
                return cls._process(Path(url), url, update_status, stopping)

            update_status(EPGProgress(EPGstatus.LOADING))
            with tempfile.TemporaryDirectory() as temp_dir:
                with requests.get(url, stream=True, timeout=timeout) as response:
                    response.raise_for_status()
                    xml = Path(temp_dir) / "xml"
                    with xml.open(mode="wb") as f:
                        total_size = int(response.headers.get("Content-Length", 0))
                        progress_step = ProgressStep(total=total_size) if total_size else None
                        for i, chunk in enumerate(response.iter_content(chunk_size=EPGupdate._chunk_size)):
                            if stopping():
                                return None
                            if progress_step and (progress := progress_step.progress(i * EPGupdate._chunk_size)):
                                update_status(EPGProgress(EPGstatus.LOADING, progress))
                            f.write(chunk)
                return cls._process(xml, url, update_status, stopping)
        except (requests.RequestException, gzip.BadGzipFile, ET.ParseError, EOFError) as error:
            logger.error("%s: %s", error.__class__.__name__, error)
        return None

    @classmethod
    def _process(cls, xml: Path, url: str, update_status: UpdateStatusT, stopping: StoppingT) -> Optional[Self]:
        update_status(EPGProgress(EPGstatus.PROCESSING))
        with gzip.GzipFile(xml) if url.endswith(".gz") else xml.open("rb") as f:
            channels: dict[str, list[InternalProgramme]] = {}
            display_names: dict[str, str] = {}
            normalized: dict[str, str] = {}
            progress_step = ProgressStep()

            def handle_channel(channel_id: str, display_name: str) -> None:
                progress_step.increment_total(1)
                display_names[channel_id] = display_name

            def handle_programme(channel_id: str, programme: InternalProgramme) -> None:
                if channel_id not in normalized:
                    normalized[channel_id] = _normalize(channel_id)
                if (channel := normalized[channel_id]) not in channels:
                    channels[channel] = []
                    if display_name := display_names.get(channel_id):
                        if display_name not in channels:
                            channels[_normalize(display_name)] = channels[channel]
                    if progress := progress_step.increment_progress(1):
                        update_status(EPGProgress(EPGstatus.PROCESSING, progress))
                channels[channel].append(programme)

            for _ in parse_programme(f, handle_channel, handle_programme):
                if stopping():
                    return None
            logger.info("%s Epg channels found from '%s'", progress_step.total, url)
            return cls(channels)

    @classmethod
    def from_url(cls, url: str, update_status: UpdateStatusT, stopping: StoppingT, timeout: int) -> Self:
        if url:
            if _valid_url(url) or Path(url).is_file():
                logger.info("Load epg channels from '%s'", url)
                if (update := cls._get(url, update_status, stopping, timeout)) is not None:
                    update_status(EPGProgress(EPGstatus.READY))
                    return update
                update_status(EPGProgress(EPGstatus.FAILED))
            else:
                update_status(EPGProgress(EPGstatus.INVALID_URL))
        else:
            update_status(EPGProgress(EPGstatus.NO_EPG))
        return cls()

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
    def __init__(self, update_status: UpdateStatusT, timeout: int) -> None:
        self._update_lock = multiprocessing.Lock()
        self._update: Optional[EPGupdate] = None
        self._update_status = update_status
        self._timeout = timeout
        super().__init__(self._updating, "Epg updater")

    def _updating(self, url: str) -> None:
        if update := EPGupdate.from_url(url, self._update_status, self.stopping, self._timeout):
            with self._update_lock:
                self._update = update

    @property
    def update(self) -> Optional[EPGupdate]:
        with self._update_lock:
            return self._update
