# use separate named package to reduce what's imported by multiprocessing
import json
import logging
from pathlib import Path
from typing import Optional

from mitmproxy import http

from ..cache import AllUpdated, MACCache, UpdateCacheProgressT
from ..epg import EPG, ChannelFoundT, UpdateStatusT
from ..utils import APIRequest, Request, get_query_key, response_json
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


def get_short_epg(flow: http.HTTPFlow, epg: EPG, api: APIRequest) -> None:
    if response := flow.response:

        def _get(stream_id: str, limit: str, listing: str):
            if _id := get_query_key(flow.request, stream_id):
                _limit = get_query_key(flow.request, limit)
                if _listing := epg.get(server, _id, _limit, api):
                    response.text = json.dumps({listing: _listing})

        server = flow.request.host_header
        match api:
            case APIRequest.XC:
                _get("stream_id", "limit", "epg_listings")
            case APIRequest.MAC:
                _get("ch_id", "size", "js")


def set_epg_server(flow: http.HTTPFlow, epg: EPG, api: APIRequest) -> None:
    server = flow.request.host_header
    epg.set_server_channels(server, response_json(flow.response), api)


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        all_name: AllCategoryName,
        all_updated: AllUpdated,
        roaming: Path,
        update_status: UpdateStatusT,
        channel_found: ChannelFoundT,
        update_progress: UpdateCacheProgressT,
        timeout: int,
    ) -> None:
        self.mac_cache = MACCache(roaming, update_progress, all_updated)
        self.epg = EPG(update_status, channel_found, timeout)
        self.panels = AllPanels(all_name)

    def epg_update(self, url: str):
        self.epg.ask_update(url)

    def epg_confidence_update(self, confidence: int):
        self.epg.update_confidence(confidence)

    def running(self) -> None:
        self.epg.start()

    def done(self) -> None:
        self.epg.stop()

    def wait_running(self, timeout: int) -> bool:
        return self.epg.wait_running(timeout)

    async def request(self, flow: http.HTTPFlow) -> None:
        if request := Request.is_api(flow.request):
            match request:
                case APIRequest.MAC, "get_ordered_list":
                    self.mac_cache.load_response(flow)
                case _:
                    self.mac_cache.stop(flow)
                    if request.action:
                        self.panels.serve_all(flow, request.action)

    async def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            if request := Request.is_api(flow.request):
                match request:
                    case APIRequest.MAC, "get_short_epg":
                        get_short_epg(flow, self.epg, APIRequest.MAC)
                    case APIRequest.MAC, "get_all_channels":
                        set_epg_server(flow, self.epg, APIRequest.MAC)
                    case APIRequest.MAC, "get_ordered_list":
                        self.mac_cache.save_response(flow)
                    case APIRequest.MAC, "get_categories":
                        self.mac_cache.inject_all_cached_category(flow)
                    case APIRequest.XC, "get_series_info":
                        fix_series_info(flow.response)
                    case APIRequest.XC, "get_live_streams":
                        set_epg_server(flow, self.epg, APIRequest.XC)
                    case APIRequest.XC, "get_short_epg" if not get_query_key(flow.request, "category_id"):
                        get_short_epg(flow, self.epg, APIRequest.XC)
                    case APIRequest.XC, action if action:
                        self.panels.inject_all(flow, action)

    async def error(self, flow: http.HTTPFlow):
        if request := Request.is_api(flow.request):
            match request:
                case APIRequest.MAC, "get_ordered_list":
                    self.mac_cache.stop(flow)

    @staticmethod
    async def responseheaders(flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not Request.is_api(flow.request):
            if flow.response:
                flow.response.stream = True
