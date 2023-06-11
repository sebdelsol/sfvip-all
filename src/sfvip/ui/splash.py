import tkinter as tk

from ...winapi import win
from .fx import _Fade
from .sticky import Rect, WinState, _Offset, _StickyWindow


class _SplashWindow(_StickyWindow):
    """splash screen"""

    _bg = "black"  # color for set_click_through
    _offset = _Offset(centered=True)

    def __init__(self, image: tk.PhotoImage) -> None:
        super().__init__(_SplashWindow._offset, bg=_SplashWindow._bg)
        tk.Label(self, bg=_SplashWindow._bg, image=image).pack()
        self.attributes("-transparentcolor", _SplashWindow._bg)
        win.set_click_through(self.winfo_id())
        self._fade = _Fade(self)

    def show(self, rect: Rect) -> None:
        self.follow(WinState(rect, is_minimized=False, no_border=False, is_topmost=True))
        self.attributes("-alpha", 1.0)
        self.deiconify()

    def hide(self, fade_duration_ms, wait_ms=0) -> None:
        self._fade.fade(fade_duration_ms, out=True, wait_ms=wait_ms)
