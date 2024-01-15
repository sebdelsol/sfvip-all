import time
from typing import Callable

from shared.job_runner import JobRunner
from translations.loc import LOC

from ..mitm.epg import ShowChannel, ShowChannelT, ShowEpg, ShowEpgT
from ..mitm.epg.update import EPGProgress, UpdateStatusT
from .app_info import AppConfig
from .ui import UI
from .ui.sticky import sticky_windows
from .watchers import KeyboardWatcher


class HoverEPG:
    def __init__(self, ui: UI) -> None:
        self.ui = ui
        self.current_epg = None

    def show_channel(self, channel: ShowChannel) -> None:
        if channel.show:
            self.ui.hover_message.show(LOC.EPGFoundConfidence % (channel.name or "", f"{channel.confidence}%"))
        else:
            self.ui.hover_message.hide()

    def show_epg(self, epg: ShowEpg) -> None:
        if epg.show and epg.programmes:
            self.current_epg = epg
            if self.ui.hover_programmes.is_shown():
                self.ui.hover_programmes.show(epg)
                self.ui.hover_message.hide()
            else:
                self.ui.hover_epg.show(epg, now=time.time())
        else:
            self.current_epg = None
            self.ui.hover_programmes.hide()
            self.ui.hover_epg.hide()

    def on_key_pressed(self, _: str) -> None:
        if sticky_windows.has_focus():
            if self.current_epg:
                if self.ui.hover_programmes.is_shown():
                    self.ui.hover_programmes.hide()
                else:
                    self.ui.hover_programmes.show(self.current_epg)
                    self.ui.hover_epg.hide()
                    self.ui.hover_message.hide()


class EpgUpdater:
    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        config: AppConfig,
        epg_update: Callable[[str], None],
        epg_confidence_update: Callable[[int], None],
        ui: UI,
    ) -> None:
        self.hover_epg = HoverEPG(ui)
        self.keyboard_watcher = KeyboardWatcher("e", self.hover_epg.on_key_pressed)
        self.show_epg_job = JobRunner[ShowEpg](self.hover_epg.show_epg, "Show epg job", check_new=False)
        self.show_channel_job = JobRunner[ShowChannel](
            self.hover_epg.show_channel, "Show channel job", check_new=False
        )
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

    def start(self) -> None:
        self.keyboard_watcher.start()
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
        self.keyboard_watcher.stop()

    def on_epg_url_changed(self, epg_url: str) -> None:
        self.config.EPG.url = epg_url if epg_url else None
        self.epg_update(epg_url)

    def on_epg_confidence_changed(self, epg_confidence: int) -> None:
        self.config.EPG.confidence = epg_confidence
        self.epg_confidence_update(epg_confidence)
