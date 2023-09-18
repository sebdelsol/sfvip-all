import threading
import tkinter as tk
from typing import Callable, Optional, TypeVar

Treturn = TypeVar("Treturn")


def run_in_thread_with_ui(
    ui: tk.Misc,
    target: Callable[[], Treturn],
    *exceptions: type[Exception],
    mainloop: bool,
) -> Optional[Treturn]:
    """
    run the target function in a thread,
    handle the tk main loop,
    any exceptions is re-raised in the main thread
    """

    class Return:
        value: Optional[Treturn] = None
        exception: Optional[Exception] = None

    def run():
        try:
            Return.value = target()
        except exceptions as exception:
            Return.exception = exception
        finally:
            if mainloop:
                ui.after(0, ui.quit)
            else:
                ui.after(0, ui.destroy)

    thread = threading.Thread(target=run, daemon=not mainloop)
    try:
        thread.start()
        if mainloop:
            ui.mainloop()
        else:
            ui.wait_window(ui)
    finally:
        if mainloop:  # TODO can't catch exception if no join, is that an issue ?
            thread.join()
        if Return.exception is not None:
            raise Return.exception
    return Return.value
