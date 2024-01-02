import tkinter as tk
from tkinter import ttk

from .sticky import Offset, Rect, StickyWindow


def _get_bar_style(bg: str) -> str:
    fg = "#1c8cbc"
    bar_style_name = "bar.Horizontal.TProgressbar"
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        bar_style_name,
        troughcolor=bg,
        bordercolor=bg,
        background=fg,
        lightcolor=fg,
        darkcolor=fg,
    )
    return bar_style_name


class ProgressBar(StickyWindow):
    _bg = "#1c1b1a"
    _height = 10
    _width_ratio = 2.35
    _offsety = 53
    _offset = Offset(centered=True, regular=(0, _offsety), maximized=(0, _offsety))

    def __init__(self) -> None:
        super().__init__(ProgressBar._offset, bg=ProgressBar._bg, takefocus=0)
        self.hide()
        self._progressbar = ttk.Progressbar(
            self,
            style=_get_bar_style(ProgressBar._bg),
            orient=tk.HORIZONTAL,
            mode="determinate",
        )
        self._progressbar.pack(expand=True, fill=tk.BOTH)

    def change_position(self, rect: Rect) -> None:
        w, h = round(rect.w / ProgressBar._width_ratio), ProgressBar._height
        rect = rect.position(self._offset, w, h)
        self.geometry(rect.to_geometry())

    def set_progress(self, progress: float) -> None:
        self._progressbar.config(value=max(0, min(progress * 100, 100)))

    def show(self) -> None:
        self._progressbar["value"] = 0
        self.attributes("-alpha", 1.0)
        # self.deiconify()

    def hide(self) -> None:
        self.attributes("-alpha", 0.0)
        # self.withdraw()
