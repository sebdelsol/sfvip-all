import math
import threading
import time
import tkinter as tk
from typing import NamedTuple, Self


class _Color(NamedTuple):
    r: int
    g: int
    b: int

    @classmethod
    def from_str(cls, color: str) -> Self:
        color = color.lstrip("#")
        return cls(*(int(color[i : i + 2], 16) for i in (0, 2, 4)))

    def blend_with(self, color: Self, t: float) -> Self:
        assert 0.0 <= t <= 1.0
        return _Color(
            round(self.r * (1 - t) + color.r * t),
            round(self.g * (1 - t) + color.g * t),
            round(self.b * (1 - t) + color.b * t),
        )

    def to_str(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


class _Pulse:
    """pulse bg of a widget, between color1 & color2 @frequency"""

    class Args(NamedTuple):
        color1: str
        color2: str
        frequency: float

    _pulse_dt_ms: int = 100  # reduce load

    def __init__(self, widget: tk.Widget) -> None:
        self._after = None
        self._widget = widget
        self._color1 = _Color.from_str("#000000")
        self._color2 = _Color.from_str("#000000")
        self._two_pi_frequency = 2 * math.pi
        self._lock = threading.Lock()

    def set(self, color1: str, color2: str, frequency: float):
        with self._lock:
            self._color1 = _Color.from_str(color1)
            self._color2 = _Color.from_str(color2)
            self._two_pi_frequency = 2 * math.pi * frequency

    def _pulse(self) -> None:
        with self._lock:
            self._after = None
            sin = math.sin(self._two_pi_frequency * time.perf_counter())
            color = self._color1.blend_with(self._color2, (sin + 1) * 0.5)  # keep in [0,1]
            self._widget.configure(bg=color.to_str())  # type: ignore
            self._after = self._widget.after(_Pulse._pulse_dt_ms, self._pulse)

    def start(self) -> None:
        self.stop()
        self._after = self._widget.after(0, self._pulse)

    def stop(self) -> None:
        if self._after:
            self._widget.after_cancel(self._after)


class _Fade:
    """fade in & out a toplevel window"""

    _fade_dt_ms: int = 25

    def __init__(self, win: tk.Toplevel) -> None:
        self._win = win
        self._after = None

    def fade(self, fade_duration_ms: int, out: bool, wait_ms: int = 0) -> None:
        dalpha = _Fade._fade_dt_ms / fade_duration_ms if fade_duration_ms > 0 else 1.0
        dalpha = (-1 if out else 1) * dalpha
        if self._after:
            self._win.after_cancel(self._after)

        def fade() -> None:
            self._after = None
            alpha = self._win.attributes("-alpha") + dalpha
            self._win.attributes("-alpha", max(0.0, min(alpha, 1.0)))
            if 0.0 < alpha < 1.0:
                self._after = self._win.after(_Fade._fade_dt_ms, fade)
            elif out:
                self._win.withdraw()

        if not out:
            self._win.deiconify()
        self._after = self._win.after(wait_ms, fade)
