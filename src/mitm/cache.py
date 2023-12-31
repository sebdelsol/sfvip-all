import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Iterator, Literal, NamedTuple, Optional, Self

from mitmproxy import http

from ..winapi import mutex
from .utils import get_int, get_query_key, response_json

logger = logging.getLogger(__name__)


class StalkerQuery(NamedTuple):
    types = "vod", "series"
    server: str
    type: str
    page: int

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            get_query_key(flow.request, "category") == "*"
            and (panel_type := get_query_key(flow.request, "type")) in StalkerQuery.types
            and (page := get_int(get_query_key(flow.request, "p")))
            and (server := flow.request.host_header)
        ):
            return cls(
                server=server,
                type=panel_type,
                page=page,
            )
        return None


DataT = list[dict[str, Any]]


class StalkerContent(NamedTuple):
    query: StalkerQuery
    data: DataT
    total: int

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            (query := StalkerQuery.get_from(flow))
            and (json_content := response_json(flow.response))
            and isinstance(json_content, dict)
            and (js := json_content.get("js"))
            and isinstance(js, dict)
        ):
            return cls(
                query=query,
                data=js.get("data", []),
                total=js.get("total_items", 0),
            )
        return None

    # TODO clean: extend data in this class ?
    def final(self, data: DataT) -> dict[str, dict[str, Any]]:
        return {
            "js": dict(
                max_page_items=self.total,
                total_items=self.total,
                data=data,
            )
        }


def sanitize_filename(filename: str) -> str:
    for char in "/?<>\\:*|":
        filename = filename.replace(char, ".")
    return filename


class StalkerCache:
    encoding = "utf-8"
    cache_marker = "ListCached"
    cache_marker_bytes = cache_marker.encode()

    def __init__(self, roaming: Path) -> None:
        self.data: DataT = []
        # TODO clean unused cache ?
        self.cache_dir = roaming / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cache is in '%s'", self.cache_dir)

    @contextmanager
    def file(self, query: StalkerQuery, mode: Literal["r"] | Literal["w"]) -> Iterator[IO[str] | None]:
        path = self.cache_dir / sanitize_filename(f"{query.server}.{query.type}")
        with mutex.SystemWideMutex(f"file lock for {path}"):
            try:
                with path.open(mode, encoding=StalkerCache.encoding) as file:
                    logger.info("%s '%s'", "Load cache from" if mode == "r" else "Save cache in", file.name)
                    yield file
            except (PermissionError, FileNotFoundError):
                yield None

    def save_response(self, flow: http.HTTPFlow) -> None:
        # TODO progress
        response = flow.response
        if response and StalkerCache.cache_marker_bytes not in response.headers:
            if content := StalkerContent.get_from(flow):
                if content.query.page == 1:
                    self.data = content.data
                else:
                    self.data.extend(content.data)
                # are we done ?
                if len(self.data) >= content.total:
                    with self.file(content.query, "w") as file:
                        if file:
                            file.write(json.dumps(content.final(self.data)))

    def load_response(self, flow: http.HTTPFlow) -> None:
        if query := StalkerQuery.get_from(flow):
            with self.file(query, "r") as file:
                if file:
                    flow.response = http.Response.make(
                        content=file.read(),
                        headers={
                            "Content-Type": "application/json",
                            StalkerCache.cache_marker: "",
                        },
                    )
