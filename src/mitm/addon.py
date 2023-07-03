# use separate named package to reduce what's imported by multiprocessing
import json
import logging
import multiprocessing
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView

logger = logging.getLogger(__name__)


class AllCategory(Protocol):
    name: str
    inject_in_live: bool


@dataclass
class Panel:
    get_categories: str
    get_category: str
    all_category_name: str
    all_category_id: str = "0"


def _is_api_request(request: http.Request) -> bool:
    return "player_api.php?" in request.path


def _query(request: http.Request) -> MultiDictView[str, str]:
    return getattr(request, "urlencoded_form" if request.method == "POST" else "query")


def _del_query_key(request: http.Request, key: str) -> None:
    del _query(request)[key]


def _get_query_key(request: http.Request, key: str) -> Optional[str]:
    return _query(request).get(key)


def _response_json(response: http.Response) -> Optional[Any]:
    if response and response.text and response.headers.get("content-type") == "application/json":
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return None
    return None


def _unused_category_id(categories: list[dict]) -> str:
    if ids := [
        int(cat_id)
        for category in categories
        if (cat_id := category.get("category_id")) is not None and isinstance(cat_id, (int, str))
    ]:
        return str(max(ids) + 1)
    return "0"


def _log(verb: str, panel: Panel, action: str) -> None:
    txt = "%s category '%s' (id=%s) for '%s' request"
    logger.info(txt, verb, panel.all_category_name, panel.all_category_id, action)


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    def __init__(self, all_category: AllCategory) -> None:
        def get_panel(name: str, streams: bool = True) -> Panel:
            return Panel(
                get_categories=f"get_{name}_categories",
                get_category=f"get_{name}{'_streams' if streams else ''}",
                all_category_name=all_category.name,
            )

        panels = get_panel("vod"), get_panel("series", streams=False)
        if all_category.inject_in_live:
            panels = *panels, get_panel("live")
        self._category_panel = {panel.get_category: panel for panel in panels}
        self._categories_panel = {panel.get_categories: panel for panel in panels}
        self._running = multiprocessing.Event()

    def running(self) -> None:
        self._running.set()

    def wait_running(self, timeout: Optional[float] = None) -> bool:
        return self._running.wait(timeout)

    def request(self, flow: http.HTTPFlow) -> None:
        if _is_api_request(flow.request):
            action = _get_query_key(flow.request, "action")
            if action in self._category_panel:
                panel = self._category_panel[action]
                category_id = _get_query_key(flow.request, "category_id")
                if category_id == panel.all_category_id:
                    # turn an all category query into a whole catalog query
                    _del_query_key(flow.request, "category_id")
                    _log("serve", panel, action)

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            if _is_api_request(flow.request):
                action = _get_query_key(flow.request, "action")
                if action in self._categories_panel:
                    categories = _response_json(flow.response)
                    if isinstance(categories, list):
                        # response with the all category injected @ the beginning
                        panel = self._categories_panel[action]
                        panel.all_category_id = _unused_category_id(categories)
                        all_category = dict(
                            category_id=panel.all_category_id,
                            category_name=panel.all_category_name,
                            parent_id=0,
                        )
                        categories.insert(0, all_category)
                        flow.response.text = json.dumps(categories)
                        _log("inject", panel, action)

    def responseheaders(self, flow: http.HTTPFlow) -> None:  # pylint: disable=no-self-use
        """all reponses are streamed except the api requests"""
        if not _is_api_request(flow.request):
            if flow.response:
                flow.response.stream = True
