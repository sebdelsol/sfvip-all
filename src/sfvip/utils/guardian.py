import threading
from typing import Callable, ParamSpec

P = ParamSpec("P")


class ThreadGuardian:
    """
    prevent execution if already in use in another thread,
    use as a decorator
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._used_by = None
        self._count = 0

    def __enter__(self) -> bool:
        with self._lock:
            if self._used_by is None:
                self._used_by = threading.get_ident()
                self._count = 1
                return True

            if self._used_by == threading.get_ident():
                self._count += 1
                return True

            return False

    def __exit__(self, *_) -> None:
        with self._lock:
            if self._used_by == threading.get_ident():
                self._count -= 1
                if not self._count:
                    self._used_by = None

    def __call__(self, func: Callable[P, None]) -> Callable[P, None]:
        def decorated(*args: P.args, **kwargs: P.kwargs) -> None:
            with self as is_free:
                if is_free:
                    func(*args, **kwargs)

        return decorated
