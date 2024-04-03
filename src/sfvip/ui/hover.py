import itertools
import tkinter as tk
from typing import Any, Optional

from src.mitm.epg import ShowEpg

from ...mitm.epg.programme import EPGprogrammeM3U
from ...winapi import win
from .fx import Fade
from .sticky import Offset, Rect, StickyWindow, sticky_windows
from .style import Style
from .widgets import Border, Button, GetWidgetT, HorizontalProgressBar, RoundedBox, RoundedBoxScroll


class _HoverWindow(StickyWindow):
    show_when_no_border = True
    click_through = True
    offset: Offset
    bg = "black"
    alpha = 0.9
    wait_before_fade = 3000
    auto_fade_out_duration = 1500
    fade_duration = 250
    box_color = "#101010"
    radius = 7
    x_margin = 150

    def __init__(self, get_widget: GetWidgetT, get_scrolling_widget: Optional[GetWidgetT] = None) -> None:
        super().__init__(self.offset, bg=self.bg)
        self.attributes("-alpha", 0)
        self.withdraw()
        self.attributes("-transparentcolor", self.bg)
        if self.click_through:
            win.set_click_through(self.winfo_id())
        if get_scrolling_widget:
            self.box = RoundedBoxScroll(
                self,
                bg=self.bg,
                radius=self.radius,
                box_color=self.box_color,
                get_widget=get_widget,
                get_scrolling_widget=get_scrolling_widget,
            )
        else:
            self.box = RoundedBox(
                self,
                bg=self.bg,
                radius=self.radius,
                box_color=self.box_color,
                get_widget=get_widget,
            )
        self.box.pack()
        self._fade = Fade(self)
        self._size = None, None

    def update_and_show(self) -> None:
        if rect := sticky_windows.get_rect():
            self.change_position(rect, forced=True)
        if self.wait_before_fade is not None:
            self._fade.fade_in_and_out(
                self.fade_duration, self.auto_fade_out_duration, self.wait_before_fade, max_alpha=self.alpha
            )
        else:
            self._fade.fade(self.fade_duration, out=False, max_alpha=self.alpha)

    def change_position(self, rect: Rect, forced: bool = False) -> None:
        if forced or self.is_shown():
            x, y = self.offset.regular
            size = (
                max(10, rect.w - (x + self.radius + _HoverWindow.x_margin) * 2),
                max(10, rect.h - (y + self.radius) * 2),
            )
            if forced or size != self._size:
                self.set_width(size[0])
                self.box.update_widget(size[1])
                self._size = size
        super().change_position(rect)

    def set_width(self, width: Optional[float]) -> None:
        pass

    def hide(self) -> None:
        self._fade.fade(self.fade_duration, out=True)

    def is_shown(self) -> bool:
        return self.attributes("-alpha") != 0


class HoverMessage(_HoverWindow):
    offset = Offset(regular=(22, 84))
    stl = Style().font("Calibri").font_size(14).bold

    def __init__(self) -> None:
        self.label = None
        super().__init__(self.get_widget)

    def get_widget(self, master: tk.Widget) -> tk.Widget:
        self.label = tk.Label(master, bg=self.box_color)
        return self.label

    def show(self, message: str) -> None:
        if self.label:
            self.label.config(**self.stl(message).to_tk)
            self.update_and_show()

    def set_width(self, width: Optional[float]) -> None:
        if width and self.label:
            self.label.config(wraplength=width)


class ProgrammeNow(tk.Frame):
    stl_title = Style().font("Calibri").font_size(12).bold
    stl_schedule = Style().font("Calibri").font_size(14).bold
    stl_descr = Style().font("Calibri").font_size(14)
    progress_bar = dict(bg="#606060", fg="#1c8cbc", height=10)

    def __init__(self, master: tk.BaseWidget, bg: str, **kwargs: Any) -> None:
        super().__init__(master, bg=bg, **kwargs)
        self.label_title = tk.Label(self, bg=bg, justify=tk.LEFT)
        schedule = tk.Frame(self, bg=bg)
        self.label_schedule = tk.Label(schedule, bg=bg, justify=tk.LEFT)
        self.progressbar = HorizontalProgressBar(schedule, **self.progress_bar)  # type:ignore
        self.label_descr = tk.Label(self, bg=bg, justify=tk.LEFT)
        self.label_title.pack(anchor=tk.W)
        schedule.pack(anchor=tk.W, fill=tk.X, expand=True)
        self.label_schedule.pack(anchor=tk.W, side=tk.LEFT)
        self.progressbar.pack(padx=(10, 0), anchor=tk.W, side=tk.LEFT, fill=tk.X, expand=True)
        self.label_descr.pack(anchor=tk.W)

    def set(self, name: Optional[str], prg: EPGprogrammeM3U, now: float) -> None:
        if prg.start_timestamp <= now and prg.duration:  # check it's now and lasts something
            name = f"{name} - " if name else ""
            self.label_title.config(**self.stl_title(f"{name}{prg.title}").to_tk)
            self.label_schedule.config(**self.stl_schedule(f"{prg.start}").to_tk)
            self.progressbar.config(value=round(100 * (now - prg.start_timestamp) / prg.duration))
            if prg.descr:
                self.label_descr.config(**self.stl_descr(prg.descr).to_tk)
                self.label_descr.pack(anchor=tk.W)
            else:
                self.label_descr.pack_forget()

    def set_width(self, width: Optional[float]) -> None:
        if width:
            padx = sum(self.progressbar.pack_info()["padx"], 0)  # type: ignore
            schedule_width = self.label_schedule.winfo_reqwidth() + padx
            self.progressbar.config(length=max(10, width - schedule_width))
            self.label_title.config(wraplength=width)
            self.label_descr.config(wraplength=width)


class HoverChannelEpg(_HoverWindow):
    offset = Offset(regular=(22, 0), center=(0, 0.85))

    def __init__(self) -> None:
        self.programme = None
        super().__init__(self.get_widget)

    def get_widget(self, master: tk.Widget) -> tk.Widget:
        self.programme = ProgrammeNow(master, bg=self.box_color)
        return self.programme

    def show(self, epg: ShowEpg, now: float) -> None:
        if epg.programmes and len(epg.programmes) and self.programme:
            self.programme.set(epg.name, epg.programmes[0], now)
            self.update_and_show()

    def set_width(self, width: Optional[float]) -> None:
        if self.programme:
            self.programme.set_width(width)


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
        self.is_packed = False

    def set(self, prg: EPGprogrammeM3U) -> None:
        self.label_title.config(**ProgrammeNow.stl_title(prg.title).to_tk)
        self.label_schedule.config(**ProgrammeNow.stl_schedule(f"{prg.start} - {prg.end}").to_tk)
        if prg.descr:
            self.label_descr.config(**ProgrammeNow.stl_descr(prg.descr).to_tk)
            self.label_descr.pack(anchor=tk.W)
        else:
            self.label_descr.pack_forget()

    def set_width(self, width: Optional[float]) -> None:
        if width:
            self.label_title.config(wraplength=width)
            self.label_descr.config(wraplength=width)

    def pack(self, **kw: Any) -> None:
        super().pack(**kw)
        self.is_packed = True

    def pack_forget(self) -> None:
        super().pack_forget()
        self.is_packed = False


class HoverChannelProgrammes(_HoverWindow):
    wait_before_fade = None
    click_through = False
    offset = HoverMessage.offset
    stl_channel = Style().font("Calibri").font_size(15).bold
    stl_button = Style().font("Calibri").font_size(10)
    n_programme = 15

    def __init__(self) -> None:
        self.channel = None
        self.programmes = None
        super().__init__(self.get_widget, self.get_scrolling_widget)

    def get_widget(self, master: tk.Widget) -> tk.Widget:
        frame = tk.Frame(master, bg=self.box_color)
        close = Button(
            frame,
            **self.stl_button(" x ").to_tk,
            bg="#1F1E1D",
            mouseover="#3F3F41",
            border=Border(bg="grey", size=0.75, relief="groove"),
        )
        self.channel = tk.Label(frame, padx=10, bg=self.box_color, justify=tk.LEFT)
        close.pack(side=tk.LEFT, anchor=tk.W)
        self.channel.pack(side=tk.LEFT, anchor=tk.W)
        close.bind("<Button-1>", lambda _: self.hide())
        return frame

    def get_scrolling_widget(self, master: tk.Widget) -> tk.Widget:
        frame = tk.Frame(master, bg=self.box_color)
        self.programmes = [Programme(frame, self.box_color) for _ in range(self.n_programme)]
        for programme in self.programmes:
            programme.pack(anchor=tk.W, pady=5, fill=tk.X, expand=True)
        return frame

    def show(self, epg: ShowEpg) -> None:
        if epg.programmes and self.channel and self.programmes:
            self.channel.config(**self.stl_channel(f"EPG - {epg.name or ''}").to_tk)
            for prg, shown_prg in itertools.zip_longest(epg.programmes[: self.n_programme], self.programmes):
                if prg:
                    shown_prg.pack()
                    shown_prg.set(prg)
                else:
                    shown_prg.pack_forget()
            self.update_and_show()

    def set_width(self, width: Optional[float]) -> None:
        if width and self.programmes:
            for shown_prg in self.programmes:
                if shown_prg.is_packed:
                    shown_prg.set_width(width)
