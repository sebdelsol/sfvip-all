import tkinter as tk
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from .fx import _Pulse
from .infos import _InfosWindow
from .sticky import Rect, _Offset, _StickyWindow
from .widgets import _Border, _get_border


class _PulseReason(Enum):
    PROXIES = auto()
    DOWNLOAD = auto()
    UNKNOWN = auto()


class _LogoTheme:
    bg = "#242424"
    border = _Border(bg="#808080", size=1, relief="")
    pulse_warn = _Pulse.Args(bg, "#902424", frequency=1)
    pulse_ok = _Pulse.Args(bg, "#249024", frequency=0.33)


class _LogoWindow(_StickyWindow):
    """logo, mouse hover to show infos, pulse color show status"""

    _offset = _Offset(regular=(-36, 0), maximized=(0, 0))

    def __init__(self, logo_path: Path, infos: _InfosWindow) -> None:
        super().__init__(_LogoWindow._offset, takefocus=0)
        self._infos = infos
        self._image = tk.PhotoImage(file=logo_path)  # keep a reference for tkinter
        border = _get_border(_LogoTheme.border)
        self._logo = tk.Label(self, bg=_LogoTheme.pulse_ok.color1, image=self._image, takefocus=0, **border)
        self._logo.pack()
        self._pulse = _Pulse(self._logo)
        self._warn_reasons: set[_PulseReason] = set()
        self.set_pulse(ok=True, reason=_PulseReason.UNKNOWN)
        self._bind_event("<Map>", self._pulse.start)
        self._bind_event("<Unmap>", self._pulse.stop)
        self._bind_event("<Enter>", self._infos.show)
        self._bind_event("<Leave>", self._infos.hide)

    def _bind_event(self, event_name: str, do: Callable[[], None]) -> None:
        def on_event(event: tk.Event) -> None:
            if event.widget == self:
                do()

        self.bind(event_name, on_event)

    def set_pulse(self, ok: bool, reason: _PulseReason) -> None:
        (self._warn_reasons.discard if ok else self._warn_reasons.add)(reason)
        self._pulse.set(*(_LogoTheme.pulse_warn if self._warn_reasons else _LogoTheme.pulse_ok))

    def change_position(self, rect: Rect) -> None:
        super().change_position(rect)
        self._logo.config(highlightthickness=0 if rect.is_maximized else 1)
