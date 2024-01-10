import time
from typing import Callable, Sequence

from shared.job_runner import JobRunner
from translations.loc import LOC

from ..mitm.epg import ChannelFoundT, EPGprogramme, ShowEpgT
from ..mitm.epg.update import EPGProgress, UpdateStatusT
from .app_info import AppConfig
from .ui import UI


class EpgUpdater:
    def __init__(
        self,
        config: AppConfig,
        epg_update: Callable[[str], None],
        epg_confidence_update: Callable[[int], None],
        ui: UI,
    ) -> None:
        self._show_epg_job = JobRunner[Sequence[EPGprogramme]](self.show_epg, "Epg show epg job", check_new=False)
        self._channel_found_job = JobRunner[int](self.channel_found, "Epg channel found job", check_new=False)
        self._status_job = JobRunner[EPGProgress](ui.set_epg_status, "Epg status job")
        self._epg_confidence_update = epg_confidence_update
        self._epg_update = epg_update
        self._config = config
        self._ui = ui

    @property
    def update_status(self) -> UpdateStatusT:
        return self._status_job.add_job

    @property
    def add_channel_found(self) -> ChannelFoundT:
        return self._channel_found_job.add_job

    @property
    def add_show_epg(self) -> ShowEpgT:
        return self._show_epg_job.add_job

    def channel_found(self, confidence: int) -> None:
        self._ui.hover_message.show(LOC.EPGFoundConfidence % f"{confidence}%")

    def show_epg(self, programmes: Sequence[EPGprogramme]) -> None:
        programme = programmes[0]
        if int(programme["start_timestamp"]) <= time.time():  # check it's now
            self._ui.hover_epg.show(
                str(programme["title"]),
                f"{programme['start']} - {programme['end']}",
                str(programme["descr"]),
            )

    def start(self) -> None:
        self._status_job.start()
        self._show_epg_job.start()
        self._channel_found_job.start()
        self._ui.set_epg_url_update(self._config.EPG.url, self._on_epg_url_changed)
        self._epg_update(self._config.EPG.url or "")
        self._ui.set_epg_confidence_update(self._config.EPG.confidence, self._on_epg_confidence_changed)
        self._epg_confidence_update(self._config.EPG.confidence)

    def stop(self) -> None:
        self._channel_found_job.stop()
        self._show_epg_job.stop()
        self._status_job.stop()

    def _on_epg_url_changed(self, epg_url: str) -> None:
        self._config.EPG.url = epg_url if epg_url else None
        self._epg_update(epg_url)

    def _on_epg_confidence_changed(self, epg_confidence: int) -> None:
        self._config.EPG.confidence = epg_confidence
        self._epg_confidence_update(epg_confidence)
