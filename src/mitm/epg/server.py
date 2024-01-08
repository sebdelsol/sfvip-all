import logging
import threading
from typing import Any, Iterator, Optional

from ..utils import APIRequest

logger = logging.getLogger(__name__)


def _stream_to_channel(channels: list[Any], stream_id: str, *keys: str) -> Iterator[tuple[str, str]]:
    for channel in channels:
        if isinstance(channel, dict):
            _id = channel.get(stream_id)
            if isinstance(stream_id, (str, int)):
                for key in keys:
                    channel_id = channel.get(key)
                    if channel_id and isinstance(channel_id, str):
                        yield str(_id), channel_id
                        break


def _xc_stream_to_channels(channels: Any) -> Optional[dict[str, str]]:
    if isinstance(channels, list):
        return dict(_stream_to_channel(channels, "stream_id", "epg_channel_id", "name"))
    return None


def _mac_stream_to_channels(channels: Any) -> Optional[dict[str, str]]:
    if (
        isinstance(channels, dict)
        and (js := channels.get("js"))
        and isinstance(js, dict)
        and (data := js.get("data"))
    ):
        return dict(_stream_to_channel(data, "id", "xmltv_id", "name"))
    return None


class EPGserverChannels:
    def __init__(self, server: str, channels: Any, api: APIRequest) -> None:
        self.server = server
        self.channels: dict[str, str] = {}
        self.channels_lock = threading.Lock()
        threading.Thread(target=self._set, args=(channels, api)).start()

    def _set(self, channels: Any, api: APIRequest) -> None:
        logger.info("Set channels for %s", self.server)
        match api:
            case APIRequest.XC:
                to_channels = _xc_stream_to_channels(channels)
            case APIRequest.MAC:
                to_channels = _mac_stream_to_channels(channels)
            case _:
                to_channels = None
        if to_channels:
            with self.channels_lock:
                self.channels = to_channels
            logger.info("%d channels found for %s", len(to_channels), self.server)

    def get(self, stream_id: str) -> Optional[str]:
        with self.channels_lock:
            return self.channels.get(stream_id)
