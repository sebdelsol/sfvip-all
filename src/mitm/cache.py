import logging
import multiprocessing
import pickle
import time
from enum import Enum, auto
from pathlib import Path
from typing import IO, Any, Callable, Literal, NamedTuple, Optional, Self, TypeVar

from mitmproxy import http

from shared.job_runner import JobRunner

from ..winapi import mutex
from .cache_cleaner import CacheCleaner
from .utils import ProgressStep, content_json, get_int, get_query_key, json_encoder

logger = logging.getLogger(__name__)
MediaTypes = "vod", "series"
ValidMediaTypes = Literal["vod", "series"]


def _in_beetween(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


class MacQuery(NamedTuple):
    server: str
    type: ValidMediaTypes

    @classmethod
    def get_from(cls, flow: http.HTTPFlow) -> Optional[Self]:
        if (
            (media_type := get_query_key(flow, "type"))
            and media_type in MediaTypes
            and (server := flow.request.host_header)
        ):
            return cls(
                server=server,
                type=media_type,
            )
        return None

    def __str__(self) -> str:
        return f"{self.server}.{self.type}"


class CacheProgressEvent(Enum):
    START = auto()
    STOP = auto()
    SHOW = auto()


class CacheProgress(NamedTuple):
    event: CacheProgressEvent
    progress: float = 0


UpdateCacheProgressT = Callable[[CacheProgress], None]
T = TypeVar("T")


def get_js(content: Optional[bytes], wanted_type: type[T]) -> Optional[T]:
    if (
        (json_ := content_json(content))
        and isinstance(json_, dict)
        and (js := json_.get("js"))
        and isinstance(js, wanted_type)
        and js
    ):
        return js
    return None


def get_reponse_js(response: http.Response, wanted_type: type[T]) -> Optional[T]:
    return get_js(response.content, wanted_type)


def set_js(obj: Any) -> dict[str, Any]:
    return {"js": obj}


def sanitize_filename(filename: str) -> str:
    for char in "/?<>\\:*|":
        filename = filename.replace(char, ".")
    return filename


class MacCacheFile:
    def __init__(self, cache_dir: Path, query: MacQuery) -> None:
        self.query = query
        self.file_path = cache_dir / sanitize_filename(str(self.query))
        self.mutex = mutex.SystemWideMutex(f"file lock for {self.file_path}")

    def open_and_do(
        self, mode: Literal["rb", "wb"], do: Callable[[IO[bytes]], None], *exceptions: type[Exception]
    ) -> None:
        with self.mutex:
            try:
                with self.file_path.open(mode) as file:
                    if file:
                        do(file)
            except (*exceptions, PermissionError, FileNotFoundError, OSError):
                pass


class MacCacheLoad(MacCacheFile):
    def __init__(self, cache_dir: Path, query: MacQuery) -> None:
        self.total: int = 0
        self.actual: int = 0
        self.timestamp: float = 0
        self.content: bytes = b""
        super().__init__(cache_dir, query)
        self._load()

    def _load(self) -> None:
        def _load(file: IO[bytes]) -> None:
            # pylint: disable=too-many-boolean-expressions
            if (
                (total := pickle.load(file))
                and isinstance(total, int)
                and (actual := pickle.load(file))
                and isinstance(actual, int)
                and (timestamp := pickle.load(file))
                and isinstance(timestamp, float)
                and (content := pickle.load(file))
                and isinstance(content, bytes)
            ):
                self.total = total
                self.actual = actual
                self.timestamp = timestamp
                self.content = content
                logger.info("Load Cache from '%s' (%s out of %s)", file.name, self.actual, self.total)

        self.open_and_do("rb", _load, pickle.PickleError, TypeError, EOFError)

    @property
    def valid(self) -> bool:
        return bool(self.total and self.actual and self.timestamp and self.content)

    @property
    def complete(self) -> float:
        return _in_beetween(self.actual / self.total, 0, 1) if self.total else 0


class MacCacheSave(MacCacheFile):
    def __init__(self, cache_dir: Path, query: MacQuery, update_progress: UpdateCacheProgressT) -> None:
        self.total: int = 0
        self.valid: bool = True
        self.contents: list[bytes] = []
        self.max_pages: float = 0
        # update the progress as often as we can to avoid the progress watchdog timeout
        self.progress_step = ProgressStep(step=0)
        self.update_progress = update_progress
        logger.info("Start creating Cache for %s.%s", query.server, query.type)
        super().__init__(cache_dir, query)

    async def update(self, response: http.Response, page: int) -> bool:
        if not self.valid:
            return False
        if not (content := response.content):
            logger.warning("No content for page %s for %s cache", page, str(self.query))
            self.valid = False
            return False
        if page == 1:
            if (
                (js := get_js(content, dict))
                and (total := get_int(js.get("total_items")))
                and (max_page_items := get_int(js.get("max_page_items")))
            ):
                self.contents = []
                self.total = total
                self.max_pages = total / max_page_items
                self.progress_step.set_total(self.max_pages)
                self.update_progress(CacheProgress(CacheProgressEvent.START))
        if not self.max_pages:
            logger.warning("Missing 1st page for %s cache", str(self.query))
            self.valid = False
            return False
        # logger.info("Page %s - total %s", page, self.max_pages)
        self.contents.append(content)
        if progress := self.progress_step.progress(page):
            self.update_progress(CacheProgress(CacheProgressEvent.SHOW, progress))
        return page >= self.max_pages

    @staticmethod
    def update_with_loaded(data_to_update: list[dict], loaded: MacCacheLoad) -> list[dict]:
        if (
            (js := get_js(loaded.content, dict))
            and (loaded_data := js.get("data"))
            and isinstance(loaded_data, list)
            and len(loaded_data) > len(data_to_update)
        ):
            ids = {id_: data for data in loaded_data if isinstance(data, dict) and (id_ := data.get("id"))}
            ids |= {id_: data for data in data_to_update if isinstance(data, dict) and (id_ := data.get("id"))}
            return list(ids.values())
        return data_to_update

    def save(self, loaded: Optional[MacCacheLoad]) -> None:
        def _save(file: IO[bytes]) -> None:
            data_to_save: list[dict] = []
            for content in self.contents:
                if (js := get_js(content, dict)) and (data := js.get("data")) and isinstance(data, list):
                    data_to_save.extend(data)
            # update with loaded if not complete
            not_complete = len(data_to_save) < self.total
            if not_complete and loaded and loaded.valid:
                data_to_save = self.update_with_loaded(data_to_save, loaded)
                timestamp = loaded.timestamp
            else:
                timestamp = time.time()
            actual = len(data_to_save)
            js = set_js(dict(max_page_items=actual, total_items=actual, data=data_to_save))
            content = json_encoder.encode(js)
            pickle.dump(self.total, file)
            pickle.dump(actual, file)
            pickle.dump(timestamp, file)
            pickle.dump(content, file)
            logger.info("Save Cache to '%s' (%s out of %s)", file.name, actual, self.total)

        self.update_progress(CacheProgress(CacheProgressEvent.STOP))
        if self.valid and self.total:
            self.open_and_do("wb", _save, pickle.PickleError, TypeError)


class AllCached(NamedTuple):
    complete: str
    today: str
    one_day: str
    several_days: str
    fast_cached: str
    all_names: dict[ValidMediaTypes, str] = {}
    all_updates: dict[ValidMediaTypes, str] = {}

    def title(self, loaded: MacCacheLoad) -> str:
        if loaded.complete < 1:
            percent = _in_beetween(round(loaded.complete * 100), 1, 99)
            missing_str = f"⚠️ {self.complete.format(percent=percent)}"
        else:
            missing_str = f"✔ {self.complete.format(percent=100)}"
        return (
            f"{self.all_names.get(loaded.query.type, '')} - {self.fast_cached.capitalize()}"
            f"\n{self._days_ago(loaded.timestamp)} {missing_str}"
        )

    def _days_ago(self, timestamp: float) -> str:
        days = int((time.time() - timestamp) / (3600 * 24))
        match days:
            case 0:
                return self.today
            case 1:
                return self.one_day
            case _:
                return self.several_days.format(days=days)


class MacCache(CacheCleaner):
    cached_all_category = "cached_all_category"
    cached_header = "ListCached"
    cached_header_bytes = cached_header.encode()
    clean_after_days = 30
    suffixes = MediaTypes
    all_category = "*"

    def __init__(self, roaming: Path, update_progress: UpdateCacheProgressT, all_cached: AllCached) -> None:
        super().__init__(roaming, MacCache.clean_after_days, *MacCache.suffixes)
        self._stop_all_job = JobRunner[bool](self._done_all, "Cache stop all job")
        self.saved_queries_lock = multiprocessing.Lock()
        self.saved_queries: dict[MacQuery, MacCacheSave] = {}
        self.loaded_queries: dict[MacQuery, MacCacheLoad] = {}
        self.update_progress = update_progress
        self.all_cached = all_cached

    async def save_response(self, flow: http.HTTPFlow) -> None:
        if (
            (response := flow.response)
            and get_query_key(flow, "category") == MacCache.all_category
            and (page := get_int(get_query_key(flow, "p")))
            and MacCache.cached_header_bytes not in response.headers
            and (query := MacQuery.get_from(flow))
        ):
            with self.saved_queries_lock:
                if query not in self.saved_queries:
                    self.saved_queries[query] = MacCacheSave(self.cache_dir, query, self.update_progress)
                if await self.saved_queries[query].update(response, page):
                    self._save(query)

    def _save(self, query: MacQuery) -> None:
        self.saved_queries[query].save(self.loaded_queries.get(query))
        del self.saved_queries[query]

    def done(self, flow: http.HTTPFlow) -> None:
        with self.saved_queries_lock:
            if (query := MacQuery.get_from(flow)) in self.saved_queries:
                logger.info("Stop creating Cache for %s", str(query))
                self._save(query)

    def _done_all(self, _) -> None:
        with self.saved_queries_lock:
            logger.info("Stop creating all Caches")
            for query in self.saved_queries.copy():
                self._save(query)

    def stop_all(self) -> None:
        self._stop_all_job.add_job(True)

    def start(self) -> None:
        self._stop_all_job.start()

    def stop(self) -> None:
        self._stop_all_job.stop()

    async def load_response(self, flow: http.HTTPFlow) -> None:
        if (
            get_query_key(flow, "category") == MacCache.cached_all_category
            and (query := MacQuery.get_from(flow))
            and (loaded := self.loaded_queries[query])
            and (loaded.valid)
        ):
            flow.response = http.Response.make(
                content=loaded.content,
                headers={
                    "Content-Type": "application/json",
                    MacCache.cached_header: "",
                },
            )

    def inject_all_cached_category(self, flow: http.HTTPFlow) -> None:
        # pylint: disable=too-many-boolean-expressions
        if (
            (response := flow.response)
            and (query := MacQuery.get_from(flow))
            and (categories := get_reponse_js(response, list))
            and (all_category := categories[0])
            and isinstance(all_category, dict)
            and (all_category.get("id") == MacCache.all_category)
        ):
            # clean queries for other servers
            for existing_query in self.loaded_queries.copy():
                if existing_query.server != query.server:
                    del self.loaded_queries[existing_query]
            # always update the loaded query since it might have changed
            loaded = self.loaded_queries[query] = MacCacheLoad(self.cache_dir, query)
            if loaded.valid:
                cached_all_category = dict(
                    censored=0,
                    alias=MacCache.all_category,
                    id=MacCache.cached_all_category,
                    title=self.all_cached.title(loaded),
                )
                categories.insert(1, cached_all_category)
                response.content = json_encoder.encode(set_js(categories))
