import socket
from typing import Self
from urllib.parse import urlparse, urlsplit, urlunsplit

from mitm_proxy import MitmLocalProxy, Mode, validate_upstream
from mitm_proxy.sfvip import AllCat, SfVipAddOn


class LocalProxies:
    """start a local proxy for each upstream proxies (no upstream proxy count as one)"""

    def __init__(self, all_cat: AllCat, upstreams: set[str]) -> None:
        self._all_cat = all_cat
        self._upstreams = upstreams
        self._by_upstreams: dict[str, str] = {}
        self._mitm_proxy: MitmLocalProxy | None = None

    @property
    def by_upstreams(self) -> dict[str, str]:
        return self._by_upstreams

    @staticmethod
    def _find_port(excluded_ports: set[int]) -> int:
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", 0))
                _, port = sock.getsockname()
                if port not in excluded_ports:
                    return port

    @staticmethod
    def _ports_from(urls: set[str]) -> set[int]:
        def _port(url: str) -> int | None:
            try:
                return urlparse(url).port
            except ValueError:
                return None

        return {port for url in urls if (port := _port(url)) is not None}

    @staticmethod
    def _fix_upstream(url: str) -> str | None:
        if not url or url.isspace():
            return ""
        url = urlunsplit(urlsplit(url)).replace("///", "//")
        if validate_upstream(url):
            return url
        return None

    def __enter__(self) -> Self:
        if self._upstreams:
            modes: set[Mode] = set()
            excluded_ports = self._ports_from(self._upstreams)
            for upstream in self._upstreams:
                upstream_fixed = self._fix_upstream(upstream)
                if upstream_fixed is not None:
                    port = self._find_port(excluded_ports)
                    excluded_ports.add(port)
                    modes.add(Mode(port=port, upstream=upstream_fixed))
                    self._by_upstreams[upstream] = f"http://127.0.0.1:{port}"
            if modes:
                self._mitm_proxy = MitmLocalProxy(SfVipAddOn(self._all_cat), modes)
                self._mitm_proxy.start()
        return self

    def __exit__(self, *_) -> None:
        if self._mitm_proxy:
            self._mitm_proxy.stop()
