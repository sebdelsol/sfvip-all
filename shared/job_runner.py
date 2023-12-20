import logging
import multiprocessing
import threading
from typing import Callable, Generic, Iterator, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Jobs(Generic[T]):
    def __init__(self, name: str) -> None:
        self._objs: "multiprocessing.SimpleQueue[T | None]" = multiprocessing.SimpleQueue()
        self._running = multiprocessing.Event()
        self._name = name

    def add_job(self, obj: T) -> None:
        if self._running.is_set():
            self._objs.put(obj)

    def run_jobs(self) -> Iterator[T]:
        logger.info("%s started", self._name)
        while self._running.is_set():
            obj = self._objs.get()
            if obj is None:
                break
            yield obj
        logger.info("%s stopped", self._name)

    def start(self) -> None:
        self._running.set()

    def stop(self) -> None:
        self._running.clear()
        self._objs.put(None)


class JobRunner(Generic[T]):
    """run jobs accross processes"""

    _name = ""

    def __init__(self, job: Callable[[T], None]) -> None:
        self._job = job
        self._jobs = Jobs[T](self._name)
        self._jobs_runner = None

    def _run_jobs(self) -> None:
        for obj in self._jobs.run_jobs():
            self._job(obj)

    @property
    def add_job(self) -> Callable[[T], None]:
        return self._jobs.add_job

    def start(self) -> None:
        self._jobs_runner = threading.Thread(target=self._run_jobs)
        self._jobs.start()
        self._jobs_runner.start()

    def stop(self) -> None:
        if self._jobs_runner:
            self._jobs.stop()
            self._jobs_runner.join()
