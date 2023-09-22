import time
from typing import Callable, Optional, ParamSpec, TypeVar

R = TypeVar("R")
P = ParamSpec("P")


def retry_if_exception(
    *exceptions: type[Exception], timeout: int
) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]:
    """decorator for retrying when exceptions occur till timeout"""
    _sleep_second = 0.1

    def decorator(func: Callable[P, R]) -> Callable[P, Optional[R]]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[R]:
            start = time.perf_counter()
            while time.perf_counter() - start <= timeout:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    time.sleep(_sleep_second)
            return None

        return wrapper

    return decorator
