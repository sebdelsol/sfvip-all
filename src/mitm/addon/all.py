import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional

from mitmproxy import http

from ..utils import del_query_key, get_query_key, response_json

logger = logging.getLogger(__name__)


class AllCategoryName(NamedTuple):
    live: Optional[str]
    series: Optional[str]
    vod: Optional[str]


@dataclass
class Panel:
    get_category: str
    get_categories: str
    all_category_name: str
    all_category_id: str = "0"


class PanelType(Enum):
    LIVE = "live"
    VOD = "vod"
    SERIES = "series"


def _get_panel(panel_type: PanelType, all_category_name: str, streams: bool = True) -> Panel:
    return Panel(
        all_category_name=all_category_name,
        get_categories=f"get_{panel_type.value}_categories",
        get_category=f"get_{panel_type.value}{'_streams' if streams else ''}",
    )


def _unused_category_id(categories: list[dict]) -> str:
    if ids := [
        int(cat_id)
        for category in categories
        if (cat_id := category.get("category_id")) is not None and isinstance(cat_id, (int, str))
    ]:
        return str(max(ids) + 1)
    return "0"


def _log(verb: str, panel: Panel, action: str) -> None:
    txt = "%s '%s' category (id=%s) for '%s' request"
    logger.info(txt.capitalize(), verb.capitalize(), panel.all_category_name, panel.all_category_id, action)


class AllPanels:
    def __init__(self, all_name: AllCategoryName) -> None:
        panels = []
        if all_name.series:
            panels.append(_get_panel(PanelType.SERIES, all_name.series, streams=False))
        if all_name.vod:
            panels.append(_get_panel(PanelType.VOD, all_name.vod))
        if all_name.live:
            panels.append(_get_panel(PanelType.LIVE, all_name.live))
        self.category_panel = {panel.get_category: panel for panel in panels}
        self.categories_panel = {panel.get_categories: panel for panel in panels}

    def inject_all(self, flow: http.HTTPFlow, action: str) -> None:
        if (
            action in self.categories_panel
            and (response := flow.response)
            and (categories := response_json(response))
            and isinstance(categories, list)
        ):
            # response with the all category injected @ the beginning
            panel = self.categories_panel[action]
            panel.all_category_id = _unused_category_id(categories)
            all_category = dict(
                category_id=panel.all_category_id,
                category_name=panel.all_category_name,
                parent_id=0,
            )
            categories.insert(0, all_category)
            _log("inject", panel, action)
            response.text = json.dumps(categories)

    def serve_all(self, flow: http.HTTPFlow, action: str) -> None:
        if action in self.category_panel:
            panel = self.category_panel[action]
            category_id = get_query_key(flow, "category_id")
            if category_id == panel.all_category_id:
                # turn an all category query into a whole catalog query
                del_query_key(flow, "category_id")
                _log("serve", panel, action)
