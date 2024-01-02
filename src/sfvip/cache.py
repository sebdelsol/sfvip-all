from shared.job_runner import JobRunner

from ..mitm.cache import CacheProgress, CacheProgressEvent, UpdateCacheProgressT
from .ui import UI


class CacheProgressListener:
    def __init__(self, ui: UI) -> None:
        self._cache_progress_job_runner = JobRunner[CacheProgress](
            self._on_progress_changed, "Cache progress listener"
        )
        self._ui = ui

    @property
    def update_progress(self) -> UpdateCacheProgressT:
        return self._cache_progress_job_runner.add_job

    def start(self) -> None:
        self._cache_progress_job_runner.start()

    def stop(self) -> None:
        self._cache_progress_job_runner.stop()
        self._ui.progress_bar.hide()

    def _on_progress_changed(self, cache_progress: CacheProgress) -> None:
        match cache_progress.event:
            case CacheProgressEvent.START:
                self._ui.progress_bar.show()
            case CacheProgressEvent.SHOW:
                self._ui.progress_bar.set_progress(cache_progress.progress)
            case CacheProgressEvent.STOP:
                self._ui.progress_bar.hide()
