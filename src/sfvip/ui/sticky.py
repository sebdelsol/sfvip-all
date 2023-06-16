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

    _instances = []

    def __init__(self, offset: _Offset, **kwargs) -> None:
        _StickyWindow._instances.append(self)
        super().__init__(**kwargs)
        self.withdraw()
        self.overrideredirect(True)
        self._offset = offset
        self._rect: Optional[Rect] = None
        self._monitor_areas = monitor.monitors_areas()
        # prevent closing (alt-f4)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def follow(self, state: WinState) -> None:
        if state.no_border or state.is_minimized:
            if self.state() == "normal":
                self.withdraw()
        elif state.rect.valid():
            if state.rect != self._rect:
                self._on_changed_position(state)
                self._rect = state.rect
            else:
                if self.state() != "normal":
                    self.deiconify()
                self._on_bring_to_front(state)

    def _fix_maximized(self, rect: Rect) -> Rect:
        if rect.is_maximized:
            # fix possible wrong zoomed coords
            for area in self._monitor_areas:
                work_area = Rect(*area.work_area, True)
                if rect.is_middle_inside(work_area):
                    return work_area
        return rect

    def _on_changed_position(self, state: WinState) -> None:
        rect = self._fix_maximized(state.rect)
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        rect = rect.position(self._offset, w, h)
        self.geometry(rect.to_geometry())

    def _on_bring_to_front(self, state: WinState) -> None:
        if state.is_topmost:
            self.attributes("-topmost", True)
        else:
            self.attributes("-topmost", True)
            self.attributes("-topmost", False)

    @staticmethod
    def instances() -> list["_StickyWindow"]:
        return _StickyWindow._instances


def follow_all(state: WinState) -> None:
    for sticky in _StickyWindow.instances():
        sticky.follow(state)


def hide_all() -> None:
    for sticky in _StickyWindow.instances():
        sticky.withdraw()
