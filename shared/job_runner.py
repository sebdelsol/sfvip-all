import logging
import multiprocessing
import threading
from typing import Callable, Generic, Iterator, Optional, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)
CheckNewsT = bool | Callable[[T, T | None], bool]


class _Jobs(Generic[T]):
    def __init__(self, name: str, check_new: CheckNewsT) -> None:
        self._objs: "multiprocessing.SimpleQueue[T | None]" = multiprocessing.SimpleQueue()
        self._stopping = multiprocessing.Event()
        self._running = multiprocessing.Event()
        self._check_new = check_new
        self._last_obj: Optional[T] = None
        self._name = name

    def add_job(self, obj: T) -> None:
        if self._running.is_set():
            # check it's a different job
            if (
                (callable(self._check_new) and self._check_new(obj, self._last_obj))
                or not self._check_new
                or obj != self._last_obj
            ):
                # stop last job
                self._stopping.set()
                self._last_obj = obj
                self._objs.put(obj)

    def run_jobs(self) -> Iterator[T]:
        logger.info("%s started", self._name)
        while self._running.is_set():
            obj = self._objs.get()
            if obj is None:
                break
            self._stopping.clear()
            yield obj
        logger.info("%s stopped", self._name)

    def wait_running(self, timeout: int) -> bool:
        return self._running.wait(timeout)

    @property
    def stopping(self) -> bool:
        return self._stopping.is_set()

    def start(self) -> None:
        self._running.set()

    def stop(self) -> None:
        self._running.clear()
        self._stopping.set()
        self._objs.put(None)


class JobRunner(Generic[T]):
    """
    run jobs accross processes
    jobs are run in a FIFO sequence
    all following methods should be called from the same process EXCEPT add_job & wait_running
    """

    def __init__(self, job: Callable[[T], None], name: str, check_new: CheckNewsT = True) -> None:
        self._job = job
        self._jobs = _Jobs[T](name, check_new)
        self._jobs_runner = None

    def _run_jobs(self) -> None:
        for obj in self._jobs.run_jobs():
            self._job(obj)

    @property
    def add_job(self) -> Callable[[T], None]:
        return self._jobs.add_job

    def stopping(self) -> bool:
        return self._jobs.stopping

    def wait_running(self, timeout: int) -> bool:
        return self._jobs.wait_running(timeout)

    def start(self) -> None:
        self._jobs_runner = threading.Thread(target=self._run_jobs)
        self._jobs.start()
        self._jobs_runner.start()

    def stop(self) -> None:
        if self._jobs_runner:
            self._jobs.stop()
            self._jobs_runner.join()
