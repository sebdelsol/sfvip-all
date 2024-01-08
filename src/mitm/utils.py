import json
from enum import StrEnum
from typing import Any, NamedTuple, Optional, Self

from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView


def _query(request: http.Request) -> MultiDictView[str, str]:
    return getattr(request, "urlencoded_form" if request.method == "POST" else "query")


def del_query_key(request: http.Request, key: str) -> None:
    del _query(request)[key]


def get_query_key(request: http.Request, key: str) -> Optional[str]:
    return _query(request).get(key)


def response_json(response: Optional[http.Response]) -> Any:
    try:
        if (
            response
            and (content := response.text)
            # could be other types like javascript
            # and "application/json" in response.headers.get("content-type", "")
            and (content_json := json.loads(content))
        ):
            return content_json
    except json.JSONDecodeError:
        pass
    return None


class APIRequest(StrEnum):
    XC = "player_api.php?"
    MAC = "portal.php?"


class Request(NamedTuple):
    api: APIRequest
    action: Optional[str]

    @classmethod
    def is_api(cls, request: http.Request) -> Optional[Self]:
        for api in APIRequest:
            if api.value in request.path:
                return cls(api, get_query_key(request, "action"))
        return None


def get_int(text: Optional[str]) -> Optional[int]:
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
