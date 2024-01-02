# use separate named package to reduce what's imported by multiprocessing
import json
import logging
from pathlib import Path
from typing import Optional

from mitmproxy import http

from ..cache import AllUpdated, MACCache, UpdateCacheProgressT
from ..epg import EPG, UpdateStatusT
from ..utils import get_query_key, response_json
from .all import AllCategoryName, AllPanels

logger = logging.getLogger(__name__)


def fix_series_info(response: http.Response) -> None:
    if (
        response
        and (info := response_json(response))
        and isinstance(info, dict)
        and (episodes := info.get("episodes"))
    ):
        # fix episode list : Xtream code api recommend a dictionary
        if isinstance(episodes, list):
            info["episodes"] = {str(season[0]["season"]): season for season in episodes}
            logger.info("Fix serie info")
            response.text = json.dumps(info)


def get_short_epg(flow: http.HTTPFlow, epg: EPG) -> None:
    if (response := flow.response) and (stream_id := get_query_key(flow.request, "stream_id")):
        server = flow.request.host_header
        limit = get_query_key(flow.request, "limit")
        if epg_listings := tuple(epg.get(server, stream_id, limit)):
            response.text = json.dumps({"epg_listings": epg_listings})


def set_epg_server(flow: http.HTTPFlow, epg: EPG) -> None:
    if not get_query_key(flow.request, "category_id"):
        server = flow.request.host_header
        epg.set_server_channels(server, response_json(flow.response))


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    _api_requests = "player_api.php?", "portal.php?"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        all_name: AllCategoryName,
        all_updated: AllUpdated,
        roaming: Path,
        update_status: UpdateStatusT,
        update_progress: UpdateCacheProgressT,
        timeout: int,
    ) -> None:
        self.mac_cache = MACCache(roaming, update_progress, all_updated)
        self.epg = EPG(update_status, timeout)
        self.panels = AllPanels(all_name)

    def epg_update(self, url: str):
        self.epg.ask_update(url)

    def running(self) -> None:
        self.epg.start()

    def done(self) -> None:
        self.epg.stop()

    def wait_running(self, timeout: int) -> bool:
        return self.epg.wait_running(timeout)

    @staticmethod
    def is_api_request(request: http.Request) -> Optional[str]:
        if any(api_request in request.path for api_request in SfVipAddOn._api_requests):
            return get_query_key(request, "action")
        return None

    async def request(self, flow: http.HTTPFlow) -> None:
        if action := self.is_api_request(flow.request):
            match action:
                case "get_ordered_list":
                    self.mac_cache.load_response(flow)
                case _:
                    self.mac_cache.stop(flow)
                    self.panels.serve_all(flow, action)

    async def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            if action := self.is_api_request(flow.request):
                match action:
                    case "get_series_info":
                        fix_series_info(flow.response)
                    case "get_live_streams":
                        set_epg_server(flow, self.epg)
                    case "get_short_epg":
                        get_short_epg(flow, self.epg)
                    case "get_ordered_list":
                        self.mac_cache.save_response(flow)
                    case "get_categories":
                        self.mac_cache.inject_all_cached_category(flow)
                    case _:
                        self.panels.inject_all(flow, action)

    async def error(self, flow: http.HTTPFlow):
        if self.is_api_request(flow.request) == "get_ordered_list":
            self.mac_cache.stop(flow)

    async def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self.is_api_request(flow.request):
            if flow.response:
                flow.response.stream = True
