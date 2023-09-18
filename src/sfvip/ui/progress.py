import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .thread import run_in_thread_with_ui


class ProgressWindow(tk.Toplevel):
    def __init__(self, title: str, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(width=width)
        self.title(title)
        self.resizable(False, False)
        if isinstance(self.master, tk.Tk):
            self.after(0, self.master.eval, f"tk::PlaceWindow {str(self)} center")
        self._label = tk.Label(self, text="")
        self._label.pack()
        self._progressbar = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=width)
        self._progressbar.pack()
        self._exceptions = exceptions

    def msg(self, text: str) -> None:
        self._label.config(text=text)

    def set_percent_progress(self, percent: float) -> None:
        self._progressbar["value"] = max(0, min(percent, 100))

    def run_in_thread(self, target: Callable[[], Any], *exceptions: type[Exception]) -> Any:
        exceptions = tk.TclError, *exceptions
        try:
            return run_in_thread_with_ui(self, target, *exceptions)
        # if self is exited by the user
        except tk.TclError:
            return None
        finally:
            self.destroy()
