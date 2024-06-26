import logging
import socket
from typing import Optional, Self
from urllib.parse import urlparse, urlsplit, urlunsplit

from translations.loc import LOC

from ..mitm.addon import AddonAllConfig, AllCategoryName, EpgCallbacks, SfVipAddOn
from ..mitm.cache import AllCached
from ..mitm.proxies import MitmLocalProxy, Mode, validate_upstream
from ..winapi import mutex
from .accounts import AccountsProxies
from .app_info import AppInfo
from .cache import CacheProgressListener
from .epg import EpgUpdater, EPGUpdates
from .exceptions import LocalproxyError
from .player import PlayerCapabilities
from .ui import UI

logger = logging.getLogger(__name__)


def _find_port(excluded_ports: set[int], retry: int) -> int:
    for _ in range(retry):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("localhost", 0))
            port = sock.getsockname()[1]
            if port not in excluded_ports:
                excluded_ports.add(port)
                return port
            logger.warning("port %s already in use", port)
    raise LocalproxyError(LOC.NoSocketPort)


def _ports_from(urls: set[str]) -> set[int]:
    def _port(url: str) -> Optional[int]:
        try:
            return urlparse(url).port
        except ValueError:
            return None

    return {port for url in urls if (port := _port(url)) is not None}


def _fix_upstream(url: str) -> Optional[str]:
    if not url or url.isspace():
        return ""
    url = urlunsplit(urlsplit(url)).replace("///", "//")
    if validate_upstream(url):
        return url
    return None


def get_all_config(player_capabilities: PlayerCapabilities) -> AddonAllConfig:
    return AddonAllConfig(
        AllCategoryName(
            live=None if player_capabilities.has_all_channels else LOC.AllChannels,
            series=None if player_capabilities.has_all_categories else LOC.AllSeries,
            vod=None if player_capabilities.has_all_categories else LOC.AllMovies,
        ),
        AllCached(
            complete=LOC.Complete,
            today=LOC.UpdatedToday,
            one_day=LOC.Updated1DayAgo,
            several_days=LOC.UpdatedDaysAgo,
            fast_cached=LOC.FastCached,
            all_names={"vod": LOC.AllMovies, "series": LOC.AllSeries},
        ),
    )


class LocalProxies:
    """start a local proxy for each upstream proxies (no upstream proxy count as one)"""

    _localhost = "http://127.0.0.1:{port}"
    _mitmproxy_start_timeout = 10
    _find_ports_retry = 10

    def __init__(
        self, app_info: AppInfo, player_capabilities: PlayerCapabilities, accounts_proxies: AccountsProxies, ui: UI
    ) -> None:
        self._epg_updater = EpgUpdater(
            app_info.config,
            EPGUpdates(
                self.epg_confidence_update,
                self.epg_prefer_update,
                self.epg_update,
            ),
            ui,
        )
        self._cache_progress = CacheProgressListener(ui, self.cache_stop_all)
        self._addon = SfVipAddOn(
            accounts_proxies.urls,
            get_all_config(player_capabilities),
            app_info.roaming,
            EpgCallbacks(
                self._epg_updater.update_status,
                self._epg_updater.add_show_channel,
                self._epg_updater.add_show_epg,
            ),
            self._cache_progress.update_progress,
            app_info.config.EPG.requests_timeout,
        )
        self._upstreams = accounts_proxies.upstreams
        self._by_upstreams: dict[str, str] = {}
        self._mitm_proxy: Optional[MitmLocalProxy] = None
        self._bind_free_ports = mutex.SystemWideMutex("bind free ports for local proxies")

    @property
    def by_upstreams(self) -> dict[str, str]:
        return self._by_upstreams

    def cache_stop_all(self) -> None:
        self._addon.cache_stop_all()

    def epg_update(self, url: str) -> None:
        self._addon.epg_update(url)

    def epg_confidence_update(self, confidence: int) -> None:
        self._addon.epg_confidence_update(confidence)

    def epg_prefer_update(self, prefer_internal: bool) -> None:
        self._addon.epg_prefer_update(prefer_internal)

    def __enter__(self) -> Self:
        with self._bind_free_ports:
            modes: set[Mode] = set()
            if self._upstreams:
                excluded_ports = _ports_from(self._upstreams)
                for upstream in self._upstreams:
                    upstream_fixed = _fix_upstream(upstream)
                    if upstream_fixed is not None:
                        port = _find_port(excluded_ports, LocalProxies._find_ports_retry)
                        modes.add(Mode(port=port, upstream=upstream_fixed))
                        self._by_upstreams[upstream] = LocalProxies._localhost.format(port=port)
            self._mitm_proxy = MitmLocalProxy(self._addon, modes)
            self._mitm_proxy.start()
            # wait for proxies running so we're sure all ports are bound
            if not self._mitm_proxy.wait_running(LocalProxies._mitmproxy_start_timeout):
                raise LocalproxyError(LOC.CantStartProxies)
            self._epg_updater.start()
            self._cache_progress.start()
            return self

    def __exit__(self, *_) -> None:
        if self._mitm_proxy:
            self._cache_progress.stop()
            self._epg_updater.stop()
            self._mitm_proxy.stop()
