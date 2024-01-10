import logging
import threading
from typing import Any, Callable, Iterable, Iterator, Optional

from ipytv import playlist
from ipytv.channel import IPTVChannel
from ipytv.exceptions import IPyTVException

from ..utils import APItype

logger = logging.getLogger(__name__)


def _stream_to_epgs(
    channels: Iterable[Any],
    channel_type: type,
    get_stream_id: Callable[[Any], Any],
    get_epg_ids: Callable[[Any], Iterator[Any]],
) -> Iterator[tuple[str, str]]:
    for channel in channels:
        if isinstance(channel, channel_type):
            stream_id = get_stream_id(channel)
            if isinstance(stream_id, (str, int)):
                for epg_id in get_epg_ids(channel):
                    if epg_id and isinstance(epg_id, str):
                        yield str(stream_id), epg_id
                        break


def _xc_stream_to_epgs(channels: Any) -> Optional[dict[str, str]]:
    if isinstance(channels, list):

        def get_stream_id(channel: dict) -> Any:
            return channel.get("stream_id")

        def get_epg_ids(channel: dict) -> Iterator[Any]:
            for epg_key in "epg_channel_id", "name":
                yield channel.get(epg_key)

        return dict(_stream_to_epgs(channels, dict, get_stream_id, get_epg_ids))
    return None


def _mac_stream_to_epgs(channels: Any) -> Optional[dict[str, str]]:
    if (
        isinstance(channels, dict)
        and (js := channels.get("js"))
        and isinstance(js, dict)
        and (channels := js.get("data"))
        and isinstance(channels, list)
    ):

        def get_stream_id(channel: dict) -> Any:
            return channel.get("id")

        def get_epg_ids(channel: dict) -> Iterator[Any]:
            for epg_key in "xmltv_id", "name":
                yield channel.get(epg_key)

        return dict(_stream_to_epgs(channels, dict, get_stream_id, get_epg_ids))
    return None


def _m3u_stream_to_epgs(channels: Any) -> Optional[dict[str, str]]:
    try:

        def get_stream_id(channel: IPTVChannel) -> Any:
            return channel.url

        def get_epg_ids(channel: IPTVChannel) -> Iterator[Any]:
            for epg_key in "tvg-id", "tvg-name":  # tvg-logo # TODO
                yield channel.attributes.get(epg_key)

        channels = playlist.loads(channels)
        return dict(_stream_to_epgs(channels, IPTVChannel, get_stream_id, get_epg_ids))
    except IPyTVException as error:
        logger.error("%s: %s", error.__class__.__name__, error)
        return None


class EPGserverChannels:
    _stream_to_epgs_get = {
        APItype.XC: _xc_stream_to_epgs,
        APItype.MAC: _mac_stream_to_epgs,
        APItype.M3U: _m3u_stream_to_epgs,
    }

    def __init__(self, server: str, channels: Any, api: APItype) -> None:
        self.server = server
        self.stream_to_epgs: dict[str, str] = {}
        self.stream_to_epgs_lock = threading.Lock()
        threading.Thread(target=self._set, args=(channels, api)).start()

    def _set(self, channels: Any, api: APItype) -> None:
        logger.info("Set channels for %s", self.server)
        if _stream_to_epgs_get := EPGserverChannels._stream_to_epgs_get.get(api):
            if stream_to_epgs := _stream_to_epgs_get(channels):
                with self.stream_to_epgs_lock:
                    self.stream_to_epgs = stream_to_epgs
                logger.info("%d channels found for %s", len(stream_to_epgs), self.server)

    def get(self, stream_id: str) -> Optional[str]:
        with self.stream_to_epgs_lock:
            return self.stream_to_epgs.get(stream_id)
