import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, NamedTuple, Optional

from winapi import set_click_through

from .fx import _Fade, _Pulse
from .sticky import Rect, WinState, _Offset, _StickyWindow
from .style import _Style
from .widget import _Button, _ListView, _set_border, _set_vscrollbar_style


class TH:
    bg = "#242424"
    bg2 = "#2A2A2A"
    separator = "#303030"


class InfoTH:
    pad = 5
    bg = TH.bg
    border = dict(bg="#808080", size=1)
    button = dict(bg="#1F1E1D", mouseover="#3F3F41", bd_color="white", bd_size=0.75, bd_relief="groove")

    class Listview:
        colors = dict(bg_headers=TH.bg, bg_row=TH.bg2, bg_separator=TH.separator)
        scrollbar = dict(bg=TH.bg2, slider="white", active_slider="grey")


class StlInfo:
    stl = _Style().font("Calibri").font_size(12).max_width(40)
    arrow = stl("➞").color("#707070").bigger(5)
    upstream = stl.color("#A0A0A0")
    proxy = stl.white
    name = upstream
    blank = stl("")


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str


def _get_infos_headers(app_name: str) -> tuple[_Style, ...]:
    return (
        StlInfo.name("User Name").bigger(2).bold,
        StlInfo.blank,
        StlInfo.proxy(f"{app_name} Proxy").bigger(2).bold,
        StlInfo.blank,
        StlInfo.upstream("User Proxy").bigger(2).bold,
    )


def _get_row(info: Info) -> tuple[_Style, ...]:
    return (
        StlInfo.name(info.name),
        StlInfo.arrow,
        StlInfo.proxy(info.proxy) if info.proxy else StlInfo.stl("No Proxy").red,
        StlInfo.arrow if info.upstream else StlInfo.blank,
        StlInfo.upstream(info.upstream) if info.upstream else StlInfo.stl("-").grey,
    )


def _get_button_relaunch() -> _Style:
    return StlInfo.stl("Click to relaunch... and fix the proxies").white


def _get_version(app_name: str, app_version: str) -> _Style:
    return StlInfo.stl(f"{app_name} v{app_version}").smaller(2).grey


def is_valid(info: Info) -> bool:
    return bool(info.proxy)


def _are_infos_valid(infos: list[Info]) -> bool:
    return all(is_valid(info) for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _max_height = 300

    def __init__(self, app_name: str, app_version: str) -> None:
        border = _set_border(**InfoTH.border)  # type:ignore
        super().__init__(_InfosWindow._offset, **border, bg=InfoTH.bg)
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        # create a frame for hovering detection
        hover_frame = tk.Frame(self, bg=InfoTH.bg)
        hover_frame.pack(fill="both", expand=True)
        self._bind_mouse_hover(hover_frame)
        # create the widgets
        self._create_widgets(hover_frame, app_name, app_version)
        self._headers = _get_infos_headers(app_name)
        self._fade = _Fade(self)

    def _create_widgets(self, frame: tk.Frame, app_name: str, app_version: str) -> None:
        pad = InfoTH.pad
        _set_vscrollbar_style(**InfoTH.Listview.scrollbar)
        self._relaunch_button = _Button(frame, **InfoTH.button, **_get_button_relaunch().to_tk)
        version = tk.Label(frame, bg=InfoTH.bg, **_get_version(app_name, app_version).to_tk)
        self._listview = _ListView(frame, **InfoTH.Listview.colors, pad=pad)
        separator = tk.Frame(frame, bg=TH.separator)
        # layout
        version.grid(row=0, padx=pad, sticky=tk.W)
        self._relaunch_button.grid(row=0, column=1, padx=pad, pady=pad, sticky=tk.EW)
        self._relaunch_button.grid_remove()
        frame.columnconfigure(1, weight=1)
        separator.grid(row=1, columnspan=2, sticky=tk.EW)
        self._listview.grid(row=2, columnspan=2, sticky=tk.NSEW)
        frame.rowconfigure(2, weight=1)

    def _set_relaunch(self, player_relaunch: Callable[[], None]) -> None:
        def relaunch(_) -> None:
            self._relaunch_button.unbind("<Button-1>")
            self._relaunch_button.grid_remove()
            # give time for the button feedback and ask for instant relaunch
            self.after(100, player_relaunch, 0)

        self._relaunch_button.grid()
        self._relaunch_button.bind("<Button-1>", relaunch)

    def _bind_mouse_hover(self, widget: tk.Widget) -> None:
        def show(_) -> None:
            """keep showing only when already there to avoid showing again when fading out"""
            if self.attributes("-alpha") == 1.0:
                self.show()

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", lambda _: self.hide(), add="+")

    def set(self, infos: list[Info], player_relaunch: Optional[Callable[[], None]]) -> bool:
        self._listview.set(self._headers, [_get_row(info) for info in infos])
        valid = _are_infos_valid(infos)
        if not valid and player_relaunch:
            self._set_relaunch(player_relaunch)
        self.geometry("")  # enable resizing
        return valid

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True, wait_ms=100)


class _LogoWindow(_StickyWindow):
    """logo, mouse hover to show infos"""

    _pulse_warn = _Pulse.Args(TH.bg, "#990000", frequency=1)
    _pulse_ok = _Pulse.Args(TH.bg, "#006000", frequency=0.33)
    _offset = _Offset(regular=(2, 2), maximized=(0, 0))

    def __init__(self, logo_path: Path, infos: _InfosWindow) -> None:
        super().__init__(_LogoWindow._offset, takefocus=0)
        self._infos = infos
        self._image = tk.PhotoImage(file=logo_path)  # keep a reference for tkinter
        logo = tk.Label(self, bg=_LogoWindow._pulse_ok.color1, image=self._image, takefocus=0)
        logo.pack()
        self.bind("<Enter>", lambda _: self._infos.show())
        self.bind("<Leave>", lambda _: self._infos.hide())
        self._pulse = _Pulse(logo)
        self.set_pulse(ok=True)

    def set_pulse(self, ok: bool) -> None:
        self._pulse.set(*(_LogoWindow._pulse_ok if ok else _LogoWindow._pulse_warn))

    def start_following(self) -> None:
        super().start_following()
        self._pulse.start()

    def stop_following(self) -> None:
        super().stop_following()
        self._pulse.stop()


class _SplashWindow(_StickyWindow):
    """splash screen"""

    _bg = "black"  # color for set_click_through
    _offset = _Offset(centered=True)

    def __init__(self, image: tk.PhotoImage) -> None:
        super().__init__(_SplashWindow._offset, bg=_SplashWindow._bg)
        tk.Label(self, bg=_SplashWindow._bg, image=image).pack()
        self.attributes("-transparentcolor", _SplashWindow._bg)
        set_click_through(self.winfo_id())
        self._fade = _Fade(self)

    def show(self, rect: Rect) -> None:
        self.follow(WinState(rect, False, False, False, True))
        self.attributes("-alpha", 1.0)
        self.deiconify()

    def hide(self, fade_duration_ms, wait_ms=0) -> None:
        self._fade.fade(fade_duration_ms, out=True, wait_ms=wait_ms)


class UI(tk.Tk):
    """basic UI with a tk mainloop, the app has to run in a thread"""

    def __init__(self, app_name: str, app_version: str, splash_path: Path, logo_path: Path) -> None:
        super().__init__()
        self.withdraw()  # we rely on some _StickyWindow instead
        self._splash_img = tk.PhotoImage(file=splash_path)  # keep a reference for tk
        self.wm_iconphoto(True, self._splash_img)
        self.splash = _SplashWindow(self._splash_img)
        self._infos = _InfosWindow(app_name, app_version)
        self._logo = _LogoWindow(logo_path, self._infos)
        self._app_name = app_name

    def run_in_thread(
        self, catch_exception: type[Exception], target: Callable[..., None], *args: Any, **kwargs: Any
    ) -> None:
        """
        run the target function in a thread,
        handle the mainloop and quit ui when done
        catch_exception is re-raised in the main thread
        """

        exception: Optional[Exception] = None

        def _run():
            nonlocal exception
            try:
                target(*args, **kwargs)
            except catch_exception as err:
                exception = err
            finally:
                self.after(0, self.quit)

        thread = threading.Thread(target=_run)
        thread.start()
        self.mainloop()
        thread.join()
        # raise exception catched in the thread
        if exception is not None:
            raise exception  # type:ignore

    def set_infos(self, infos: list[Info], player_relaunch: Optional[Callable[[], None]]) -> None:
        ok = self._infos.set(infos, player_relaunch)
        self._logo.set_pulse(ok=ok)

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._app_name, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._app_name}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._app_name, message=message)
