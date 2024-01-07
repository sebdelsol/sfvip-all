import tkinter as tk

from ...winapi import win
from .fx import Fade
from .sticky import Offset, StickyWindow, StickyWindows
from .style import Style


class HoverMessageWindow(StickyWindow):
    """splash screen"""

    _bg = "#101010"
    _stl = Style().font("Calibri").font_size(14).bold
    _offset = Offset(regular=(30, 35), center=(0.025, 0))

    def __init__(self) -> None:
        super().__init__(HoverMessageWindow._offset, bg=HoverMessageWindow._bg)
        self.attributes("-alpha", 0)
        self.withdraw()
        self.label = tk.Label(self, bg=HoverMessageWindow._bg)
        self.label.pack()
        self.attributes("-transparentcolor", HoverMessageWindow._bg)
        win.set_click_through(self.winfo_id())
        self._fade = Fade(self)

    def show(self, message: str) -> None:
        self.label.config(**HoverMessageWindow._stl(message).to_tk)
        self.attributes("-alpha", 0.9)
        self.deiconify()
        StickyWindows.update_position(self)
        self._fade.fade(1000, out=True, wait_ms=2000)
