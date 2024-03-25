# use separate named package to reduce what's imported by multiprocessing
import json
import logging
from pathlib import Path
from typing import NamedTuple, Optional
from urllib.parse import urlparse

from mitmproxy import http
from mitmproxy.proxy.server_hooks import ServerConnectionHookData

from ..cache import AllCached, MACCache, UpdateCacheProgressT
from ..epg import EPG, EpgCallbacks
from ..utils import APItype, get_query_key, response_json
from .all import AllCategoryName, AllPanels

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


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
            # already an epg ?
            if epg.prefer_updater.prefer_internal and (json_response := response_json(flow.response)):
                if isinstance(json_response, dict) and json_response.get(programmes):
                    return
            server = flow.request.host_header
            if _id := get_query_key(flow, stream_id):
                _limit = get_query_key(flow, limit)
                if _listing := epg.ask_epg(server, _id, _limit, api):
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
    _api = {
        "player_api.php": APItype.XC,
        "stalker_portal": APItype.MAC,
        "portal.php": APItype.MAC,
        "load.php": APItype.MAC,
    }

    def __init__(self, accounts_urls: set[str]) -> None:
        self.accounts_urls = accounts_urls

    async def __call__(self, flow: http.HTTPFlow) -> Optional[APItype]:
        request = flow.request
        if (components := request.path_components) and (api := ApiRequest._api.get(components[0])):
            return api
        return APItype.M3U if request.url in self.accounts_urls else None


class M3UStream:
    _disconnected_after = 0.5

    def __init__(self, epg: EPG) -> None:
        self.current_address: Optional[tuple[str | None, int | None]]
        self.current_urls: tuple[str, ...]
        self.current_started: float
        self.reinit()
        self.epg = epg

    def is_current(self, url: str) -> bool:
        return bool(self.current_urls and url in self.current_urls)

    def reinit(self) -> None:
        self.current_urls = ()
        self.current_address = None
        self.current_started = 0

    def start(self, flow: http.HTTPFlow) -> bool:
        if flow.response:
            url = flow.request.url
            # already started ?
            if not self.is_current(url):
                if self.epg.m3u_stream_started(url):
                    self.current_started = flow.timestamp_start
                    redirect = flow.response.headers.get(b"location")
                    if isinstance(redirect, str):
                        self.current_urls = url, redirect
                        try:
                            result = urlparse(redirect)
                            self.current_address = result.hostname, result.port
                        except ValueError:
                            self.current_address = flow.server_conn.ip_address
                    else:
                        self.current_urls = (url,)
                        self.current_address = flow.server_conn.ip_address
                    return True
        return False

    def stop(self, flow: http.HTTPFlow) -> bool:
        url = flow.request.url
        if self.is_current(url):
            self.epg.m3u_stream_stopped()
            self.reinit()
            return True
        return False

    def disconnect(self, data: ServerConnectionHookData) -> None:
        if self.current_address and (address := data.server.peername):
            if address == self.current_address:
                # do not stop if disconnected right away
                started = data.server.timestamp_start
                if started and started - self.current_started > M3UStream._disconnected_after:
                    self.epg.m3u_stream_stopped()
                    self.reinit()


class AddonAllConfig(NamedTuple):
    all_name: AllCategoryName
    all_cached: AllCached


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        accounts_urls: set[str],
        all_config: AddonAllConfig,
        roaming: Path,
        epg_callbacks: EpgCallbacks,
        update_progress: UpdateCacheProgressT,
        timeout: int,
    ) -> None:
        self.api_request = ApiRequest(accounts_urls)
        self.mac_cache = MACCache(roaming, update_progress, all_config.all_cached)
        self.epg = EPG(roaming, epg_callbacks, timeout)
        self.m3u_stream = M3UStream(self.epg)
        self.panels = AllPanels(all_config.all_name)

    def epg_update(self, url: str) -> None:
        self.epg.ask_update(url)

    def epg_confidence_update(self, confidence: int) -> None:
        self.epg.update_confidence(confidence)

    def epg_prefer_update(self, prefer_internal: bool) -> None:
        self.epg.update_prefer(prefer_internal)

    def running(self) -> None:
        self.epg.start()

    def done(self) -> None:
        self.epg.stop()

    def wait_running(self, timeout: int) -> bool:
        return self.epg.wait_running(timeout)

    async def request(self, flow: http.HTTPFlow) -> None:
        # logger.debug("REQUEST %s", flow.request.pretty_url)
        if api := await self.api_request(flow):
            match api, get_query_key(flow, "action"):
                case APItype.MAC, "get_ordered_list":
                    await self.mac_cache.load_response(flow)
                case APItype.MAC, _:
                    self.mac_cache.stop(flow)
                case APItype.XC, action if action:
                    self.panels.serve_all(flow, action)

    async def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        # logger.debug("STREAM %s", flow.request.pretty_url)
        if not await self.api_request(flow):
            if flow.response:
                flow.response.stream = True

    async def response(self, flow: http.HTTPFlow) -> None:
        # logger.debug("RESPONSE %s %s", flow.request.pretty_url, flow.response and flow.response.status_code)
        if not flow.response:
            return
        if not flow.response.stream:
            if api := await self.api_request(flow):
                match api, get_query_key(flow, "action"):
                    case APItype.MAC, "get_ordered_list":
                        await self.mac_cache.save_response(flow)
                    case APItype.MAC, "get_short_epg":
                        get_short_epg(flow, self.epg, api)
                    case APItype.MAC, "get_all_channels":
                        set_epg_server(flow, self.epg, api)
                    case APItype.MAC, "get_categories":
                        self.mac_cache.inject_all_cached_category(flow)
                    case APItype.XC, "get_series_info":
                        fix_series_info(flow.response)
                    case APItype.XC, "get_live_streams":
                        set_epg_server(flow, self.epg, api)
                    case APItype.XC, "get_short_epg" if not get_query_key(flow, "category_id"):
                        get_short_epg(flow, self.epg, api)
                    case APItype.XC, action if action:
                        self.panels.inject_all(flow, action)
                    case APItype.M3U, _:
                        set_epg_server(flow, self.epg, api)
        else:
            self.m3u_stream.start(flow)
            self.mac_cache.stop_all()

    # TODO progress for MAC Cache not hiding !! nee to call self.mac_cache.stop_all(), but where?
    async def error(self, flow: http.HTTPFlow) -> None:
        # logger.debug("ERROR %s", flow.request.pretty_url)
        if not self.m3u_stream.stop(flow):
            if api := await self.api_request(flow):
                match api, get_query_key(flow, "action"):
                    case APItype.MAC, "get_ordered_list":
                        self.mac_cache.stop(flow)

    def server_disconnected(self, data: ServerConnectionHookData) -> None:
        # logger.debug("DISCONNECT %s %s", data.server.peername, data.server.transport_protocol)
        self.m3u_stream.disconnect(data)
