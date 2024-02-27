import logging
import threading
from typing import Any, Callable, Generic, Iterable, Iterator, Optional, Self, TypeVar

from ipytv import playlist
from ipytv.channel import IPTVChannel
from ipytv.exceptions import IPyTVException

from ..utils import APItype

logger = logging.getLogger(__name__)
T = TypeVar("T")


class StreamTo(Generic[T]):
    def __init__(
        self,
        get_stream_id: Callable[[T], Any],
        get_epg_id: Callable[[T], Any],
        get_name: Callable[[T], Iterator[Any]],
    ) -> None:
        self.epgs: dict[str, str] = {}
        self.names: dict[str, str] = {}
        self.get_stream_id = get_stream_id
        self.get_epg_id = get_epg_id
        self.get_name = get_name

    def get_names(self, channel: Any) -> Iterator[str]:
        for name in self.get_name(channel):
            if isinstance(name, str):
                yield name

    def populate(self, channels: Iterable[Any], channels_type: type) -> Self:
        epgs, names = self.epgs, self.names
        for channel in channels:
            if isinstance(channel, channels_type):
                if (stream_id := self.get_stream_id(channel)) and isinstance(stream_id, (str, int)):
                    stream_id = str(stream_id)
                    if (epg_id := self.get_epg_id(channel)) and isinstance(epg_id, str):
                        epgs[stream_id] = epg_id
                    for name in self.get_names(channel):
                        names[stream_id] = name
                        if stream_id not in epgs:
                            epgs[stream_id] = name
                        break
        return self


def xc_stream_to(channels: Any) -> Optional[StreamTo]:
    if isinstance(channels, list):

        def get_stream_id(channel: dict) -> Any:
            return channel.get("stream_id")

        def get_epg_id(channel: dict) -> Any:
            return channel.get("epg_channel_id")

        def get_name(channel: dict) -> Iterator[Any]:
            yield channel.get("name")

        return StreamTo[dict](get_stream_id, get_epg_id, get_name).populate(channels, dict)
    return None


def mac_stream_to(channels: Any) -> Optional[StreamTo]:
    if (
        isinstance(channels, dict)
        and (js := channels.get("js"))
        and isinstance(js, dict)
        and (channels := js.get("data"))
        and isinstance(channels, list)
    ):

        def get_stream_id(channel: dict) -> Any:
            return channel.get("id")

        def get_epg_id(channel: dict) -> Any:
            return channel.get("xmltv_id")

        def get_name(channel: dict) -> Iterator[Any]:
            yield channel.get("name")

        return StreamTo[dict](get_stream_id, get_epg_id, get_name).populate(channels, dict)
    return None


def m3u_stream_to(channels: Any) -> Optional[StreamTo]:
    try:

        def get_stream_id(channel: IPTVChannel) -> Any:
            return channel.url

        def get_epg_id(channel: IPTVChannel) -> Any:
            return channel.attributes.get("tvg-id")

        def get_name(channel: IPTVChannel) -> Iterator[Any]:
            yield channel.attributes.get("tvg-name")
            yield channel.name

        channels = playlist.loads(channels)
        return StreamTo[IPTVChannel](get_stream_id, get_epg_id, get_name).populate(channels, IPTVChannel)
    except IPyTVException as error:
        logger.error("%s: %s", error.__class__.__name__, error)
        return None


class EPGserverChannels:
    _stream_to_get = {
        APItype.XC: xc_stream_to,
        APItype.MAC: mac_stream_to,
        APItype.M3U: m3u_stream_to,
    }

    def __init__(self, server: str, channels: Any, api: APItype) -> None:
        self.stream_to: Optional[StreamTo] = None
        self.stream_to_lock = threading.Lock()
        threading.Thread(target=self._populate, args=(channels, api, server)).start()

    def _populate(self, channels: Any, api: APItype, server: str) -> None:
        logger.info("Set channels for %s", server)
        if _stream_to_get := EPGserverChannels._stream_to_get.get(api):
            if stream_to := _stream_to_get(channels):
                with self.stream_to_lock:
                    self.stream_to = stream_to
                logger.info("%d channels found for %s", len(stream_to.epgs), server)

    def get_epg(self, stream_id: str) -> Optional[str]:
        with self.stream_to_lock:
            if self.stream_to:
                return self.stream_to.epgs.get(stream_id)
            return None

    def get_name(self, stream_id: str) -> Optional[str]:
        with self.stream_to_lock:
            if self.stream_to:
                return self.stream_to.names.get(stream_id)
            return None
