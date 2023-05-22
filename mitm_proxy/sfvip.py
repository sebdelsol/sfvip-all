# use separate named package to reduce what's imported by multiproccessing
import json
import re
from typing import Any, Optional, Protocol

from mitmproxy import http
from mitmproxy.coretypes.multidict import MultiDictView


class AllCat(Protocol):
    inject: tuple[str, ...]
    name: str
    id: int


class SfVipAddOn:
    """mitmproxy addon to inject the all category"""

    def __init__(self, all_cat: AllCat) -> None:
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
            if flow.response and (categories := self._response_json(flow.response)):
                if isinstance(categories, list):
                    # response with the all category injected @ first
                    categories = self._all_cat_json, *categories
                    flow.response.text = json.dumps(categories)

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """all reponses are streamed except the api requests"""
        if not self._is_api_request(flow.request):
            if flow.response:
                flow.response.stream = True
