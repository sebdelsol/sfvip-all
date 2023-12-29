# pylint: disable=c-extension-no-member
import gzip
import logging
import multiprocessing
import tempfile
import time
import unicodedata
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, Optional, Self
from urllib.parse import urlparse

import lxml.etree as ET
import requests

from shared.job_runner import JobRunner

from .programme import EPGprogramme, InternalProgramme

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
    name = name.lower()
    for char in ".-/(){}[]: ":
        name = name.replace(char, "")
    name = name.replace("+", "plus")
    # remove accents
    nfkd_form = unicodedata.normalize("NFKD", name)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def _valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc and result.scheme in ("http", "https"))
    except ValueError:
        return False


class _ProgressStep:
    def __init__(self, step: float = 0.01, total: float = 0) -> None:
        self._total = total
        self._last = 0
        self._step = step

    def increment_total(self, increment: float):
        self._total += increment

    def progress(self, current: float) -> Optional[float]:
        progress = current / (self._total or 1)
        if progress - self._last >= self._step:
            self._last = progress
            return progress
        return None


class EPGupdate(NamedTuple):
    channels: dict[str, list[InternalProgramme]] = {}

    @classmethod
    def _get(cls, url: str, update_status: UpdateStatusT, stopping: StoppingT, timeout: int) -> Optional[Self]:
        try:
            update_status(EPGProgress(EPGstatus.LOADING))
            with tempfile.TemporaryDirectory() as temp_dir:
                with requests.get(url, stream=True, timeout=timeout) as response:
                    response.raise_for_status()
                    if total_size := int(response.headers.get("Content-Length", 0)):
                        progress_step = _ProgressStep(total=total_size)
                        xml = Path(temp_dir) / "xml"
                        with xml.open(mode="wb") as f:
                            chunk_size = 1024 * 128
                            for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                                if stopping():
                                    break
                                if progress := progress_step.progress(i * chunk_size):
                                    update_status(EPGProgress(EPGstatus.LOADING, progress))
                                f.write(chunk)
                            else:
                                return cls._process(xml, url, update_status, stopping)
        except (requests.RequestException, gzip.BadGzipFile, ET.ParseError):
            pass
        return None

    @classmethod
    def _process(cls, xml: Path, url: str, update_status: UpdateStatusT, stopping: StoppingT) -> Optional[Self]:
        update_status(EPGProgress(EPGstatus.PROCESSING))
        with gzip.GzipFile(xml) if url.endswith(".gz") else xml.open("rb") as f:
            channels: dict[str, list[InternalProgramme]] = {}
            progress_step = _ProgressStep()
            elem: ET.ElementBase
            title: str = ""
            desc: str = ""
            for _, elem in ET.iterparse(
                f,
                events=("end",),
                tag=("channel", "programme", "title", "desc"),
                remove_blank_text=True,
                remove_comments=True,
                remove_pis=True,
            ):
                if stopping():
                    break
                match elem.tag:
                    case "channel":
                        progress_step.increment_total(1)
                    case "title":
                        title = elem.text
                    case "desc":
                        desc = elem.text
                    case "programme":
                        if channel := elem.get("channel", None):
                            channel = _normalize(channel)
                            if channel not in channels:
                                channels[channel] = []
                                if progress := progress_step.progress(len(channels)):
                                    update_status(EPGProgress(EPGstatus.PROCESSING, progress))
                            channels[channel].append(
                                InternalProgramme(
                                    start=elem.get("start", ""),
                                    stop=elem.get("stop", ""),
                                    title=title,
                                    desc=desc,
                                )
                            )
                        title = ""
                        desc = ""
                elem.clear(False)
            else:
                return cls(channels)
            return None

    @classmethod
    def from_url(cls, url: str, update_status: UpdateStatusT, stopping: StoppingT, timeout: int) -> Self:
        if url:
            if _valid_url(url):
                logger.info("Load epg channels from '%s'", url)
                if (update := cls._get(url, update_status, stopping, timeout)) is not None:
                    logger.info("Epg channels updated from '%s'", url)
                    logger.info("%s Epg channels found", len(update.channels))
                    update_status(EPGProgress(EPGstatus.READY))
                    return update
                update_status(EPGProgress(EPGstatus.FAILED))
            else:
                update_status(EPGProgress(EPGstatus.INVALID_URL))
        else:
            update_status(EPGProgress(EPGstatus.NO_EPG))
        return cls()

    def get_programmes(self, channel: str) -> Iterator[dict[str, str]]:
        now = time.time()
        for programme in self.channels.get(_normalize(channel), ()):
            if programme := EPGprogramme.from_programme(programme, now):
                yield programme


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
