import tkinter as tk
from abc import ABC, abstractmethod

from ...winapi import win
from .fx import Fade
from .sticky import Offset, StickyWindow, StickyWindows
from .style import Style
from .widgets import RoundedBox

# TODO check max width & height


class _HoverMessageBox(StickyWindow, ABC):
    offset: Offset
    bg = "black"
    alpha = 0.9
    wait_before_fade = 3000
    fade_duration = 1500
    box_color = "#101010"
    radius = 7

    def __init__(self) -> None:
        super().__init__(self.offset, bg=self.bg)
        self.attributes("-alpha", 0)
        self.withdraw()
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

    @abstractmethod
    def get_widget(self) -> tk.Widget:
        ...


class HoverMessage(_HoverMessageBox):
    offset = Offset(regular=(20, 35))
    stl = Style().font("Calibri").font_size(14).bold

    def get_widget(self) -> tk.Widget:
        self.label = tk.Label(self, bg=self.box_color)
        return self.label

    def show(self, message: str) -> None:
        self.label.config(**self.stl(message).to_tk)
        self.update_and_show()


class HoverChannelEpg(_HoverMessageBox):
    offset = Offset(regular=(20, 0), center=(0, 0.75))
    stl_title = Style().font("Calibri").font_size(20).wrap(50).bold
    stl_schedule = Style().font("Calibri").font_size(15).bold
    stl_descr = Style().font("Calibri").font_size(14).wrap(100)

    def get_widget(self) -> tk.Widget:
        frame = tk.Frame(self, bg=self.box_color)
        self.label_title = tk.Label(frame, bg=self.box_color, justify=tk.LEFT)
        self.label_schedule = tk.Label(frame, bg=self.box_color)
        self.label_descr = tk.Label(frame, bg=self.box_color, justify=tk.LEFT)
        self.label_title.pack(anchor=tk.W)
        self.label_schedule.pack(anchor=tk.W)
        self.label_descr.pack(anchor=tk.W)
        return frame

    def show(self, title: str, schedule: str, descr: str) -> None:
        self.label_title.config(**self.stl_title(title).to_tk)
        self.label_schedule.config(**self.stl_schedule(schedule).to_tk)
        self.label_descr.config(**self.stl_descr(descr).to_tk)
        self.update_and_show()
