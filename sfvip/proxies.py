import socket
from typing import Iterable
from urllib.parse import urlparse

from proxy import Proxy
from sfvip_all_config import AllCat


class Proxies:
    """start a proxy for each upstream proxies ('' upstream proxy count as one)"""

    def __init__(self, all_cat: type[AllCat], upstreams: set[str]) -> None:
        self._upstreams = upstreams
        self._all_cat = all_cat
        self._proxies: list[Proxy] = []

    @staticmethod
    def _find_port(excluded_ports: tuple[int]) -> int:
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", 0))
                _, port = sock.getsockname()
                if port not in excluded_ports:
                    return port

    @staticmethod
    def _urls_to_ports(urls: Iterable[str]) -> list[int]:
        return [port for url in urls if isinstance(port := urlparse(url).port, int)]

    def __enter__(self) -> dict[str, str]:
        """launch only one proxy per upstream proxy"""
        excluded_ports = self._urls_to_ports(self._upstreams)
        proxies_by_upstreams: dict[str, str] = {}
        for upstream in self._upstreams:
            if upstream not in proxies_by_upstreams:
                port = self._find_port(excluded_ports)
                excluded_ports.append(port)
                proxies_by_upstreams[upstream] = f"http://127.0.0.1:{port}"
                proxy = Proxy(self._all_cat, port, upstream)
                self._proxies.append(proxy)
                proxy.start()
        return proxies_by_upstreams

    def __exit__(self, *_) -> None:
        for proxy in self._proxies:
            proxy.stop()
