import base64
import gzip
import logging
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Iterator, NamedTuple, Optional, Self

import requests

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
    name = name.lower().replace(".", "").replace("+", "plus")
    return unicodedata.normalize("NFKD", name)


class EPG:
    _timeout = 10

    def __init__(self, url: str) -> None:
        self.url = url
        self.tree = None
        self.to_channel_ids = {}
        self.normalized_channels = {}
        self.channels_lock = threading.Lock()
        threading.Thread(target=self._populate_channels).start()

    def _get_tree(self) -> Optional[ET.Element]:
        try:
            with requests.get(self.url, timeout=EPG._timeout) as response:
                response.raise_for_status()
                xml = gzip.decompress(response.content) if self.url.endswith(".gz") else response.content
                return ET.fromstring(xml)
        except (requests.RequestException, gzip.BadGzipFile, ET.ParseError):
            return None

    def _populate_channels(self) -> None:
        if tree := self._get_tree():
            normalized_channels = {
                _normalize(channel_id): channel_id
                for element in tree.findall("./channel")
                if (channel_id := element.get("id"))
            }
            with self.channels_lock:
                self.tree = tree
                self.normalized_channels = normalized_channels

    def _find_channel_id(self, channel: dict) -> Optional[str]:
        if channel_id := channel.get("epg_channel_id"):
            if isinstance(channel_id, str):
                channel_id = _normalize(channel_id)
                if channel_id in self.normalized_channels:
                    return self.normalized_channels[channel_id]
        return None

    def _get_from_channel_id(self, channel_id: str) -> Iterator[Programme]:
        with self.channels_lock:
            tree = self.tree
        if tree:
            now = time.time()
            for element in tree.findall(f'./programme[@channel="{channel_id}"]'):
                if programme := Programme.from_element(element, now):
                    yield programme

    def set_channel_ids(self, json) -> None:
        # TODO store in self.all_channels & deffer self.to_channel_ids creation in populate_channels
        if isinstance(json, list):
            for channel in json:
                if isinstance(channel, dict):
                    stream_id = channel.get("stream_id")
                    channel_id = self._find_channel_id(channel)
                    if stream_id and channel_id:
                        self.to_channel_ids[str(stream_id)] = channel_id

    def get(self, stream_id: str, limit: int) -> Iterator[dict[str, str]]:
        # TODO check to_channel_ids is valid
        if channel_id := self.to_channel_ids.get(stream_id):
            logger.info("get epg for %s", channel_id)
            for i, programme in enumerate(self._get_from_channel_id(channel_id)):
                if i >= limit:
                    break
                yield programme._asdict()


if __name__ == "__main__":
    _epg = EPG("https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz")
    time.sleep(3)
    for p in _epg._get_from_channel_id("TF1.fr"):
        print(p)
