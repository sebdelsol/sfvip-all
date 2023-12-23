from typing import Callable

from shared.job_runner import JobRunner

from ..mitm.epg.update import EPGstatus, UpdateStatusT
from .app_info import AppConfig
from .ui import UI


class EpgUpdater:
    def __init__(self, config: AppConfig, epg_update: Callable[[str], None], ui: UI) -> None:
        self._status_job_runner = JobRunner[EPGstatus](ui.set_epg_status, "Epg status listener")
        self._epg_update = epg_update
        self._config = config
        self._ui = ui

    @property
    def update_status(self) -> UpdateStatusT:
        return self._status_job_runner.add_job

    def start(self) -> None:
        self._status_job_runner.start()
        self._ui.set_epg_url_update(self._config.EPG.url, self._on_epg_url_changed)
        self._epg_update(self._config.EPG.url or "")

    def stop(self) -> None:
        self._status_job_runner.stop()

    def _on_epg_url_changed(self, epg_url: str) -> None:
        self._config.EPG.url = epg_url if epg_url else None
        self._epg_update(epg_url)
