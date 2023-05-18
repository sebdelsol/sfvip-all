import socket
from typing import Self
from urllib.parse import urlparse

from proxy import LocalProxy
from sfvip_all_config import AllCat


class LocalProxies:
    """start a local proxy for each upstream proxies (no upstream proxy count as one)"""

    def __init__(self, all_cat: type[AllCat], upstreams: set[str]) -> None:
        self._all_cat = all_cat
        self._upstreams = upstreams
        self._proxies: list[LocalProxy] = []
        self.by_upstreams: dict[str, str] = {}

    @staticmethod
    def _find_port(excluded_ports: set[int]) -> int:
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", 0))
                _, port = sock.getsockname()
                if port not in excluded_ports:
                    return port

    def __enter__(self) -> Self:
        """launch only one local proxy per upstream proxy"""
        excluded_ports = {port for url in self._upstreams if isinstance(port := urlparse(url).port, int)}
        for upstream in self._upstreams:
            port = self._find_port(excluded_ports)
            excluded_ports.add(port)
            self.by_upstreams[upstream] = f"http://127.0.0.1:{port}"
            proxy = LocalProxy(self._all_cat, port, upstream)
            self._proxies.append(proxy)
            proxy.start()
        for proxy in self._proxies:
            proxy.wait_for_init_done()
        return self

    def __exit__(self, *_) -> None:
        for proxy in self._proxies:
            proxy.stop()
