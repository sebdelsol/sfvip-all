import tkinter as tk
from pathlib import Path
from typing import Callable

from .fx import _Pulse
from .infos import _InfosWindow
from .sticky import Rect, _Offset, _StickyWindow
from .widgets import _set_border


class _LogoTheme:
    bg = "#242424"
    border = dict(bg="#808080", size=1)
    pulse_warn = _Pulse.Args(bg, "#902424", frequency=1)
    pulse_ok = _Pulse.Args(bg, "#249024", frequency=0.33)


class _LogoWindow(_StickyWindow):
    """logo, mouse hover to show infos, pulse color show status"""

    _offset = _Offset(regular=(-36, 0), maximized=(0, 0))

    def __init__(self, logo_path: Path, infos: _InfosWindow) -> None:
        super().__init__(_LogoWindow._offset, takefocus=0)
        self._infos = infos
        self._image = tk.PhotoImage(file=logo_path)  # keep a reference for tkinter
        border = _set_border(**_LogoTheme.border)  # type: ignore
        self._logo = tk.Label(self, bg=_LogoTheme.pulse_ok.color1, image=self._image, takefocus=0, **border)
        self._logo.pack()
        self._pulse = _Pulse(self._logo)
        self.set_pulse(ok=True)
        self._bind_event("<Map>", self._pulse.start)
        self._bind_event("<Unmap>", self._pulse.stop)
        self._bind_event("<Enter>", self._infos.show)
        self._bind_event("<Leave>", self._infos.hide)

    def _bind_event(self, event_name: str, do: Callable[[], None]) -> None:
        def on_event(event: tk.Event) -> None:
            if event.widget == self:
                do()

        self.bind(event_name, on_event)

    def set_pulse(self, ok: bool) -> None:
        self._pulse.set(*(_LogoTheme.pulse_ok if ok else _LogoTheme.pulse_warn))

    def change_position(self, rect: Rect) -> None:
        super().change_position(rect)
        self._logo.config(highlightthickness=0 if rect.is_maximized else 1)
