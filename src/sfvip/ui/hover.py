import tkinter as tk
from abc import ABC, abstractmethod

from ...winapi import win
from .fx import Fade
from .sticky import Offset, StickyWindow, StickyWindows
from .style import Style
from .widgets import HorizontalProgressBar, RoundedBox

# TODO check max width & height


class _HoverMessageBox(StickyWindow, ABC):
    show_when_no_border = True

    offset: Offset
    bg = "black"
    alpha = 0.9
    wait_before_fade = 3000
    fade_duration = 1500
    box_color = "#101010"
    radius = 7

    def __init__(self) -> None:
        super().__init__(self.offset, bg=self.bg)
        self.hide()
        self.attributes("-transparentcolor", self.bg)
        win.set_click_through(self.winfo_id())
        self.box = RoundedBox(self, bg=self.bg, radius=self.radius, box_color=self.box_color)
        self.box.pack()
        self.box.add_widget(self.get_widget())
        self._fade = Fade(self)

    def update_and_show(self) -> None:
        self.attributes("-alpha", self.alpha)
        self.deiconify()
        self.box.update_widget()
        StickyWindows.update_position(self)
        self._fade.fade(self.fade_duration, out=True, wait_ms=self.wait_before_fade)

    def hide(self) -> None:
        self.attributes("-alpha", 0)
        self.withdraw()

    @abstractmethod
    def get_widget(self) -> tk.Widget:
        ...


class HoverMessage(_HoverMessageBox):
    offset = Offset(regular=(22, 35))
    stl = Style().font("Calibri").font_size(14).bold

    def get_widget(self) -> tk.Widget:
        self.label = tk.Label(self, bg=self.box_color)
        return self.label

    def show(self, message: str) -> None:
        self.label.config(**self.stl(message).to_tk)
        self.update_and_show()


class HoverChannelEpg(_HoverMessageBox):
    offset = Offset(regular=(22, 0), center=(0, 0.75))
    stl_title = Style().font("Calibri").font_size(14).bold
    stl_schedule = Style().font("Calibri").font_size(15).bold
    stl_descr = Style().font("Calibri").font_size(14).wrap(80)
    progress_bar = dict(bg="#606060", fg="#1c8cbc", height=10, length=300)

    def get_widget(self) -> tk.Widget:
        frame = tk.Frame(self, bg=self.box_color)
        self.label_title = tk.Label(frame, bg=self.box_color, justify=tk.LEFT)
        schedule = tk.Frame(frame, bg=self.box_color)
        self.label_schedule = tk.Label(schedule, bg=self.box_color)
        self.progressbar = HorizontalProgressBar(schedule, **HoverChannelEpg.progress_bar)  # type:ignore
        self.label_descr = tk.Label(frame, bg=self.box_color, justify=tk.LEFT)
        self.label_title.pack(anchor=tk.W)
        schedule.pack(anchor=tk.W, fill=tk.X, expand=True)
        self.label_schedule.pack(anchor=tk.W, side=tk.LEFT)
        self.progressbar.pack(padx=(10, 0), anchor=tk.W, side=tk.LEFT, fill=tk.X, expand=True)
        self.label_descr.pack(anchor=tk.W)
        return frame

    def show(self, title: str, schedule: str, descr: str, progress: int) -> None:
        self.label_title.config(**self.stl_title(title).to_tk)
        self.label_schedule.config(**self.stl_schedule(schedule).to_tk)
        self.progressbar.config(value=progress)
        self.label_descr.config(**self.stl_descr(descr).to_tk)
        self.update_and_show()
