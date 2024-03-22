import tkinter as tk
from tkinter import ttk

from .sticky import Offset, Rect, StickyWindow, offset_centered
from .style import Style


def _get_bar_style(bg: str) -> str:
    fg = "#1c8cbc"
    bar_style_name = "stickybar.Horizontal.TProgressbar"
    style = ttk.Style()
    style.configure(
        bar_style_name,
        troughcolor=bg,
        bordercolor=bg,
        background=fg,
        lightcolor=fg,
        darkcolor=fg,
    )
    return bar_style_name


_PercentStyle = Style().font("Calibri").font_size(8).grey80


class ProgressBar(StickyWindow):
    _bg = "#1c1b1a"
    _height = 10
    _width_ratio = 0.42
    _offset = Offset(center=offset_centered, regular=(0, 53))

    def __init__(self) -> None:
        super().__init__(ProgressBar._offset, bg=ProgressBar._bg, takefocus=0)
        self.hide()
        self._percent = tk.Label(self, bg=ProgressBar._bg, width=len(self.progress_str(100)) - 1)
        self._progressbar = ttk.Progressbar(
            self,
            style=_get_bar_style(ProgressBar._bg),
            orient=tk.HORIZONTAL,
            mode="determinate",
        )
        self._percent.pack(anchor=tk.W, side=tk.LEFT)
        self._progressbar.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

    def change_position(self, rect: Rect) -> None:
        w, h = round(rect.w * ProgressBar._width_ratio), ProgressBar._height
        rect = rect.position(self._offset, w, h)
        self.geometry(rect.to_geometry())

    @staticmethod
    def progress_str(progress: float) -> str:
        return f"{progress:.1f}%"

    def set_progress(self, progress: float) -> None:
        progress = max(0, min(progress * 100, 100))
        self._percent.configure(**_PercentStyle(self.progress_str(progress)).to_tk)
        self._progressbar.config(value=progress)

    def show(self) -> None:
        self.set_progress(0)
        self.attributes("-alpha", 1.0)
        # self.deiconify()

    def hide(self) -> None:
        self.attributes("-alpha", 0.0)
        # self.withdraw()
