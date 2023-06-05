import tkinter as tk
from typing import NamedTuple, Optional, Self

from .exception import UIError


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

    def valid(self) -> bool:
        return all(attr != Rect._default for attr in self)  # pylint: disable=not-an-iterable

    def position(self, offset: _Offset, is_maximized: bool, w: int, h: int) -> Self:
        if offset.centered:
            return Rect(self.x + (self.w - w) * 0.5, self.y + (self.h - h) * 0.5, w, h)
        x, y = offset.maximized if is_maximized else offset.regular
        return Rect(self.x + x, self.y + y, w, h)

    def to_geometry(self) -> str:
        return f"{self.w}x{self.h}+{self.x:.0f}+{self.y:.0f}"


class WinState(NamedTuple):
    rect: Rect
    is_minimized: bool
    no_border: bool
    is_maximized: bool
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

    @staticmethod
    def instances() -> list["_StickyWindow"]:
        return _StickyWindow._instances

    def follow(self, state: WinState) -> None:
        if state.no_border or state.is_minimized:
            if self.winfo_ismapped():
                self.stop_following()
        elif state.rect.valid():
            # position changed ?
            if state.rect != self._rect:
                w, h = self.winfo_reqwidth(), self.winfo_reqheight()
                rect = state.rect.position(self._offset, state.is_maximized, w, h)
                self.geometry(rect.to_geometry())
                self._rect = state.rect
            # else lift me to stay on top
            else:
                self.attributes("-topmost", True)
                self.attributes("-topmost", state.is_topmost)
                self.lift()
                if not self.winfo_ismapped():
                    self.start_following()

    def stop_following(self) -> None:
        self.withdraw()

    def start_following(self) -> None:
        self.deiconify()


def follow(state: WinState) -> None:
    for sticky in _StickyWindow.instances():
        try:
            sticky.follow(state)
        # catch tcl error due to alt-f4
        # and propagate as UIError
        except tk.TclError as err:
            raise UIError from err


def stop_following() -> None:
    for sticky in _StickyWindow.instances():
        try:
            sticky.stop_following()
        # clean exit when exiting due to alt-f4
        except tk.TclError:
            pass
