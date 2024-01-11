import time
from typing import Callable

from shared.job_runner import JobRunner
from translations.loc import LOC

from ..mitm.epg import EPGprogrammeM3U, ShowChannel, ShowChannelT, ShowEpg, ShowEpgT
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
        self.show_epg_job = JobRunner[ShowEpg](self.show_epg, "Epg show epg job", check_new=False)
        self.show_channel_job = JobRunner[ShowChannel](self.show_channel, "Epg channel found job", check_new=False)
        self.status_job = JobRunner[EPGProgress](ui.set_epg_status, "Epg status job")
        self.epg_confidence_update = epg_confidence_update
        self.epg_update = epg_update
        self.config = config
        self.ui = ui

    @property
    def update_status(self) -> UpdateStatusT:
        return self.status_job.add_job

    @property
    def add_show_channel(self) -> ShowChannelT:
        return self.show_channel_job.add_job

    @property
    def add_show_epg(self) -> ShowEpgT:
        return self.show_epg_job.add_job

    def show_channel(self, channel: ShowChannel) -> None:
        if channel.show:
            self.ui.hover_message.show(LOC.EPGFoundConfidence % (channel.name or "", f"{channel.confidence}%"))
        else:
            self.ui.hover_message.hide()

    def show_epg(self, epg: ShowEpg) -> None:
        if epg.show and epg.programmes:
            programme = epg.programmes[0]
            now = time.time()
            if isinstance(programme, EPGprogrammeM3U):
                if programme.start_timestamp <= now:  # check it's now
                    name = f"{epg.name} - " if epg.name else ""
                    self.ui.hover_epg.show(
                        f"{name}{programme.title}",
                        f"{programme.start}",
                        str(programme.descr),
                        round(100 * (now - programme.start_timestamp) / programme.duration),
                    )
        else:
            self.ui.hover_epg.hide()

    def start(self) -> None:
        self.status_job.start()
        self.show_epg_job.start()
        self.show_channel_job.start()
        self.ui.set_epg_url_update(self.config.EPG.url, self.on_epg_url_changed)
        self.epg_update(self.config.EPG.url or "")
        self.ui.set_epg_confidence_update(self.config.EPG.confidence, self.on_epg_confidence_changed)
        self.epg_confidence_update(self.config.EPG.confidence)

    def stop(self) -> None:
        self.show_channel_job.stop()
        self.show_epg_job.stop()
        self.status_job.stop()

    def on_epg_url_changed(self, epg_url: str) -> None:
        self.config.EPG.url = epg_url if epg_url else None
        self.epg_update(epg_url)

    def on_epg_confidence_changed(self, epg_confidence: int) -> None:
        self.config.EPG.confidence = epg_confidence
        self.epg_confidence_update(epg_confidence)
