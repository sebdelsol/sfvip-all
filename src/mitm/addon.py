# use separate named package to reduce what's imported by multiprocessing
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple, Optional

from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView

from .cache import StalkerCache
from .epg import EPG, UpdateStatusT

logger = logging.getLogger(__name__)


class AllCategoryName(NamedTuple):
    live: Optional[str]
    vod: str
    series: str


@dataclass
class Panel:
    get_categories: str
    get_category: str
    all_category_name: str
    all_category_id: str = "0"


class PanelType(Enum):
    LIVE = "live"
    VOD = "vod"
    SERIES = "series"


def get_panel(panel_type: PanelType, all_category_name: str, streams: bool = True) -> Panel:
    return Panel(
        get_categories=f"get_{panel_type.value}_categories",
        get_category=f"get_{panel_type.value}{'_streams' if streams else ''}",
        all_category_name=all_category_name,
    )


def _query(request: http.Request) -> MultiDictView[str, str]:
    return getattr(request, "urlencoded_form" if request.method == "POST" else "query")


def _del_query_key(request: http.Request, key: str) -> None:
    del _query(request)[key]


def _get_query_key(request: http.Request, key: str) -> Optional[str]:
    return _query(request).get(key)


def _response_json(response: http.Response) -> Optional[Any]:
    if response and response.text and "application/json" in response.headers.get("content-type", ""):
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
    logger.info(txt.capitalize(), verb.capitalize(), panel.all_category_name, panel.all_category_id, action)


def fix_info_serie(info: Any) -> Optional[dict[str, Any]]:
    if isinstance(info, dict):
        if episodes := info.get("episodes"):
            # fix episode list : Xtream code api recommend a dictionary
            if isinstance(episodes, list):
                info["episodes"] = {str(season[0]["season"]): season for season in episodes}
                logger.info("Fix serie info")
                return info
    return None


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    api_requests = "player_api.php?", "portal.php?"

    def __init__(
        self, all_name: AllCategoryName, roaming: Path, update_status: UpdateStatusT, timeout: int
    ) -> None:
        panels = [
            get_panel(PanelType.VOD, all_name.vod),
            get_panel(PanelType.SERIES, all_name.series, streams=False),
        ]
        if all_name.live:
            panels.append(get_panel(PanelType.LIVE, all_name.live))
        self._category_panel = {panel.get_category: panel for panel in panels}
        self._categories_panel = {panel.get_categories: panel for panel in panels}
        self.cache: StalkerCache | None = StalkerCache(roaming)
        self.epg = EPG(update_status, timeout)

    def epg_update(self, url: str):
        self.epg.ask_update(url)

    def running(self) -> None:
        self.epg.start()

    def done(self) -> None:
        self.epg.stop()

    def wait_running(self, timeout: int) -> bool:
        return self.epg.wait_running(timeout)

    @staticmethod
    def is_api_request(request: http.Request) -> bool:
        return any(api_request in request.path for api_request in SfVipAddOn.api_requests)

    def inject_all(self, categories: Any, action: str) -> Optional[list[Any]]:
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
            _log("inject", panel, action)
            return categories
        return None

    def request(self, flow: http.HTTPFlow) -> None:
        if self.is_api_request(flow.request):
            match action := _get_query_key(flow.request, "action"):
                case "get_ordered_list":
                    if self.cache and (response := self.cache.load_response(flow)):
                        flow.response = response
                case action if action in self._category_panel:
                    panel = self._category_panel[action]
                    category_id = _get_query_key(flow.request, "category_id")
                    if category_id == panel.all_category_id:
                        # turn an all category query into a whole catalog query
                        _del_query_key(flow.request, "category_id")
                        _log("serve", panel, action)

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            if self.is_api_request(flow.request):
                match action := _get_query_key(flow.request, "action"):
                    case "get_ordered_list":
                        if self.cache:
                            self.cache.save_response(flow)
                    case "get_series_info":
                        info = _response_json(flow.response)
                        if fixed_info := fix_info_serie(info):
                            flow.response.text = json.dumps(fixed_info)
                    case "get_live_streams":
                        category_id = _get_query_key(flow.request, "category_id")
                        if not category_id:
                            server = flow.request.host_header
                            self.epg.set_server_channels(server, _response_json(flow.response))
                    case "get_short_epg":
                        if stream_id := _get_query_key(flow.request, "stream_id"):
                            server = flow.request.host_header
                            limit = _get_query_key(flow.request, "limit")
                            if epg_listings := tuple(self.epg.get(server, stream_id, limit)):
                                flow.response.text = json.dumps({"epg_listings": epg_listings})
                    case action if action in self._categories_panel:
                        categories = _response_json(flow.response)
                        if all_injected := self.inject_all(categories, action):
                            flow.response.text = json.dumps(all_injected)

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self.is_api_request(flow.request):
            if flow.response:
                flow.response.stream = True
