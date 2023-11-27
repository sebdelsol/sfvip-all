import logging
import socket
from typing import Optional, Self
from urllib.parse import urlparse, urlsplit, urlunsplit

from translations.loc import LOC

from ..mitm import MitmLocalProxy, Mode, validate_upstream
from ..mitm.addon import AllCategoryName, SfVipAddOn
from ..winapi import mutex

logger = logging.getLogger(__name__)


class LocalproxyError(Exception):
    pass


def _find_port(excluded_ports: set[int], retry: int) -> int:
    for _ in range(retry):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("localhost", 0))
            port = sock.getsockname()[1]
            if port not in excluded_ports:
                excluded_ports.add(port)
                return port
            logging.warning("port %s already in use", port)
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


class LocalProxies:
    """start a local proxy for each upstream proxies (no upstream proxy count as one)"""

    _localhost = "http://127.0.0.1:{port}"
    _find_ports_retry = 10
    _mitmproxy_start_timeout = 5

    def __init__(self, inject_in_live: bool, upstreams: set[str]) -> None:
        self._all_name = AllCategoryName(
            live=LOC.AllChannels if inject_in_live else None,
            series=LOC.AllSeries,
            vod=LOC.AllMovies,
        )
        self._upstreams = upstreams
        self._by_upstreams: dict[str, str] = {}
        self._mitm_proxy: Optional[MitmLocalProxy] = None
        self._bind_free_ports = mutex.SystemWideMutex("bind free ports for local proxies")

    @property
    def by_upstreams(self) -> dict[str, str]:
        return self._by_upstreams

    def __enter__(self) -> Self:
        with self._bind_free_ports:
            if self._upstreams:
                modes: set[Mode] = set()
                excluded_ports = _ports_from(self._upstreams)
                for upstream in self._upstreams:
                    upstream_fixed = _fix_upstream(upstream)
                    if upstream_fixed is not None:
                        port = _find_port(excluded_ports, LocalProxies._find_ports_retry)
                        modes.add(Mode(port=port, upstream=upstream_fixed))
                        self._by_upstreams[upstream] = LocalProxies._localhost.format(port=port)
                if modes:
                    addon = SfVipAddOn(self._all_name)
                    self._mitm_proxy = MitmLocalProxy(addon, modes)
                    self._mitm_proxy.start()
                    # wait for proxies running so we're sure all ports are bound
                    if not addon.wait_running(LocalProxies._mitmproxy_start_timeout):
                        raise LocalproxyError(LOC.CantStartProxies)
            return self

    def __exit__(self, *_) -> None:
        if self._mitm_proxy:
            self._mitm_proxy.stop()
