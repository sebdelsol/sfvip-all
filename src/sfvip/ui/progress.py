import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional, TypeVar

from .style import _Style
from .thread import run_in_thread_with_ui
from .widgets import _Button

Treturn = TypeVar("Treturn")


class _Theme:
    text = _Style().font("Calibri").font_size(10).max_width(30).white
    wait = text("Please wait").bigger(6)
    bg = "#242424"
    space = 30


def _get_bar_style() -> str:
    bg = "#2A2A2A"
    fg = "#1c8cbc"
    bar_style_name = "bar.Horizontal.TProgressbar"
    style = ttk.Style()
    style.configure(bar_style_name, troughcolor=bg, bordercolor=bg, background=fg, lightcolor=fg, darkcolor=fg)
    return bar_style_name


class _Title:
    bg = "#222222"
    quit = _Theme.text("x").bigger(4)
    title = _Theme.text.copy().bigger(10)
    button = dict(bg=bg, mouseover="red")


class TitleBarWindow(tk.Toplevel):
    def __init__(self, title: str, quit_method: Callable[[], None], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.overrideredirect(True)  # turns off title bar, geometry
        self.attributes("-topmost", True)
        self._offsetx = 0
        self._offsety = 0
        title_bar = tk.Frame(self, bg=_Title.bg)
        space = tk.Label(title_bar, bg=_Title.bg, **_Title.quit(" ").to_tk)
        title_txt = tk.Label(title_bar, bg=_Title.bg, **_Title.title(title).to_tk)
        close_button = _Button(title_bar, **_Title.button, **_Title.quit.to_tk, command=quit_method)
        title_bar.pack(expand=True, fill=tk.X)
        space.grid(row=0, column=0, sticky=tk.W)
        title_txt.grid(row=0, column=1, sticky=tk.EW)
        close_button.grid(row=0, column=2, sticky=tk.E)
        title_bar.columnconfigure(1, weight=1)
        self._grip_widgets(space, title_txt)

    def _move_window(self, event: tk.Event) -> None:
        self.geometry(f"+{event.x_root - self._offsetx}+{event.y_root - self._offsety}")

    def _click_win(self, event: tk.Event) -> None:
        self._offsetx = event.x
        self._offsety = event.y

    def _grip_widgets(self, *widgets: tk.Widget) -> None:
        for widget in widgets:
            widget.bind("<B1-Motion>", self._move_window)
            widget.bind("<Button-1>", self._click_win)


# TODO better progressbar behavior
class ProgressWindow(TitleBarWindow):
    def __init__(self, title: str, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(title=title, width=width, bg=_Theme.bg, quit_method=self.quitting)
        self.overrideredirect(True)  # turns off title bar, geometry
        self.attributes("-topmost", True)
        self.resizable(False, False)
        if isinstance(self.master, tk.Tk):
            self.after(0, self.master.eval, f"tk::PlaceWindow {str(self)} center")
        wait = tk.Label(self, bg=_Theme.bg, **_Theme.wait.to_tk)
        self._label = tk.Label(self, bg=_Theme.bg, text="")
        self._progressbar = ttk.Progressbar(
            self, style=_get_bar_style(), orient=tk.HORIZONTAL, mode="determinate", length=width
        )
        wait.pack(pady=(_Theme.space / 2, 0))
        self._progressbar.pack()
        self._label.pack(pady=(0, _Theme.space))
        self._exceptions = exceptions
        self._destroyed = False

    def quitting(self) -> None:
        self._destroyed = True
        self.destroy()

    def msg(self, text: str) -> None:
        self._label.config(**_Theme.text(text).to_tk)

    def set_percent_progress(self, percent: float) -> None:
        self._progressbar["value"] = max(0, min(percent, 100))

    def run_in_thread(
        self, target: Callable[[], Treturn], *exceptions: type[Exception], mainloop: bool
    ) -> Optional[Treturn]:
        exceptions = tk.TclError, *exceptions
        try:
            return run_in_thread_with_ui(self, target, *exceptions, mainloop=mainloop)
        except tk.TclError:
            # if self is exited by the user
            return None
        finally:
            self.destroy()
