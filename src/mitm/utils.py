import json
from typing import Any, Optional

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
            and "application/json" in response.headers.get("content-type", "")
            and (content_json := json.loads(content))
        ):
            return content_json
    except json.JSONDecodeError:
        pass
    return None


def get_int(text: Optional[str]) -> Optional[int]:
    try:
        if text:
            return int(text)
    except ValueError:
        pass
    return None
