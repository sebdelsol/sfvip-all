# use separate named package to reduce what's imported by multiprocessing
import json
import logging
from pathlib import Path
from typing import NamedTuple, Optional, Sequence

from mitmproxy import http

from ..cache import AllUpdated, MACCache, UpdateCacheProgressT
from ..epg import EPG, ChannelFoundT, ShowEpgT, UpdateStatusT
from ..utils import APItype, get_query_key, response_json
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


def get_short_epg(flow: http.HTTPFlow, epg: EPG, api: APItype) -> None:
    if response := flow.response:

        def set_response(stream_id: str, limit: str, programmes: str) -> None:
            server = flow.request.host_header
            if _id := get_query_key(flow.request, stream_id):
                _limit = get_query_key(flow.request, limit)
                if _listing := epg.ask_stream(server, _id, _limit, api):
                    response.text = json.dumps({programmes: _listing})

        match api:
            case APItype.XC:
                set_response("stream_id", "limit", "epg_listings")
            case APItype.MAC:
                set_response("ch_id", "size", "js")


def set_epg_server(flow: http.HTTPFlow, epg: EPG, api: APItype) -> None:
    server = flow.request.host_header
    match api:
        case APItype.XC | APItype.MAC:
            epg.set_server_channels(server, response_json(flow.response), api)
        case APItype.M3U:
            if flow.response and (content := flow.response.text):
                epg.set_server_channels(server, content, api)


class ApiRequest:
    _api = {"portal.php?": APItype.MAC, "player_api.php?": APItype.XC}

    def __init__(self, urls: set[str]) -> None:
        self.urls = urls

    def __call__(self, request: http.Request) -> Optional[APItype]:
        for request_part, api in ApiRequest._api.items():
            if request_part in request.path:
                return api
        return APItype.M3U if request.url in self.urls else None


class AddonCallbacks(NamedTuple):
    update_status: UpdateStatusT
    channel_found: ChannelFoundT
    show_epg: ShowEpgT
    update_progress: UpdateCacheProgressT


class AddonAllConfig(NamedTuple):
    all_name: AllCategoryName
    all_updated: AllUpdated


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        accounts_urls: set[str],
        all_config: AddonAllConfig,
        roaming: Path,
        callbacks: AddonCallbacks,
        timeout: int,
    ) -> None:
        self.api_request = ApiRequest(accounts_urls)
        self.mac_cache = MACCache(roaming, callbacks.update_progress, all_config.all_updated)
        self.epg = EPG(callbacks.update_status, callbacks.channel_found, callbacks.show_epg, timeout)
        self.panels = AllPanels(all_config.all_name)

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
        if not self.epg.ask_m3u_stream(flow.request.host_header, flow.request.url):
            if api := self.api_request(flow.request):
                match api, get_query_key(flow.request, "action"):
                    case APItype.MAC, "get_ordered_list":
                        self.mac_cache.load_response(flow)
                    case APItype.MAC, _:
                        self.mac_cache.stop(flow)
                    case APItype.XC, action if action:
                        self.panels.serve_all(flow, action)

    async def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and not flow.response.stream:
            # print(flow.request.pretty_url)
            if api := self.api_request(flow.request):
                match api, get_query_key(flow.request, "action"):
                    case APItype.M3U, _:
                        set_epg_server(flow, self.epg, api)
                    case APItype.MAC, "get_short_epg":
                        get_short_epg(flow, self.epg, api)
                    case APItype.MAC, "get_all_channels":
                        set_epg_server(flow, self.epg, api)
                    case APItype.MAC, "get_ordered_list":
                        self.mac_cache.save_response(flow)
                    case APItype.MAC, "get_categories":
                        self.mac_cache.inject_all_cached_category(flow)
                    case APItype.XC, "get_series_info":
                        fix_series_info(flow.response)
                    case APItype.XC, "get_live_streams":
                        set_epg_server(flow, self.epg, api)
                    case APItype.XC, "get_short_epg" if not get_query_key(flow.request, "category_id"):
                        get_short_epg(flow, self.epg, api)
                    case APItype.XC, action if action:
                        self.panels.inject_all(flow, action)

    async def error(self, flow: http.HTTPFlow):
        if api := self.api_request(flow.request):
            # print("ERROR", flow.request.pretty_url)
            match api, get_query_key(flow.request, "action"):
                case APItype.MAC, "get_ordered_list":
                    self.mac_cache.stop(flow)

    async def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self.api_request(flow.request):
            if flow.response:
                flow.response.stream = True
