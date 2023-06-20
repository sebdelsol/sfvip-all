import threading
import tkinter as tk
from typing import NamedTuple, Optional, Self

from ...winapi import monitor


class _Offset(NamedTuple):
    regular: tuple[int, int] = 0, 0
    maximized: tuple[int, int] = 0, 0
    centered: bool = False


class Rect(NamedTuple):
    _default = float("inf")
    x: float = _default
    y: float = _default
    w: float = _default
    h: float = _default
    is_maximized: bool = False

    def valid(self) -> bool:
        return all(attr != Rect._default for attr in self)  # pylint: disable=not-an-iterable

    def position(self, offset: _Offset, w: int, h: int) -> Self:
        if offset.centered:
            return Rect(self.x + (self.w - w) * 0.5, self.y + (self.h - h) * 0.5, w, h)
        x, y = offset.maximized if self.is_maximized else offset.regular
        return Rect(self.x + x, self.y + y, w, h)

    def to_geometry(self) -> str:
        return f"{self.w}x{self.h}+{self.x:.0f}+{self.y:.0f}"

    def is_middle_inside(self, rect: Self) -> bool:
        x, y = self.x + self.w * 0.5, self.y + self.h * 0.5
        return rect.x <= x <= rect.x + rect.w and rect.y <= y <= rect.y + rect.h


class WinState(NamedTuple):
    rect: Rect
    is_minimized: bool
    no_border: bool
    is_topmost: bool


class _StickyWindow(tk.Toplevel):
    """follow position, hide & show when needed"""

    def __init__(self, offset: _Offset, **kwargs) -> None:
        super().__init__(**kwargs)
        self.withdraw()
        self.overrideredirect(True)
        self._offset = offset
        # prevent closing (alt-f4)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        StickyWindows.register(self)

    def withdraw(self) -> None:
        if self.state() == "normal":
            super().withdraw()

    def change_position(self, rect: Rect) -> None:
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        rect = rect.position(self._offset, w, h)
        self.geometry(rect.to_geometry())

    def bring_to_front(self, is_topmost: bool) -> None:
        if self.state() != "normal":
            self.deiconify()
        if is_topmost:
            self.attributes("-topmost", True)
        else:
            self.attributes("-topmost", True)
            self.attributes("-topmost", False)


class StickyWindows:
    """pure class, handle on_state_changed on all _StickyWindow"""

    _current_rect: Optional[Rect] = None
    _instances: list[_StickyWindow] = []
    _lock = threading.Lock()

    @staticmethod
    def register(instance: _StickyWindow) -> None:
        StickyWindows._instances.append(instance)

    @staticmethod
    def get_rect() -> Optional[Rect]:
        return StickyWindows._current_rect

    @staticmethod
    def change_position_all(rect: Rect) -> None:
        for sticky in StickyWindows._instances:
            sticky.change_position(rect)

    @staticmethod
    def bring_to_front_all(is_topmost: bool) -> None:
        for sticky in StickyWindows._instances:
            sticky.bring_to_front(is_topmost)

    @staticmethod
    def hide_all() -> None:
        for sticky in StickyWindows._instances:
            sticky.withdraw()

    @staticmethod
    def on_state_changed(state: WinState) -> None:
        with StickyWindows._lock:  # sure to be sequential
            if state.no_border or state.is_minimized:
                StickyWindows.hide_all()
            elif state.rect.valid():
                if state.rect != StickyWindows._current_rect:
                    StickyWindows._current_rect = state.rect
                    StickyWindows.change_position_all(FixMaximized.fix(state.rect))
                else:
                    StickyWindows.bring_to_front_all(state.is_topmost)


class FixMaximized:
    _monitor_rects = [Rect(*area.work_area, True) for area in monitor.monitors_areas()]

    @staticmethod
    def fix(rect: Rect) -> Rect:
        if rect.is_maximized:
            # fix possible wrong zoomed coords
            for monitor_rect in FixMaximized._monitor_rects:
                if rect.is_middle_inside(monitor_rect):
                    return monitor_rect
        return rect
