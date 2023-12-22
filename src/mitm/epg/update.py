import base64
import gzip
import logging
import multiprocessing
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from enum import Enum, auto
from typing import Callable, Iterator, NamedTuple, Optional, Self
from urllib.parse import urlparse

import requests

from shared.job_runner import JobRunner

logger = logging.getLogger(__name__)


class _EPGprogramme(dict[str, str]):
    @classmethod
    def from_element(cls, element: ET.Element, now: float) -> Optional[Self]:
        if (start := element.get("start")) and (stop := element.get("stop")):
            end = cls.get_timestamp(stop)
            if end >= now:
                start = cls.get_timestamp(start)
                return cls(
                    title=cls.get_text(element, "title"),
                    description=cls.get_text(element, "desc"),
                    start=cls.get_date_str(start),
                    end=cls.get_date_str(end),
                    start_timestamp=str(start),
                    stop_timestamp=str(end),
                )
        return None

    @staticmethod
    def get_text(element: ET.Element, tag: str) -> str:
        if (found := element.find(tag)) is not None and (text := found.text):
            return base64.b64encode(text.replace("\\", "").encode()).decode()
        return ""

    @staticmethod
    def get_timestamp(date: str) -> int:
        return round(datetime.strptime(date, r"%Y%m%d%H%M%S %z").timestamp())

    @staticmethod
    def get_date_str(timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp).strftime(r"%Y-%m-%d %H:%M:%S")


class EPGstatus(Enum):
    LOADING = auto()
    READY = auto()
    FAILED = auto()
    NO_EPG = auto()
    INVALID_URL = auto()


UpdateStatusT = Callable[[EPGstatus], None]


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


class EPGupdate(NamedTuple):
    _timeout = 5

    url: str = ""
    channels: dict[str, str] = {}
    tree: Optional[ET.Element] = None

    @staticmethod
    def _get_tree(url: str) -> Optional[ET.Element]:
        try:
            with requests.get(url, timeout=EPGupdate._timeout) as response:
                response.raise_for_status()
                xml = gzip.decompress(response.content) if url.endswith(".gz") else response.content
                return ET.fromstring(xml)
        except (requests.RequestException, gzip.BadGzipFile, ET.ParseError):
            return None

    @classmethod
    def from_url(cls, url: str, update_status: UpdateStatusT) -> Self:
        if url:
            if _valid_url(url):
                logger.info("load epg channels from '%s'", url)
                update_status(EPGstatus.LOADING)
                if tree := cls._get_tree(url):
                    channels = {
                        _normalize(channel_id): channel_id
                        for element in tree.findall("./channel")
                        if (channel_id := element.get("id"))
                    }
                    logger.info("epg channels updated from '%s'", url)
                    update_status(EPGstatus.READY)
                    return cls(url, channels, tree)
                update_status(EPGstatus.FAILED)
            else:
                update_status(EPGstatus.INVALID_URL)
        else:
            update_status(EPGstatus.NO_EPG)
        return cls(url)

    def get_programmes(self, channel_id: str) -> Iterator[dict[str, str]]:
        if self.channels and self.tree:
            channel_id = _normalize(channel_id)
            if channel := self.channels.get(channel_id):
                now = time.time()
                for element in self.tree.findall(f'./programme[@channel="{channel}"]'):
                    if programme := _EPGprogramme.from_element(element, now):
                        yield programme


class EPGupdater(JobRunner[str]):
    def __init__(self, update_status: UpdateStatusT) -> None:
        self._update_lock = multiprocessing.Lock()
        self._update: Optional[EPGupdate] = None
        self._update_status = update_status
        super().__init__(self._updating, "epg updater")

    def _updating(self, url: str) -> None:
        with self._update_lock:
            update = self._update
        if not update or update.url != url:
            update = EPGupdate.from_url(url, self._update_status)
            with self._update_lock:
                self._update = update

    @property
    def update(self) -> Optional[EPGupdate]:
        with self._update_lock:
            return self._update
