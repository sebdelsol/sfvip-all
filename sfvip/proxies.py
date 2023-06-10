import socket
from typing import Optional, Self
from urllib.parse import urlparse, urlsplit, urlunsplit

from mitm_proxy import MitmLocalProxy, Mode, validate_upstream
from mitm_proxy.addon import AllCategory, SfVipAddOn


def _find_port(excluded_ports: set[int]) -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("localhost", 0))
            _, port = sock.getsockname()
            if port not in excluded_ports:
                return port


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

    _localhost = "http://127.0.0.1"

    def __init__(self, all_category: AllCategory, upstreams: set[str]) -> None:
        self._all_category = all_category
        self._upstreams = upstreams
        self._by_upstreams: dict[str, str] = {}
        self._mitm_proxy: Optional[MitmLocalProxy] = None

    @property
    def by_upstreams(self) -> dict[str, str]:
        return self._by_upstreams

    def __enter__(self) -> Self:
        if self._upstreams:
            modes: set[Mode] = set()
            excluded_ports = _ports_from(self._upstreams)
            for upstream in self._upstreams:
                upstream_fixed = _fix_upstream(upstream)
                if upstream_fixed is not None:
                    port = _find_port(excluded_ports)
                    excluded_ports.add(port)
                    modes.add(Mode(port=port, upstream=upstream_fixed))
                    self._by_upstreams[upstream] = f"{LocalProxies._localhost}:{port}"
            if modes:
                self._mitm_proxy = MitmLocalProxy(SfVipAddOn(self._all_category), modes)
                self._mitm_proxy.start()
        return self

    def __exit__(self, *_) -> None:
        if self._mitm_proxy:
            self._mitm_proxy.stop()
