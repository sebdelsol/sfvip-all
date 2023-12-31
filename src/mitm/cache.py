import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Iterator, Literal, NamedTuple, Optional, Self

from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView

from src.winapi import mutex

logger = logging.getLogger(__name__)

PannelTypes = "vod", "series"


# TODO facto
def _query(request: http.Request) -> MultiDictView[str, str]:
    return getattr(request, "urlencoded_form" if request.method == "POST" else "query")


def _get_query_key(request: http.Request, key: str) -> Optional[str]:
    return _query(request).get(key)


def _get_int(text: Optional[str]) -> Optional[int]:
    try:
        if text:
            return int(text)
    except ValueError:
        pass
    return None


class StalkerQuery(NamedTuple):
    server: str
    type: str
    page: int

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            _get_query_key(flow.request, "category") == "*"
            and (pannel_type := _get_query_key(flow.request, "type")) in PannelTypes
            and (page := _get_int(_get_query_key(flow.request, "p")))
            and (server := flow.request.host_header)
        ):
            return cls(
                server=server.replace(":", ""),
                type=pannel_type,
                page=page,
            )
        return None


DataT = list[dict[str, Any]]


class StalkerContent(NamedTuple):
    query: StalkerQuery
    data: DataT
    total: int
    # TODO category

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            (query := StalkerQuery.get_from(flow))
            and (json_content := cls._response_json(flow))
            and (js := json_content.get("js"))
            and isinstance(js, dict)
        ):
            return cls(
                query=query,
                data=js.get("data", []),
                total=js.get("total_items", 0),
            )
        return None

    @staticmethod
    # TODO facto
    def _response_json(flow: http.HTTPFlow) -> Optional[dict[str, Any]]:
        try:
            if (
                (response := flow.response)
                and (content := response.text)
                and "application/json" in response.headers.get("content-type", "")
                and (json_dict := json.loads(content))
                and isinstance(json_dict, dict)
            ):
                return json_dict
        except json.JSONDecodeError:
            pass
        return None


class StalkerCache:
    cache_marker = "ListCached"
    encoding = "utf-8"

    def __init__(self, roaming: Path) -> None:
        self.data: DataT = []
        # TODO clean unused cache ?
        self.cache_dir = roaming / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cache is in '%s'", self.cache_dir)

    @contextmanager
    def file(self, query: StalkerQuery, mode: Literal["r"] | Literal["w"]) -> Iterator[IO | None]:
        path = self.cache_dir / f"{query.server}.{query.type}"
        with mutex.SystemWideMutex(f"file lock for {path.name}"):
            try:
                with path.open(mode, encoding=StalkerCache.encoding) as file:
                    logger.info("Load cache from '%s'" if mode == "r" else "Save cache in '%s'", file.name)
                    yield file
            except (PermissionError, FileNotFoundError):
                yield None

    def save_response(self, flow: http.HTTPFlow) -> None:
        # TODO progress
        response = flow.response
        if response and StalkerCache.cache_marker.encode() not in response.headers:
            if content := StalkerContent.get_from(flow):
                if content.query.page == 1:
                    self.data = content.data
                else:
                    self.data.extend(content.data)
                # are we done ?
                if len(self.data) == content.total:
                    # TODO winapi out of sfvip
                    with self.file(content.query, "w") as file:
                        if file:
                            js = dict(
                                max_page_items=content.total,
                                total_items=content.total,
                                data=self.data,
                            )
                            file.write(json.dumps({"js": js}))

    def load_response(self, flow: http.HTTPFlow) -> Optional[http.Response]:
        if query := StalkerQuery.get_from(flow):
            with self.file(query, "r") as file:
                if file:
                    return http.Response.make(
                        content=file.read(),
                        headers={
                            "Content-Type": "application/json",
                            StalkerCache.cache_marker: "",
                        },
                    )
        return None
