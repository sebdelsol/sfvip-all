import itertools
import tkinter as tk
from abc import ABC, abstractmethod
from typing import Any

from src.mitm.epg import ShowEpg

from ...mitm.epg.programme import EPGprogrammeM3U
from ...winapi import win
from .fx import Fade
from .sticky import Offset, StickyWindow, sticky_windows
from .style import Style
from .widgets import HorizontalProgressBar, RoundedBox

# TODO check max width & height


class _HoverMessageBox(StickyWindow, ABC):
    show_when_no_border = True
    click_through = True
    max_height = None

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
        if self.click_through:
            win.set_click_through(self.winfo_id())
        self.box = RoundedBox(
            self, bg=self.bg, radius=self.radius, box_color=self.box_color, max_height=self.max_height
        )
        self.box.pack()
        self.box.add_widget(self.get_widget())
        self._fade = Fade(self)

    def update_and_show(self) -> None:
        self.attributes("-alpha", self.alpha)
        self.deiconify()
        self.box.update_widget()
        sticky_windows.update_position(self)
        if self.wait_before_fade is not None:
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
    stl_title = Style().font("Calibri").font_size(12).bold
    stl_schedule = Style().font("Calibri").font_size(14).bold
    stl_descr = Style().font("Calibri").font_size(14).wrap(100)
    progress_bar = dict(bg="#606060", fg="#1c8cbc", height=10, length=400)

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

    def show(self, epg: ShowEpg, now: float) -> None:
        if epg.programmes and len(epg.programmes):
            prg = epg.programmes[0]
            if prg.start_timestamp <= now:  # check it's now
                name = f"{epg.name} - " if epg.name else ""
                self.label_title.config(**self.stl_title(f"{name}{prg.title}").to_tk)
                self.label_schedule.config(**self.stl_schedule(f"{prg.start}").to_tk)
                self.progressbar.config(value=round(100 * (now - prg.start_timestamp) / prg.duration))
                if prg.descr:
                    self.label_descr.config(**self.stl_descr(prg.descr).to_tk)
                    self.label_descr.pack(anchor=tk.W)
                else:
                    self.label_descr.pack_forget()
                self.update_and_show()


class Programme(tk.Frame):
    border_color = "#303030"

    def __init__(self, master: tk.BaseWidget, bg: str, **kwargs: Any) -> None:
        super().__init__(master, bg=bg, highlightthickness=1, highlightbackground=self.border_color, **kwargs)
        self.label_title = tk.Label(self, bg=bg, justify=tk.LEFT)
        self.label_schedule = tk.Label(self, bg=bg, justify=tk.LEFT)
        self.label_descr = tk.Label(self, bg=bg, justify=tk.LEFT)
        self.label_title.pack(anchor=tk.W)
        self.label_schedule.pack(anchor=tk.W)
        self.label_descr.pack(anchor=tk.W)

    def set(self, prg: EPGprogrammeM3U) -> None:
        self.label_title.config(**HoverChannelEpg.stl_title(prg.title).to_tk)
        self.label_schedule.config(**HoverChannelEpg.stl_schedule(f"{prg.start} - {prg.end}").to_tk)
        if prg.descr:
            self.label_descr.config(**HoverChannelEpg.stl_descr(prg.descr).to_tk)
            self.label_descr.pack(anchor=tk.W)
        else:
            self.label_descr.pack_forget()


# TODO close button
class HoverChannelProgrammes(_HoverMessageBox):
    wait_before_fade = None
    click_through = False
    max_height = 600
    offset = Offset(regular=(22, 45))
    stl_channel = Style().font("Calibri").font_size(15).bold
    n_programme = 15

    def get_widget(self) -> tk.Widget:
        frame = tk.Frame(self, bg=self.box_color)
        self.channel = tk.Label(frame, bg=self.box_color, justify=tk.LEFT)
        self.channel.pack(anchor=tk.W)
        self.programmes = [Programme(frame, self.box_color) for _ in range(self.n_programme)]
        for programme in self.programmes:
            programme.pack(anchor=tk.W, pady=5, fill=tk.X, expand=True)
        return frame

    def show(self, epg: ShowEpg) -> None:
        if epg.programmes:
            self.channel.config(**self.stl_channel(f"EPG - {epg.name or ''}").to_tk)
            for prg, shown_prg in itertools.zip_longest(epg.programmes[: self.n_programme], self.programmes):
                if prg:
                    shown_prg.pack()
                    shown_prg.set(prg)
                else:
                    shown_prg.pack_forget()
        self.update_and_show()
