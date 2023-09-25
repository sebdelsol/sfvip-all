import tkinter as tk
from contextlib import contextmanager
from enum import Enum
from tkinter import ttk
from typing import Any, Callable, Iterator, Self, TypeVar

from .style import _Style
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


class ProgressMode(Enum):
    PERCENT = "determinate"
    UNKNOWN = "indeterminate"


class ProgressWindow(TitleBarWindow):
    _instances: set["ProgressWindow"] = set()

    @classmethod
    def quit_all(cls) -> None:
        for instance in ProgressWindow._instances.copy():
            instance.destroy()

    def __init__(self, title: str, width: int, *exceptions: type[Exception]) -> None:
        super().__init__(title=title, width=width, bg=_Theme.bg, quit_method=self.destroy)
        ProgressWindow._instances.add(self)
        self.overrideredirect(True)  # turns off title bar, geometry
        self.attributes("-topmost", True)
        self.resizable(False, False)
        if isinstance(self.master, tk.Tk):
            self.after(0, self.master.eval, f"tk::PlaceWindow {str(self)} center")
        wait = tk.Label(self, bg=_Theme.bg, **_Theme.wait.to_tk)
        self._label = tk.Label(self, bg=_Theme.bg, text="")
        self._progressbar = ttk.Progressbar(self, style=_get_bar_style(), orient=tk.HORIZONTAL, length=width)
        self._progress_mode = None
        self._set_progress_mode(ProgressMode.UNKNOWN)
        wait.pack(pady=(_Theme.space / 2, 0))
        self._progressbar.pack(expand=True, fill=tk.BOTH)
        self._label.pack(pady=(0, _Theme.space))
        self._exceptions = exceptions
        self._destroyed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.destroy()

    def destroy(self) -> None:
        ProgressWindow._instances.discard(self)
        if not self._destroyed:
            self._destroyed = True
            super().destroy()

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def msg(self, text: str) -> None:
        self._label.config(**_Theme.text(text).to_tk)

    def _set_progress_mode(self, mode: ProgressMode) -> None:
        if self._progress_mode != mode:
            if mode == ProgressMode.UNKNOWN:
                self._progressbar.start(10)
            else:
                self._progressbar.stop()
            self._progressbar["mode"] = mode.value
            self._progress_mode = mode

    @contextmanager
    def show_percent(self) -> Iterator[Callable[[float], None]]:
        def set_progress(percent: float) -> None:
            self._set_progress_mode(ProgressMode.PERCENT)
            self._progressbar["value"] = max(0, min(percent, 100))

        yield set_progress
        self.after(200, self._set_progress_mode, ProgressMode.UNKNOWN)
