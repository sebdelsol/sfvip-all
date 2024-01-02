import json
import logging
import time
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from typing import IO, Any, Callable, Iterator, Literal, NamedTuple, Optional, Self

from mitmproxy import http

from ..winapi import mutex
from .utils import ProgressStep, get_int, get_query_key, response_json

logger = logging.getLogger(__name__)

MediaTypes = "vod", "series"
ValidMediaTypes = Literal["vod", "series"]


class StalkerQuery(NamedTuple):
    server: str
    type: ValidMediaTypes

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            (media_type := get_query_key(flow.request, "type"))
            and media_type in MediaTypes
            and ((server := flow.request.host_header))
        ):
            return cls(
                server=server,
                type=media_type,
            )
        return None


DataT = list[dict[str, Any]]


class StalkerContent(NamedTuple):
    query: StalkerQuery
    page: Optional[int]
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
                page=get_int(get_query_key(flow.request, "p")),
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


class AllUpdated(NamedTuple):
    today: str
    one_day: str
    several_days: str
    all_names: dict[ValidMediaTypes, str] = {}
    all_updates: dict[ValidMediaTypes, str] = {}

    def all_title(self, query: StalkerQuery) -> str:
        return self.all_names.get(query.type, "")

    def _days_ago(self, path: Path) -> str:
        timestamp = path.stat().st_mtime
        days = int((time.time() - timestamp) / (3600 * 24))
        match days:
            case 0:
                return self.today
            case 1:
                return self.one_day
            case _:
                return self.several_days % days

    def update_all_title(self, query: StalkerQuery, path: Path) -> str:
        return f"🔄 {self.all_updates.get(query.type)}\n{self._days_ago(path)}"


class CacheProgressEvent(Enum):
    START = auto()
    STOP = auto()
    SHOW = auto()


class CacheProgress(NamedTuple):
    event: CacheProgressEvent
    progress: float = 0


UpdateCacheProgressT = Callable[[CacheProgress], None]


class StalkerCache:
    encoding = "utf-8"
    cached_marker = "ListCached"
    cached_marker_bytes = cached_marker.encode()
    cached_all_category = "cached_all_category"
    update_all_category = "*"

    def __init__(self, roaming: Path, update_progress: UpdateCacheProgressT, all_updated: AllUpdated) -> None:
        self.data: DataT = []
        self.current_server = None
        self.progress_step = None
        self.update_progress = update_progress
        self.all_updated = all_updated
        # TODO clean unused cache ?
        self.cache_dir = roaming / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cache is in '%s'", self.cache_dir)

    def file_path(self, query: StalkerQuery) -> Path:
        return self.cache_dir / sanitize_filename(f"{query.server}.{query.type}")

    @contextmanager
    def file(self, query: StalkerQuery, mode: Literal["r", "w"]) -> Iterator[IO[str] | None]:
        path = self.file_path(query)
        with mutex.SystemWideMutex(f"file lock for {path}"):
            try:
                with path.open(mode, encoding=StalkerCache.encoding) as file:
                    logger.info("%s '%s'", "Load cache from" if mode == "r" else "Save cache in", file.name)
                    yield file
            except (PermissionError, FileNotFoundError):
                yield None

    def save_response(self, flow: http.HTTPFlow) -> None:
        if (
            get_query_key(flow.request, "category") == StalkerCache.update_all_category
            and (response := flow.response)
            and StalkerCache.cached_marker_bytes not in response.headers
            and (content := StalkerContent.get_from(flow))
        ):
            self.current_server = content.query.server
            if content.page == 1:
                self.data = content.data
                self.progress_step = ProgressStep(step=0.0005, total=content.total)
                self.update_progress(CacheProgress(CacheProgressEvent.START))
            else:
                self.data.extend(content.data)
            if self.progress_step and (progress := self.progress_step.progress(len(self.data))):
                self.update_progress(CacheProgress(CacheProgressEvent.SHOW, progress))
            # are we done ?
            if len(self.data) >= content.total:
                self.update_progress(CacheProgress(CacheProgressEvent.STOP))
                with self.file(content.query, "w") as file:
                    if file:
                        file.write(json.dumps(content.final(self.data)))

    def stop(self, flow: http.HTTPFlow) -> None:
        if flow.request.host_header == self.current_server:
            self.update_progress(CacheProgress(CacheProgressEvent.STOP))
            self.data = []

    def load_response(self, flow: http.HTTPFlow) -> None:
        if get_query_key(flow.request, "category") == StalkerCache.cached_all_category and (
            query := StalkerQuery.get_from(flow)
        ):
            with self.file(query, "r") as file:
                if file:
                    flow.response = http.Response.make(
                        content=file.read(),
                        headers={
                            "Content-Type": "application/json",
                            StalkerCache.cached_marker: "",
                        },
                    )

    def inject_all_cached_category(self, flow: http.HTTPFlow):
        # pylint: disable=too-many-boolean-expressions
        if (
            (query := StalkerQuery.get_from(flow))
            and (response := flow.response)
            and (json_content := response_json(response))
            and isinstance(json_content, dict)
            and (categories := json_content.get("js"))
            and isinstance(categories, list)
            and categories
            and (all_category := categories[0])
            and isinstance(all_category, dict)
            and (all_category.get("id") == StalkerCache.update_all_category)
        ):
            all_title = self.all_updated.all_title(query)
            logger.info("Rename '%s' category for '%s'", all_title, query.server)
            all_category["title"] = all_title
            if (path := self.file_path(query)) and path.is_file():
                all_category["id"] = StalkerCache.cached_all_category
                update_all_category = dict(
                    alias=StalkerCache.update_all_category,
                    censored=0,
                    id=StalkerCache.update_all_category,
                    title=self.all_updated.update_all_title(query, path),
                )
                categories.insert(1, update_all_category)
                logger.info("Inject cached '%s' category for '%s'", all_title, query.server)
            response.text = json.dumps(dict(js=categories))
