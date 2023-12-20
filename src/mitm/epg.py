import base64
import gzip
import logging
import multiprocessing
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Iterator, NamedTuple, Optional, Self

import requests

from shared.job_runner import JobRunner

logger = logging.getLogger(__name__)


class Programme(NamedTuple):
    title: str
    description: str
    start: str
    end: str
    start_timestamp: str
    stop_timestamp: str

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


def _normalize(name: str) -> str:
    name = name.lower()
    for char in ".", "-", "/", "(", ")":
        name = name.replace(char, "")
    name = name.replace("+", "plus")
    # remove accents
    nfkd_form = unicodedata.normalize("NFKD", name)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def _get_int(text: Optional[str]) -> Optional[int]:
    try:
        if text:
            return int(text)
    except ValueError:
        pass
    return None


class ServerChannels:
    def __init__(self, channels: Any) -> None:
        self.channels: dict[str, str] = {}
        self.set(channels)

    def set(self, channels: Any) -> None:
        if isinstance(channels, list):
            for channel in channels:
                if isinstance(channel, dict):
                    stream_id = channel.get("stream_id")
                    channel_id = channel.get("epg_channel_id")
                    if isinstance(stream_id, (str, int)) and isinstance(channel_id, str):
                        self.channels[str(stream_id)] = channel_id

    def get(self, stream_id: str) -> Optional[str]:
        return self.channels.get(stream_id)


class EPGstatus(Enum):
    LOADING = auto()
    READY = auto()
    FAILED = auto()
    NOEPG = auto()


UpdateStatusT = Callable[[EPGstatus], None]


class EPGupdate(NamedTuple):
    _timeout = 5

    url: str = ""
    tree: Optional[ET.Element] = None
    channels: dict[str, str] = {}

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
            logger.info("update epg channels from '%s'", url)
            update_status(EPGstatus.LOADING)
            if tree := cls._get_tree(url):
                channels = {
                    _normalize(channel_id): channel_id
                    for element in tree.findall("./channel")
                    if (channel_id := element.get("id"))
                }
                logger.info("epg channels updated from '%s'", url)
                update_status(EPGstatus.READY)
                return cls(url, tree, channels)
            update_status(EPGstatus.FAILED)
        else:
            update_status(EPGstatus.NOEPG)
        return cls(url)


class EPGupdater(JobRunner[str]):
    _name = "epg updater"

    def __init__(self, update_done: Callable[[EPGupdate], None], update_status: UpdateStatusT) -> None:
        self._update_status = update_status
        self._update_done = update_done
        self._last_url = None
        super().__init__(self._update)

    def _update(self, url: str) -> None:
        if self._last_url != url:
            self._last_url = url
            self._update_done(EPGupdate.from_url(url, self._update_status))


class EPG:
    def __init__(self, update_status: UpdateStatusT) -> None:
        self.update: Optional[EPGupdate] = None
        self.servers: dict[str, ServerChannels] = {}
        self.update_lock = multiprocessing.Lock()
        self.updater = EPGupdater(self._update_done, update_status)

    def ask_update(self, url: str) -> None:
        self.updater.add_job(url)

    # All the following methods should be called int the same process !
    def _update_done(self, update: EPGupdate) -> None:
        with self.update_lock:
            self.update = update

    def start(self) -> None:
        self.updater.start()

    def stop(self) -> None:
        self.updater.stop()

    def get_programmes(self, channel_id: str) -> Iterator[Programme]:
        channel_id = _normalize(channel_id)
        with self.update_lock:
            tree = self.update and self.update.tree
            channel = self.update and self.update.channels.get(channel_id)
        if tree and channel:
            now = time.time()
            for element in tree.findall(f'./programme[@channel="{channel}"]'):
                if programme := Programme.from_element(element, now):
                    yield programme

    def set_server_channels(self, server: Optional[str], channels: Any) -> None:
        if server:
            logger.info("set channels for %s", server)
            self.servers[server] = ServerChannels(channels)

    def get(self, server: Optional[str], stream_id: str, limit: Optional[str]) -> Iterator[dict[str, str]]:
        if server and (server_channels := self.servers.get(server)):
            if channel_id := server_channels.get(stream_id):
                count = 0
                _limit = _get_int(limit)
                for count, programme in enumerate(self.get_programmes(channel_id)):
                    if _limit and count >= _limit:
                        break
                    yield programme._asdict()
                if count > 0:
                    logger.info("get epg for %s", channel_id)
