import time
from io import BytesIO
from typing import Protocol, Self

import feedparser
import requests


class FeedEntry(Protocol):
    title: str
    link: str
    updated_parsed: time.struct_time


class FeedEntries(Protocol):
    entries: list[FeedEntry]
    status: int
    bozo: bool

    @classmethod
    def get_from_url(cls, url: str, timeout: int) -> list[FeedEntry]:
        try:
            with requests.get(url, timeout=timeout) as response:
                response.raise_for_status()
                feed: Self = feedparser.parse(BytesIO(response.content))
                if not feed.bozo and feed.entries:
                    return feed.entries
        except requests.RequestException:
            pass
        return []
