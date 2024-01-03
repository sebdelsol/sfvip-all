import json
import logging
import time
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    Iterator,
    Literal,
    NamedTuple,
    Optional,
    Self,
    TypeVar,
)

from mitmproxy import http

from ..winapi import mutex
from .utils import ProgressStep, get_int, get_query_key, response_json

logger = logging.getLogger(__name__)

MediaTypes = "vod", "series"
ValidMediaTypes = Literal["vod", "series"]


class MACQuery(NamedTuple):
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


class AllUpdated(NamedTuple):
    today: str
    one_day: str
    several_days: str
    all_names: dict[ValidMediaTypes, str] = {}
    all_updates: dict[ValidMediaTypes, str] = {}

    def all_title(self, query: MACQuery) -> str:
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

    def update_all_title(self, query: MACQuery, path: Path) -> str:
        return f"🔄 {self.all_updates.get(query.type)}\n{self._days_ago(path)}"


class CacheProgressEvent(Enum):
    START = auto()
    STOP = auto()
    SHOW = auto()


class CacheProgress(NamedTuple):
    event: CacheProgressEvent
    progress: float = 0


UpdateCacheProgressT = Callable[[CacheProgress], None]

DataT = list[dict[str, Any]]
T = TypeVar("T")


def get_js(response: http.Response, wanted_type: type[T]) -> Optional[T]:
    if (
        (json_content := response_json(response))
        and isinstance(json_content, dict)
        and (js := json_content.get("js"))
        and isinstance(js, wanted_type)
        and js
    ):
        return js
    return None


def set_js(obj: Any) -> dict[str, Any]:
    return {"js": obj}


class MACContent:
    def __init__(self, update_progress: UpdateCacheProgressT) -> None:
        self.data: DataT = []
        self.progress_step = ProgressStep(step=0.0005)
        self.update_progress = update_progress

    def extend(self, flow: http.HTTPFlow) -> Optional[dict]:
        if flow.response and (js := get_js(flow.response, dict)):
            data = js.get("data", [])
            total = js.get("total_items", 0)
            page = get_int(get_query_key(flow.request, "p"))
            self.data.extend(data)
            if page == 1:  # page
                self.progress_step.set_total(total)
                self.update_progress(CacheProgress(CacheProgressEvent.START))
            if self.progress_step and (progress := self.progress_step.progress(len(self.data))):
                self.update_progress(CacheProgress(CacheProgressEvent.SHOW, progress))
            if len(self.data) >= total:
                self.update_progress(CacheProgress(CacheProgressEvent.STOP))
                return set_js(
                    dict(
                        max_page_items=total,
                        total_items=total,
                        data=self.data,
                    )
                )
        return None


def sanitize_filename(filename: str) -> str:
    for char in "/?<>\\:*|":
        filename = filename.replace(char, ".")
    return filename


class MACCache:
    encoding = "utf-8"
    cached_marker = "ListCached"
    cached_marker_bytes = cached_marker.encode()
    cached_all_category = "cached_all_category"
    update_all_category = "*"

    def __init__(self, roaming: Path, update_progress: UpdateCacheProgressT, all_updated: AllUpdated) -> None:
        self.data: DataT = []
        self.contents: dict[str, MACContent] = {}
        self.update_progress = update_progress
        self.all_updated = all_updated
        # TODO clean unused cache ?
        self.cache_dir = roaming / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cache is in '%s'", self.cache_dir)

    def file_path(self, query: MACQuery) -> Path:
        return self.cache_dir / sanitize_filename(f"{query.server}.{query.type}")

    @contextmanager
    def file(self, query: MACQuery, mode: Literal["r", "w"]) -> Iterator[IO[str] | None]:
        path = self.file_path(query)
        with mutex.SystemWideMutex(f"file lock for {path}"):
            try:
                with path.open(mode, encoding=MACCache.encoding) as file:
                    logger.info("%s '%s'", "Load cache from" if mode == "r" else "Save cache in", file.name)
                    yield file
            except (PermissionError, FileNotFoundError):
                yield None

    def save_response(self, flow: http.HTTPFlow) -> None:
        if (
            get_query_key(flow.request, "category") == MACCache.update_all_category
            and (response := flow.response)
            and MACCache.cached_marker_bytes not in response.headers
            and (query := MACQuery.get_from(flow))
        ):
            if query.server not in self.contents:
                self.contents[query.server] = MACContent(self.update_progress)
            if final := self.contents[query.server].extend(flow):
                with self.file(query, "w") as file:
                    if file:
                        file.write(json.dumps(final))
                        del self.contents[query.server]

    def stop(self, flow: http.HTTPFlow) -> None:
        if (server := flow.request.host_header) in self.contents:
            self.update_progress(CacheProgress(CacheProgressEvent.STOP))
            del self.contents[server]

    def load_response(self, flow: http.HTTPFlow) -> None:
        if get_query_key(flow.request, "category") == MACCache.cached_all_category and (
            query := MACQuery.get_from(flow)
        ):
            with self.file(query, "r") as file:
                if file:
                    flow.response = http.Response.make(
                        content=file.read(),
                        headers={
                            "Content-Type": "application/json",
                            MACCache.cached_marker: "",
                        },
                    )

    def inject_all_cached_category(self, flow: http.HTTPFlow):
        # pylint: disable=too-many-boolean-expressions
        if (
            (query := MACQuery.get_from(flow))
            and (response := flow.response)
            and (categories := get_js(response, list))
            and (all_category := categories[0])
            and isinstance(all_category, dict)
            and (all_category.get("id") == MACCache.update_all_category)
        ):
            all_title = self.all_updated.all_title(query)
            logger.info("Rename '%s' category for '%s'", all_title, query.server)
            all_category["title"] = all_title
            if (path := self.file_path(query)) and path.is_file():
                all_category["id"] = MACCache.cached_all_category
                update_all_category = dict(
                    alias=MACCache.update_all_category,
                    censored=0,
                    id=MACCache.update_all_category,
                    title=self.all_updated.update_all_title(query, path),
                )
                categories.insert(1, update_all_category)
                logger.info("Inject cached '%s' category for '%s'", all_title, query.server)
            response.text = json.dumps(dict(js=categories))
