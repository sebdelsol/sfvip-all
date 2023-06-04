import math
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Iterator, NamedTuple, Optional, Self

from winapi import set_click_through

# TODO add a scrollbar if to much infos
# TODO separate ui named package

WIDGET_BG = "#242424"


class UIError(Exception):
    pass


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


class _Style:
    def __init__(self, bg: str, font: str, font_size: int) -> None:
        self._bg = bg
        self._font = font
        self._font_size = font_size

    def __call__(self, fg: str, font_dsize: int = 0, font_style: str = "") -> dict[str, Any]:
        font_style = f"{self._font} {font_style}" if font_style else self._font
        return dict(bg=self._bg, fg=fg, font=(font_style, self._font_size + font_dsize))


INFO_STL = _Style(bg=WIDGET_BG, font="Calibri", font_size=12)
INFO_ARROW = "➞", INFO_STL("#707070", 3)
INFO_MAX_STR = 30
INFO_NAME = "white"
INFO_PROXY = "light green"
INFO_UPSTREAM = "#A0A0A0"


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str

    def get_text_kw(self) -> Iterator[tuple[str, dict[str, Any]]]:
        yield self.name[:INFO_MAX_STR], INFO_STL(INFO_NAME)
        yield INFO_ARROW
        yield (self.proxy[:INFO_MAX_STR], INFO_STL(INFO_PROXY)) if self.proxy else ("No Proxy", INFO_STL("red"))
        yield INFO_ARROW
        yield (self.upstream[:INFO_MAX_STR], INFO_STL(INFO_UPSTREAM)) if self.upstream else ("-", INFO_STL("grey"))

    def valid(self) -> bool:
        return bool(self.proxy)

    @staticmethod
    def get_headers(app_name: str, app_version: str) -> Iterator[tuple[str, dict[str, Any]]]:
        yield "Account", INFO_STL(INFO_NAME, 1, "bold")
        yield f"{app_name} v{app_version} Proxy", INFO_STL(INFO_PROXY, 1, "bold")
        yield "Account Proxy", INFO_STL(INFO_UPSTREAM, 1, "bold")


class _Fade:
    """fade in & out a toplevel window"""

    _fade_dt_ms: int = 25

    def __init__(self, win: tk.Toplevel) -> None:
        self._win = win
        self._after = None

    def fade(self, fade_duration_ms: int, out: bool) -> None:
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
        fade()


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
        self._pulse()

    def stop(self) -> None:
        with self._lock:
            if self._after:
                self._widget.after_cancel(self._after)


class _Sticky(tk.Toplevel):
    """follow position, hide & show when needed"""

    _instances = []

    def __init__(self, offset: _Offset, **kwargs) -> None:
        _Sticky._instances.append(self)
        super().__init__(**kwargs)
        self.withdraw()
        self.overrideredirect(True)
        self._offset = offset
        self._rect: Optional[Rect] = None

    @staticmethod
    def instances() -> list["_Sticky"]:
        return _Sticky._instances

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


class _Infos(_Sticky):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _border_color = "#333333"
    _border_size = 2
    _padx = 10

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__(_Infos._offset, bg=WIDGET_BG)
        self.attributes("-alpha", 0.0)
        bd = dict(
            highlightbackground=_Infos._border_color,
            highlightcolor=_Infos._border_color,
            highlightthickness=_Infos._border_size,
        )
        self._frame = frame = tk.Frame(self, bg=WIDGET_BG, **bd)
        self._headers = list(Info.get_headers(app_name, app_version))
        self._fade = _Fade(self)
        frame.bind("<Enter>", lambda _: self.show())
        frame.bind("<Leave>", lambda _: self.hide())
        frame.pack()

    def set(self, infos: list[Info]) -> bool:
        for item in self._frame.winfo_children():
            item.destroy()

        row = 0
        if not (valid := all(info.valid() for info in infos)):
            text, warn = "Relaunch Sfvip Player to have all proxies working", INFO_STL("red", 1, "bold")
            tk.Label(self._frame, text=text, **warn).grid(row=0, columnspan=6, padx=_Infos._padx)
            row = 1
        for column, (text, kw) in enumerate(self._headers):
            tk.Label(self._frame, text=text, **kw).grid(row=row, column=column * 2, padx=_Infos._padx)
        for drow, info in enumerate(infos):
            for column, (text, kw) in enumerate(info.get_text_kw()):
                tk.Label(self._frame, text=text, **kw).grid(row=row + drow + 1, column=column, padx=_Infos._padx)

        self.geometry("")  # to enable resizing
        return valid

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True)


class _Logo(_Sticky):
    """logo, mouse hover to show infos"""

    _pulse_warn = _Pulse.Args(WIDGET_BG, "#880000", frequency=0.75)
    _pulse_ok = _Pulse.Args(WIDGET_BG, "#006000", frequency=0.5)
    _offset = _Offset(regular=(2, 2), maximized=(0, 0))

    def __init__(self, logo_path: str, infos: _Infos) -> None:
        super().__init__(_Logo._offset)
        self._infos = infos
        logo_file = Path(__file__).parent.parent / logo_path
        self._image = tk.PhotoImage(file=logo_file)  # keep a reference for tkinter
        label = tk.Label(self, bg=_Logo._pulse_ok.color1, image=self._image)
        label.bind("<Enter>", lambda _: self._infos.show())
        label.bind("<Leave>", lambda _: self._infos.hide())
        label.pack()
        self._pulse = _Pulse(label)
        self.set_pulse(ok=True)

    def set_pulse(self, ok: bool) -> None:
        self._pulse.set(*(_Logo._pulse_ok if ok else _Logo._pulse_warn))

    def start_following(self) -> None:
        super().start_following()
        self._pulse.start()

    def stop_following(self) -> None:
        super().stop_following()
        self._pulse.stop()


class _Splash(_Sticky):
    """splash screen"""

    _bg = "black"  # color for set_click_through
    _offset = _Offset(centered=True)

    def __init__(self, image: tk.PhotoImage) -> None:
        super().__init__(_Splash._offset, bg=_Splash._bg)
        tk.Label(self, bg=_Splash._bg, image=image).pack()
        self.attributes("-transparentcolor", _Splash._bg)
        set_click_through(self.winfo_id())
        self._fade = _Fade(self)

    def show(self, rect: Rect) -> None:
        self.follow(WinState(rect, False, False, False, True))
        self.attributes("-alpha", 1.0)
        self.deiconify()

    def hide(self, fade_duration_ms) -> None:
        self._fade.fade(fade_duration_ms, out=True)


class UI(tk.Tk):
    """basic UI with a tk mainloop, the app has to run in a thread"""

    def __init__(self, app_name: str, app_version: str, splash_path: str, logo_path: str) -> None:
        super().__init__()
        self.withdraw()
        splash_file = Path(__file__).parent.parent / splash_path
        self._splash_img = tk.PhotoImage(file=splash_file)  # keep a reference for tk
        self.wm_iconphoto(True, self._splash_img)
        self._app_name = app_name
        self.splash = _Splash(self._splash_img)
        self._infos = _Infos(app_name, app_version)
        self._logo = _Logo(logo_path, self._infos)

    def run_in_thread(
        self, catch_exception: type[Exception], target: Callable[..., None], *args: Any, **kwargs: Any
    ) -> None:
        """
        run the target function in a thread,
        handle the mainloop and quit ui when done
        catch_exception is re-raised in the main thread
        """

        exceptions = []

        def _run():
            try:
                target(*args, **kwargs)
            except catch_exception as err:
                exceptions.append(err)
            finally:
                self.after(0, self.quit)

        thread = threading.Thread(target=_run)
        thread.start()
        self.mainloop()
        thread.join()
        # raise exception catched in the thread
        if exceptions:
            raise exceptions[0]

    def set_infos(self, infos: list[Info]) -> None:
        ok = self._infos.set(infos)
        self._logo.set_pulse(ok=ok)

    @staticmethod
    def follow(state: WinState) -> None:
        for sticky in _Sticky.instances():
            try:
                sticky.follow(state)
            except tk.TclError as err:  # due to alt-f4
                raise UIError from err  # to be catched

    @staticmethod
    def stop_following() -> None:
        for sticky in _Sticky.instances():
            try:
                sticky.stop_following()
            except tk.TclError:  # due to alt-f4
                pass

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._app_name, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._app_name}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._app_name, message=message)
