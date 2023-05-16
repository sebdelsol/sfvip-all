import asyncio
import json
import multiprocessing
import re
import threading
from typing import Any, Optional

from mitmproxy import http, options
from mitmproxy.addons import (
    core,
    disable_h2c,
    dns_resolver,
    next_layer,
    proxyserver,
    tlsconfig,
)
from mitmproxy.coretypes.multidict import MultiDictView
from mitmproxy.master import Master

from sfvip_all_config import AllCat


# warning: use only the needed addons,
# if any issues use addons.default_addons() instead
def _minimum_addons():
    return [
        core.Core(),
        disable_h2c.DisableH2C(),
        proxyserver.Proxyserver(),
        dns_resolver.DnsResolver(),
        next_layer.NextLayer(),
        tlsconfig.TlsConfig(),
    ]


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

    def _get_query_key(self, request: http.Request, key: str) -> Optional[str]:
        return self._query(request).get(key, None) if self._is_api_request(request) else None

    def request(self, flow: http.HTTPFlow) -> None:
        category_id = self._get_query_key(flow.request, "category_id")
        if category_id is not None and category_id == self._all_cat_id:
            # turn an all category query into a whole catalog query
            self._remove_query_key(flow.request, "category_id")

    def response(self, flow: http.HTTPFlow) -> None:
        action = self._get_query_key(flow.request, "action")
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


class Proxy(multiprocessing.Process):
    """run mitmdump in a process"""

    def __init__(self, all_cat: type[AllCat], port: int, upstream: str) -> None:
        self._init_done = multiprocessing.Event()
        self._stop = multiprocessing.Event()
        self._all_cat = all_cat
        self._port = port
        self._upstream = upstream
        self._master = None
        super().__init__()

    def run(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            mode = f"upstream:{self._upstream}" if self._upstream else "regular"
            opts = options.Options(listen_port=self._port, ssl_insecure=True, mode=(mode,))
            self._master = master = Master(opts, event_loop=loop)
            master.addons.add(*_minimum_addons())
            master.addons.add(_AddOn(self._all_cat))
            threading.Thread(target=self._wait_for_stop).start()
        finally:
            self._init_done.set()
        loop.run_until_complete(master.run())

    def _wait_for_stop(self) -> None:
        self._stop.wait()
        if self._master:
            self._master.shutdown()

    def wait_for_init_done(self) -> None:
        self._init_done.wait()

    def stop(self) -> None:
        self._stop.set()
        self.join()
