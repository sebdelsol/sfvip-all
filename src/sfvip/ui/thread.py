import threading
import tkinter as tk
from typing import Callable, Optional, ParamSpec, TypeVar

R = TypeVar("R")
P = ParamSpec("P")


class EventContextManager(threading.Event):
    def __enter__(self) -> None:
        self.set()

    def __exit__(self, *_) -> None:
        self.clear()


class ThreadUI:
    _is_main_loop_running = EventContextManager()

    @classmethod
    def quit(cls) -> None:
        # in case a thread is still waiting for the mainloop
        cls._is_main_loop_running.set()

    def __init__(self, ui: tk.Misc, *exceptions: type[Exception]) -> None:
        self._ui = ui
        self._exceptions = exceptions
        self._create_mainloop = not ThreadUI._is_main_loop_running.is_set()

    def start(self, target: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
        """
        run the target function in a thread,
        handle the main loop if needed,
        any exceptions is re-raised in the main thread
        """

        class Return:
            value: Optional[R] = None
            exception: Optional[Exception] = None

        def run() -> None:
            try:
                ThreadUI._is_main_loop_running.wait()
                Return.value = target(*args, **kwargs)
            except self._exceptions as exception:
                Return.exception = exception
            finally:
                if self._create_mainloop:
                    self._ui.after(0, self._ui.quit)
                else:
                    self._ui.after(0, self._ui.destroy)

        thread = threading.Thread(target=run)
        try:
            thread.start()
            if self._create_mainloop:
                with ThreadUI._is_main_loop_running:
                    self._ui.mainloop()
            else:
                self._ui.wait_window(self._ui)
        finally:
            # do not block the main thread
            while thread.is_alive():
                thread.join(timeout=0)
                self._ui.update()
            if Return.exception is not None:
                raise Return.exception
        return Return.value
