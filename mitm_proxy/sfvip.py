# use separate named package to reduce what's imported by multiproccessing
import json
import logging
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


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    def __init__(self, all_category: AllCategory) -> None:
        def get_panel(name: str, streams: bool = True) -> Panel:
            return Panel(
                get_categories=f"get_{name}_categories",
                get_category=f"get_{name}{'_streams' if streams else ''}",
                all_category_name=all_category.name,
            )

        panels = [get_panel("vod"), get_panel("series", streams=False)]
        if all_category.inject_in_live:
            panels.append(get_panel("live"))
        self._category_panel = {panel.get_category: panel for panel in panels}
        self._categories_panel = {panel.get_categories: panel for panel in panels}

    @staticmethod
    def _is_api_request(request: http.Request) -> bool:
        return "player_api.php?" in request.path

    @staticmethod
    def _response_json(response: http.Response) -> Optional[Any]:
        if response and response.text and response.headers.get("content-type") == "application/json":
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _unused_category_id(categories: list[dict]) -> str:
        if ids := [
            int(cat_id)
            for category in categories
            if (cat_id := category.get("category_id")) is not None and isinstance(cat_id, (int, str))
        ]:
            return str(max(ids) + 1)
        return "0"

    @staticmethod
    def _log(msg: str, panel: Panel, action: str) -> None:
        txt = "%s category '%s' (id='%s') in response to '%s' api request"
        logger.info(txt, msg, panel.all_category_name, panel.all_category_id, action)

    @staticmethod
    def _query(request: http.Request) -> MultiDictView[str, str]:
        return getattr(request, "urlencoded_form" if request.method == "POST" else "query")

    def _remove_query_key(self, request: http.Request, key: str) -> None:
        del self._query(request)[key]

    def _get_query_key(self, request: http.Request, key: str) -> Optional[str]:
        return self._query(request).get(key, None)

    def request(self, flow: http.HTTPFlow) -> None:
        if self._is_api_request(flow.request):
            action = self._get_query_key(flow.request, "action")
            if action in self._category_panel:
                panel = self._category_panel[action]
                category_id = self._get_query_key(flow.request, "category_id")
                if category_id == panel.all_category_id:
                    # turn an all category query into a whole catalog query
                    self._remove_query_key(flow.request, "category_id")
                    self._log("serve", panel, action)

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            if self._is_api_request(flow.request):
                action = self._get_query_key(flow.request, "action")
                if action in self._categories_panel:
                    categories = self._response_json(flow.response)
                    if isinstance(categories, list):
                        # response with the all category injected @ first
                        panel = self._categories_panel[action]
                        panel.all_category_id = self._unused_category_id(categories)
                        categories.insert(
                            0,
                            dict(
                                category_id=panel.all_category_id,
                                category_name=panel.all_category_name,
                                parent_id=0,
                            ),
                        )
                        flow.response.text = json.dumps(categories)
                        self._log("inject", panel, action)

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self._is_api_request(flow.request):
            if flow.response:
                flow.response.stream = True
