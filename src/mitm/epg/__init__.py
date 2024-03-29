import logging
import multiprocessing
import time
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple, Optional

from shared.job_runner import JobRunner

from ..utils import APItype, get_int
from .programme import EPGprogramme, EPGprogrammeM3U, EPGprogrammeMAC, EPGprogrammeXC
from .server import EPGserverChannels
from .update import EPGupdater, FoundProgammes, UpdateStatusT

logger = logging.getLogger(__name__)


class ShowChannel(NamedTuple):
    show: bool
    name: Optional[str] = None
    confidence: Optional[int] = None


ShowChannelT = Callable[[ShowChannel], None]


class ShowEpg(NamedTuple):
    show: bool
    name: Optional[str] = None
    programmes: Optional[tuple[EPGprogrammeM3U, ...]] = None


ShowEpgT = Callable[[ShowEpg], None]


class EpgCallbacks(NamedTuple):
    update_status: UpdateStatusT
    show_channel: ShowChannelT
    show_epg: ShowEpgT


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


class PreferUpdater(JobRunner[bool]):
    def __init__(self) -> None:
        self._prefer_internal_lock = multiprocessing.Lock()
        self._prefer_internal: Optional[bool] = None
        super().__init__(self._updating, "Epg prefer internal updater")

    def _updating(self, prefer_internal: bool) -> None:
        with self._prefer_internal_lock:
            self._prefer_internal = prefer_internal

    @property
    def prefer_internal(self) -> Optional[bool]:
        with self._prefer_internal_lock:
            return self._prefer_internal


# pylint: disable=too-many-instance-attributes
class EPG:
    _programme_type = {APItype.XC: EPGprogrammeXC, APItype.MAC: EPGprogrammeMAC, APItype.M3U: EPGprogrammeM3U}
    _m3u_server = "m3u.server"

    # all following methods should be called from the same process EXCEPT add_job & wait_running
    def __init__(self, roaming: Path, callbacks: EpgCallbacks, timeout: int) -> None:
        self.servers: dict[str, EPGserverChannels] = {}
        self.updater = EPGupdater(roaming, callbacks.update_status, timeout)
        self.confidence_updater = ConfidenceUpdater()
        self.prefer_updater = PreferUpdater()
        self.show_channel = callbacks.show_channel
        self.channel_shown = False
        self.show_epg = callbacks.show_epg
        self.epg_shown = False

    def ask_update(self, url: str) -> None:
        self.updater.add_job(url)

    def update_confidence(self, confidence: int) -> None:
        self.confidence_updater.add_job(confidence)

    def update_prefer(self, prefer_internal: bool) -> None:
        self.prefer_updater.add_job(prefer_internal)

    def wait_running(self, timeout: int) -> bool:
        return self.updater.wait_running(timeout)

    def start(self) -> None:
        self.confidence_updater.start()
        self.prefer_updater.start()
        self.updater.start()

    def stop(self) -> None:
        self.updater.stop()
        self.prefer_updater.stop()
        self.confidence_updater.stop()

    def set_server_channels(self, server: Optional[str], channels: Any, api: APItype) -> None:
        if server:
            if api == APItype.M3U:
                server = EPG._m3u_server
            self.servers[server] = EPGserverChannels(server, channels, api)

    @staticmethod
    def _get_listing(
        programme_type: EPGprogramme, programmes: FoundProgammes, limit: Optional[str]
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

    def ask_epg(
        self, server: Optional[str], stream_id: str, limit: Optional[str], api: APItype
    ) -> Optional[tuple[EPGprogramme, ...]]:
        if (
            server
            and (server_channels := self.servers.get(server))
            and (epg_id := server_channels.get_epg(stream_id))
            and (confidence := self.confidence_updater.confidence)
            and (update := self.updater.update)
        ):
            if programmes := update.get_programmes(epg_id, confidence):
                if programme_type := EPG._programme_type.get(api):
                    if listing := tuple(self._get_listing(programme_type, programmes, limit)):
                        logger.info("Get epg for %s", epg_id)
                        name = self.ask_stream(server, stream_id)
                        self.show_channel(ShowChannel(True, name, programmes.confidence))
                        self.channel_shown = True
                        return listing
        return None

    def ask_stream(self, server: Optional[str], stream_id: str) -> Optional[str]:
        if (
            server
            and (server_channels := self.servers.get(server))
            and (name := server_channels.get_name(stream_id))
        ):
            return name
        return None

    def m3u_stream_started(self, stream_id: str) -> bool:
        server = EPG._m3u_server
        if programmes := self.ask_epg(server, stream_id, "15", APItype.M3U):
            name = self.ask_stream(server, stream_id)
            self.show_epg(ShowEpg(True, name, programmes))  # type: ignore # we know those are EPGprogrammeM3U
            logger.info("Start showing epg for %s", name)
            self.epg_shown = True
            return True
        return False

    def m3u_stream_stopped(self) -> None:
        if self.epg_shown:
            logger.info("Stop showing epg")
            self.show_epg(ShowEpg(False))
            self.epg_shown = False
        if self.channel_shown:
            self.show_channel(ShowChannel(False))
            self.channel_shown = False
