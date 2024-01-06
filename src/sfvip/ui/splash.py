import tkinter as tk

from ...winapi import win
from .fx import Fade
from .sticky import Maximized, Offset, Rect, StickyWindow


class SplashWindow(StickyWindow):
    """splash screen"""

    _bg = "black"  # color for set_click_through
    _offset = Offset(center=(0.5, 0.5))

    def __init__(self, image: tk.PhotoImage) -> None:
        super().__init__(SplashWindow._offset, bg=SplashWindow._bg)
        tk.Label(self, bg=SplashWindow._bg, image=image).pack()
        self.attributes("-transparentcolor", SplashWindow._bg)
        win.set_click_through(self.winfo_id())
        self._fade = Fade(self)
        self.update()  # force size computation

    def show(self, rect: Rect) -> None:
        if rect.valid():
            self.change_position(Maximized.fix(rect))
            self.bring_to_front(is_topmost=True, is_foreground=True)
        self.attributes("-alpha", 1.0)
        self.deiconify()

    def hide(self, fade_duration_ms: int, wait_ms: int = 0) -> None:
        self._fade.fade(fade_duration_ms, out=True, wait_ms=wait_ms)
