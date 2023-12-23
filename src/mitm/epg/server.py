import logging
import threading
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


class EPGserverChannels:
    def __init__(self, server: str, channels: Any) -> None:
        self.server = server
        self.channels: dict[str, str] = {}
        self.channels_lock = threading.Lock()
        if isinstance(channels, list):
            threading.Thread(target=self._set, args=(channels,)).start()

    @staticmethod
    def _stream_to_channels(channels: list[Any]) -> Iterator[tuple[str, str]]:
        for channel in channels:
            if isinstance(channel, dict):
                stream_id = channel.get("stream_id")
                if isinstance(stream_id, (str, int)):
                    for key in "epg_channel_id", "name":
                        channel_id = channel.get(key)
                        if channel_id and isinstance(channel_id, str):
                            yield str(stream_id), channel_id
                            break

    def _set(self, channels: list[Any]) -> None:
        logger.info("Set channels for %s", self.server)
        to_channels = dict(self._stream_to_channels(channels))
        with self.channels_lock:
            self.channels = to_channels
        logger.info("%d channels found for %s", len(to_channels), self.server)

    def get(self, stream_id: str) -> Optional[str]:
        with self.channels_lock:
            return self.channels.get(stream_id)
