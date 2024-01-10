import logging
import multiprocessing
import time
from typing import Any, Callable, Iterator, Optional

from shared.job_runner import JobRunner

from ..utils import APItype, get_int
from .programme import EPGprogramme, EPGprogrammeM3U, EPGprogrammeMAC, EPGprogrammeXC
from .server import EPGserverChannels
from .update import EPGupdater, FoundProgammes, UpdateStatusT

logger = logging.getLogger(__name__)

ChannelFoundT = Callable[[int], None]
ShowEpgT = Callable[[tuple[EPGprogramme, ...]], None]


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
    _programme_type = {APItype.XC: EPGprogrammeXC, APItype.MAC: EPGprogrammeMAC, APItype.M3U: EPGprogrammeM3U}

    # all following methods should be called from the same process EXCEPT add_job & wait_running
    def __init__(
        self, update_status: UpdateStatusT, channel_found: ChannelFoundT, show_epg: ShowEpgT, timeout: int
    ) -> None:
        self.servers: dict[str, EPGserverChannels] = {}
        self.updater = EPGupdater(update_status, timeout)
        self.confidence_updater = ConfidenceUpdater()
        self._channel_found = channel_found
        self._show_epg = show_epg

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

    def set_server_channels(self, server: Optional[str], channels: Any, api: APItype) -> None:
        if server:
            self.servers[server] = EPGserverChannels(server, channels, api)

    def _get_listing(
        self,
        programme_type: EPGprogramme,
        programmes: FoundProgammes,
        epg_id: str,
        limit: Optional[str],
    ) -> Iterator[EPGprogramme]:
        count = 0
        now = time.time()
        int_limit = get_int(limit)
        for programme in programmes.list:
            if programme := programme_type.from_programme(programme, now):
                yield programme
                count += 1
                if int_limit and count >= int_limit:
                    break
        if count > 0:
            logger.info("Get epg for %s", epg_id)
            self._channel_found(programmes.confidence)

    def ask_stream(
        self, server: Optional[str], stream_id: str, limit: Optional[str], api: APItype
    ) -> Optional[tuple[EPGprogramme, ...]]:
        if (
            server
            and (server_channels := self.servers.get(server))
            and (epg_id := server_channels.get(stream_id))
            and (confidence := self.confidence_updater.confidence)
            and (update := self.updater.update)
        ):
            if programmes := update.get_programmes(epg_id, confidence):
                if programme_type := EPG._programme_type.get(api):
                    return tuple(self._get_listing(programme_type, programmes, epg_id, limit))
        return None

    def ask_m3u_stream(self, server: Optional[str], stream_id: str) -> bool:
        if listing := self.ask_stream(server, stream_id, "1", APItype.M3U):
            self._show_epg(listing)
            return True
        return False
