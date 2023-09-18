import threading
import tkinter as tk
from typing import Any, Callable, Optional


def run_in_thread_with_ui(ui: tk.Misc, target: Callable[[], Any], *exceptions: type[Exception]) -> Any:
    """
    run the target function in a thread,
    handle the tk main loop,
    any exceptions is re-raised in the main thread
    """

    class Return:
        value = None
        exception: Optional[Exception] = None

    def run():
        try:
            Return.value = target()
        except exceptions as exception:
            Return.exception = exception
        finally:
            ui.after(0, ui.quit)

    thread = threading.Thread(target=run)
    try:
        thread.start()
        ui.mainloop()
    finally:
        thread.join()
        if Return.exception is not None:
            raise Return.exception
    return Return.value
