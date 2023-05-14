import asyncio
import json
import re
import socket
import threading
from typing import Any, Optional, Self
from urllib.parse import urlparse

from mitmproxy import http, options
from mitmproxy.coretypes.multidict import MultiDictView
from mitmproxy.tools.dump import DumpMaster

from sfvip_all_config import AllCat

from .users import Users


class _AddOn:
    """mitmproxy addon to inject the all category"""

    def __init__(self, all_cat: type[AllCat]) -> None:
        inject_in_re = "|".join(re.escape(what) for what in all_cat.inject)
        self._is_action_get_categories = re.compile(f"get_({inject_in_re})_categories").search
        self._all_cat_id = str(all_cat.id)
        self._all_cat_json = dict(category_id=str(all_cat.id), category_name=all_cat.name, parent_id=0)

    @staticmethod
    def _is_api_request(request: http.Request) -> bool:
        return "player_api.php?" in request.path

    @staticmethod
    def _response_json(response: http.Response) -> Optional[Any]:
        if response and response.text and response.headers.get("content-type") == "application/json":
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _query(request: http.Request) -> MultiDictView[str, str]:
        return getattr(request, "urlencoded_form" if request.method == "POST" else "query")

    def _remove_query_key(self, request: http.Request, key: str) -> None:
        del self._query(request)[key]

    def _api_query(self, request: http.Request, key: str) -> Optional[str]:
        return self._query(request).get(key, None) if self._is_api_request(request) else None

    def request(self, flow: http.HTTPFlow) -> None:
        category_id = self._api_query(flow.request, "category_id")
        if category_id is not None and category_id == self._all_cat_id:
            # turn an all category query into a whole catalog query
            self._remove_query_key(flow.request, "category_id")

    def response(self, flow: http.HTTPFlow) -> None:
        action = self._api_query(flow.request, "action")
        if action is not None and self._is_action_get_categories(action):
            if categories := self._response_json(flow.response):
                if isinstance(categories, list):
                    # response with the all category injected @ first
                    categories = self._all_cat_json, *categories
                    flow.response.text = json.dumps(categories)

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self._is_api_request(flow.request):
            flow.response.stream = True


class Proxy:
    """run a mitmdump in a thread"""

    def __init__(self, addon: _AddOn, port: int, upstream_proxy: str) -> None:
        self._master: Optional[DumpMaster] = None
        init_done = threading.Event()
        target, *args = asyncio.run, self._run(addon, port, upstream_proxy, init_done)
        self._thread = threading.Thread(target=target, args=args)
        self._thread.start()
        init_done.wait()

    async def _run(self, addon: _AddOn, port: int, upstream_proxy: str, init_done: threading.Event) -> None:
        mode = f"upstream:{upstream_proxy}" if upstream_proxy else "regular"
        opts = options.Options(listen_port=port, ssl_insecure=True, mode=(mode,))
        self._master = master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        master.addons.add(addon)
        init_done.set()
        await master.run()

    def stop(self) -> None:
        self._master.shutdown()
        self._thread.join()


class Proxies:
    """start a proxy for each upstream proxies (no upstream proxy count as one)"""

    def __init__(self, all_cat: type[AllCat], users: Users) -> None:
        self._users = users
        self._addon = _AddOn(all_cat)
        self._proxies: list[Proxy] = []
        self.by_upstreams: dict[str, str] = {}

    @staticmethod
    def _find_port(excluded_ports: list[int]) -> int:
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", 0))
                _, port = sock.getsockname()
                if port not in excluded_ports:
                    return port

    def _excluded_ports(self) -> list[int]:
        return [port for user in self._users if isinstance(port := urlparse(user.HttpProxy).port, int)]

    def __enter__(self) -> Self:
        """launch only one mitmdump by upstream proxy"""
        excluded_ports = self._excluded_ports()
        for user in self._users:
            if user.HttpProxy not in self.by_upstreams:
                port = self._find_port(excluded_ports)
                self.by_upstreams[user.HttpProxy] = f"http://127.0.0.1:{port}"
                self._proxies.append(Proxy(self._addon, port, user.HttpProxy))
        return self

    def __exit__(self, *_) -> None:
        for proxy in self._proxies:
            proxy.stop()
