import logging
import multiprocessing
import time
from typing import Any, Callable, Iterator, Optional

from shared.job_runner import JobRunner

from ..utils import get_int
from .programme import EPGprogramme
from .server import EPGserverChannels
from .update import EPGupdater, UpdateStatusT

logger = logging.getLogger(__name__)

# TODO EPG for MAC portal


ChannelFoundT = Callable[[int], None]


class ConfidenceUpdater(JobRunner[int]):
    def __init__(self) -> None:
        self._confidence_lock = multiprocessing.Lock()
        self._confidence: Optional[int] = None
        super().__init__(self._updating, "Epg confidence updater")

    def _updating(self, confidence: int) -> None:
        with self._confidence_lock:
            self._confidence = max(0, min(confidence, 100))

    @property
    def confidence(self) -> Optional[int]:
        with self._confidence_lock:
            return self._confidence


class EPG:
    # all following methods should be called from the same process EXCEPT add_job & wait_running

    def __init__(self, update_status: UpdateStatusT, channel_found: ChannelFoundT, timeout: int) -> None:
        self.servers: dict[str, EPGserverChannels] = {}
        self.updater = EPGupdater(update_status, timeout)
        self.confidence_updater = ConfidenceUpdater()
        self._channel_found = channel_found

    def ask_update(self, url: str) -> None:
        self.updater.add_job(url)

    def update_confidence(self, confidence: int) -> None:
        self.confidence_updater.add_job(confidence)

    def wait_running(self, timeout: int) -> bool:
        return self.updater.wait_running(timeout)

    def start(self) -> None:
        self.confidence_updater.start()
        self.updater.start()

    def stop(self) -> None:
        self.updater.stop()
        self.confidence_updater.stop()

    def set_server_channels(self, server: Optional[str], channels: Any) -> None:
        if server:
            self.servers[server] = EPGserverChannels(server, channels)

    def get(self, server: Optional[str], stream_id: str, limit: Optional[str]) -> Iterator[dict[str, str]]:
        if (
            server
            and (update := self.updater.update)
            and (server_channels := self.servers.get(server))
            and (channel_id := server_channels.get(stream_id))
            and (confidence := self.confidence_updater.confidence)
        ):
            count = 0
            now = time.time()
            int_limit = get_int(limit)
            if found_progammes := update.get_programmes(channel_id, confidence):
                for programme in found_progammes.list:
                    if programme := EPGprogramme.from_programme(programme, now):
                        yield programme
                        count += 1
                        if int_limit and count >= int_limit:
                            break
                if count > 0:
                    logger.info("Get epg for %s", channel_id)
                    self._channel_found(found_progammes.confidence)
