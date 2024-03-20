from enum import Enum, auto
from typing import Any, Optional

import msgspec
from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView

json_decoder = msgspec.json.Decoder()
json_encoder = msgspec.json.Encoder()


class APItype(Enum):
    XC = auto()
    MAC = auto()
    M3U = auto()


def _query(request: http.Request) -> MultiDictView[str, str]:
    return request.urlencoded_form if request.method == "POST" else request.query


def del_query_key(flow: http.HTTPFlow, key: str) -> None:
    del _query(flow.request)[key]


def get_query_key(flow: http.HTTPFlow, key: str) -> Optional[str]:
    return _query(flow.request).get(key)


def content_json(content: Optional[bytes]) -> Any:
    try:
        if content and (json_ := json_decoder.decode(content)):
            return json_
    except msgspec.MsgspecError:
        pass
    return None


def response_json(response: Optional[http.Response]) -> Any:
    if response and (json_ := content_json(response.content)):
        return json_
    return None


def get_int(text: Optional[str | int]) -> Optional[int]:
    try:
        if text:
            return int(text)
    except ValueError:
        pass
    return None


class ProgressStep:
    def __init__(self, step: float = 0.01, total: float = 0) -> None:
        self._total = total
        self._current = 0
        self._last = 0
        self._step = step

    @property
    def total(self) -> float:
        return self._total

    def increment_total(self, increment: float):
        self._total += increment

    def set_total(self, total: float) -> None:
        self._total = total

    def increment_progress(self, increment: float) -> Optional[float]:
        self._current += increment
        return self.progress(self._current)

    def progress(self, current: float) -> Optional[float]:
        progress = current / (self._total or 1)
        if progress - self._last >= self._step:
            self._last = progress
            return progress
        return None
