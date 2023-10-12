import time
from typing import Callable, Optional, ParamSpec, TypeVar

R = TypeVar("R")
P = ParamSpec("P")


class RetryIfException:
    """decorator for retrying when exceptions occur till timeout"""

    _sleep_second = 0.1

    def __init__(self, *exceptions: type[Exception], timeout: int) -> None:
        self._exceptions = exceptions
        self._timeout = timeout

    def __call__(self, func: Callable[P, R]) -> Callable[P, Optional[R]]:
        def decorated(*args: P.args, **kwargs: P.kwargs) -> Optional[R]:
            start = time.perf_counter()
            while time.perf_counter() - start <= self._timeout:
                try:
                    return func(*args, **kwargs)
                except self._exceptions:
                    time.sleep(RetryIfException._sleep_second)
            return None

        return decorated
