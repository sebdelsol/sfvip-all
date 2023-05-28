import time
from typing import Any, Callable

_TFunc = Callable[..., Any]


def retry_if_exception(*exceptions: type[Exception], timeout: int) -> Callable[[_TFunc], _TFunc]:
    """decorator for retrying when exceptions occur till timeout"""

    def decorator(func: _TFunc) -> _TFunc:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            while time.perf_counter() - start <= timeout:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    time.sleep(0.1)
            return None

        return wrapper

    return decorator
