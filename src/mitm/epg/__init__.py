import logging
from typing import Any, Iterator, Optional

from .server import EPGserverChannels
from .update import EPGupdater, UpdateStatusT

logger = logging.getLogger(__name__)


def _get_int(text: Optional[str]) -> Optional[int]:
    try:
        if text:
            return int(text)
    except ValueError:
        pass
    return None


class EPG:
    # all following methods should be called from the same process EXCEPT add_job & wait_running

    def __init__(self, update_status: UpdateStatusT, timeout: int) -> None:
        self.servers: dict[str, EPGserverChannels] = {}
        self.updater = EPGupdater(update_status, timeout)

    def ask_update(self, url: str) -> None:
        self.updater.add_job(url)

    def wait_running(self, timeout: int) -> bool:
        return self.updater.wait_running(timeout)

    def start(self) -> None:
        self.updater.start()

    def stop(self) -> None:
        self.updater.stop()

    def set_server_channels(self, server: Optional[str], channels: Any) -> None:
        if server:
            self.servers[server] = EPGserverChannels(server, channels)

    def get(self, server: Optional[str], stream_id: str, limit: Optional[str]) -> Iterator[dict[str, str]]:
        if server and (update := self.updater.update):
            if channel_id := self.servers.get(server, {}).get(stream_id):
                count = 0
                int_limit = _get_int(limit)
                for count, programme in enumerate(update.get_programmes(channel_id)):
                    if int_limit and count >= int_limit:
                        break
                    yield programme
                if count > 0:
                    logger.info("get epg for %s", channel_id)
