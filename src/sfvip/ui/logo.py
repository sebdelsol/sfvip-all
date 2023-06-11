import tkinter as tk
from pathlib import Path

from .fx import _Pulse
from .infos import _InfosWindow
from .sticky import _Offset, _StickyWindow


class _LogoTheme:
    bg = "#242424"
    pulse_warn = _Pulse.Args(bg, "#990000", frequency=1)
    pulse_ok = _Pulse.Args(bg, "#006000", frequency=0.33)


class _LogoWindow(_StickyWindow):
    """logo, mouse hover to show infos"""

    _offset = _Offset(regular=(2, 2), maximized=(0, 0))

    def __init__(self, logo_path: Path, infos: _InfosWindow) -> None:
        super().__init__(_LogoWindow._offset, takefocus=0)
        self._infos = infos
        self._image = tk.PhotoImage(file=logo_path)  # keep a reference for tkinter
        logo = tk.Label(self, bg=_LogoTheme.pulse_ok.color1, image=self._image, takefocus=0)
        logo.pack()
        self.bind("<Enter>", lambda _: self._infos.show())
        self.bind("<Leave>", lambda _: self._infos.hide())
        self._pulse = _Pulse(logo)
        self.set_pulse(ok=True)

    def set_pulse(self, ok: bool) -> None:
        self._pulse.set(*(_LogoTheme.pulse_ok if ok else _LogoTheme.pulse_warn))

    def start_following(self) -> None:
        super().start_following()
        self._pulse.start()

    def stop_following(self) -> None:
        super().stop_following()
        self._pulse.stop()
