import asyncio
import json
import re
import socket
import threading
from typing import Any, Optional, Self

from mitmproxy import http, options
from mitmproxy.coretypes.multidict import MultiDictView
from mitmproxy.tools.dump import DumpMaster

from sfvip_all_config import AllCat


class _AddOn:
    """mitmproxy addon to inject the all category"""

    def __init__(self, all_cat: type[AllCat]):
        inject_in_re = "|".join(re.escape(what) for what in all_cat.inject)
        self._is_action_get_categories = re.compile(f"get_({inject_in_re})_categories").search
        self._all_cat_id = str(all_cat.id)
        self._all_cat_json = dict(category_id=str(all_cat.id), category_name=all_cat.name, parent_id=0)

    @staticmethod
    def _is_api_request(request: http.Request) -> bool:
        return "player_api.php?" in request.path

    @staticmethod
    def _response_json(response: http.Response) -> Optional[Any]:
        if response and response.content and response.headers.get("content-type") == "application/json":
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

    async def request(self, flow: http.HTTPFlow) -> None:
        category_id = self._api_query(flow.request, "category_id")
        if category_id is not None and category_id == self._all_cat_id:
            # turn an all category query into a whole catalog query
            self._remove_query_key(flow.request, "category_id")

    async def response(self, flow: http.HTTPFlow) -> None:
        action = self._api_query(flow.request, "action")
        if action is not None and self._is_action_get_categories(action):
            if categories := self._response_json(flow.response):
                if isinstance(categories, list):
                    # response with the all category injected @ first
                    categories = self._all_cat_json, *categories
                    flow.response.text = json.dumps(categories)

    async def responseheaders(self, flow: http.HTTPFlow):
        """all reponses are streamed except the api requests"""
        if not self._is_api_request(flow.request):
            flow.response.stream = True


class Proxy:
    def __init__(self, all_cat: type[AllCat]) -> None:
        self.running = threading.Event()
        self.all_cat = all_cat
        self.master = None
        self.port = None

    @staticmethod
    def _find_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("localhost", 0))
            return sock.getsockname()[1]

    async def _start(self):
        self.port = self._find_port()
        opts = options.Options(listen_port=self.port)
        self.master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        self.master.addons.add(_AddOn(self.all_cat))
        self.running.set()
        await self.master.run()

    def __enter__(self) -> Self:
        threading.Thread(target=asyncio.run, args=(self._start(),)).start()
        self.running.wait()
        return self

    def __exit__(self, *_) -> None:
        self.master.shutdown()
