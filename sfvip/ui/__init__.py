import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, NamedTuple, Optional

from winapi import set_click_through

from .fx import _Fade, _Pulse
from .sticky import Rect, WinState, _Offset, _StickyWindow
from .style import _Style
from .widget import _Button, _ListView, _VscrollCanvas


class TH:
    bg = "#2A2A2A"


class InfoTH:
    pad = 5
    bg = TH.bg

    class Listview:
        headers = TH.bg
        rows = "#242424"
        sep = "#303030"

    class Button:
        bg = "#1F1E1D"
        mouseover = "#3F3F41"

    class Border:
        bg = "#808080"
        bd = 1


class StlInfo:
    stl = _Style().font("Calibri").font_size(12)
    arrow = stl("➞").color("#707070").bigger(5)
    upstream = stl.color("#A0A0A0")
    proxy = stl.white
    blank = stl("")
    name = upstream
    max_len = 30


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str


def _get_infos_headers(app_name: str) -> tuple[_Style, ...]:
    return (
        StlInfo.name("User Name").bigger(2).bold,  # type: ignore
        StlInfo.blank,
        StlInfo.proxy(f"{app_name} Proxy").bigger(2).bold,  # type: ignore
        StlInfo.blank,
        StlInfo.proxy("User Proxy").bigger(2).bold,
    )


def get_row(info: Info) -> tuple[_Style, ...]:
    name = info.name[: StlInfo.max_len]
    proxy = info.proxy[: StlInfo.max_len]
    upstream = info.upstream[: StlInfo.max_len]
    return (
        StlInfo.name(name),  # type: ignore
        StlInfo.arrow,
        StlInfo.proxy(proxy) if proxy else StlInfo.stl("No Proxy").red,
        StlInfo.arrow if upstream else StlInfo.stl(""),
        StlInfo.upstream(upstream) if upstream else StlInfo.stl("-").grey,
    )


def _get_button_relaunch() -> _Style:
    return StlInfo.stl("Click to relaunch... and fix the proxies").white


def _get_version(app_name: str, app_version: str) -> _Style:
    return StlInfo.stl(f"{app_name} {app_version}").smaller(2).grey


def is_valid(info: Info) -> bool:
    return bool(info.proxy)


def _are_infos_valid(infos: list[Info]) -> bool:
    return all(is_valid(info) for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _max_height = 300

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__(
            _InfosWindow._offset,
            highlightbackground=InfoTH.Border.bg,
            highlightthickness=InfoTH.Border.bd,
            highlightcolor=InfoTH.Border.bg,
            bg=InfoTH.bg,
        )
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        self._headers = _get_infos_headers(app_name)
        self._fade = _Fade(self)
        # create a frame for a working mouse hovering detection
        hover_frame = tk.Frame(self, bg=InfoTH.bg)
        hover_frame.pack(fill="both", expand=True)
        self._bind_mouse_hover(hover_frame)
        # create the widgets
        self.create_widgets(hover_frame, app_name, app_version)

    def create_widgets(self, frame: tk.Frame, app_name: str, app_version: str) -> None:
        # version
        pad = InfoTH.pad
        text = _get_version(app_name, app_version)
        label = tk.Label(frame, bg=InfoTH.bg, **text.to_tk)
        # relaunch button
        text = _get_button_relaunch()
        border = dict(bd_color="white", bd_width=0.75, bd_relief="groove")
        buttonstyle = dict(bg=InfoTH.Button.bg, mouseover=InfoTH.Button.mouseover)
        relaunch_button = _Button(frame, **buttonstyle, **border, **text.to_tk)
        # separator
        sep = tk.Frame(frame, bg=InfoTH.Listview.sep)
        # list view
        listview = _ListView(frame, InfoTH.Listview.headers, InfoTH.Listview.rows, InfoTH.Listview.sep, pad)
        # layout
        label.grid(row=0, padx=pad, sticky=tk.W)
        relaunch_button.grid(row=0, column=1, padx=pad, pady=pad, sticky=tk.EW)
        relaunch_button.grid_remove()
        frame.columnconfigure(1, weight=1)
        sep.grid(row=1, columnspan=2, sticky=tk.EW)
        listview.grid(row=2, columnspan=2, sticky=tk.NSEW)
        frame.rowconfigure(2, weight=1)
        # for later use
        self._relaunch_button = relaunch_button
        self._listview = listview

    def set(self, infos: list[Info], player_relaunch: Optional[Callable[[], None]]) -> bool:
        self._listview.set(self._headers, [get_row(info) for info in infos])
        valid = _are_infos_valid(infos)
        if not valid and player_relaunch:
            self._set_relaunch(player_relaunch)
        self.geometry("")  # enable resizing
        return valid

    def _set_relaunch(self, player_relaunch: Callable[[], None]) -> None:
        def relaunch(_) -> None:
            self._relaunch_button.unbind("<Button-1>")
            self._relaunch_button.grid_remove()
            # give time for the button feedback and ask for instant relaunch
            self.after(100, player_relaunch, 0)

        self._relaunch_button.grid()
        self._relaunch_button.bind("<Button-1>", relaunch)

    def _bind_mouse_hover(self, widget: tk.Widget) -> None:
        def show(_):
            """keep showing only when already there to avoid showing again when fading out"""
            if self.attributes("-alpha") == 1.0:
                self.show()

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", lambda _: self.hide(), add="+")

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
        label = tk.Label(self, bg=_LogoWindow._pulse_ok.color1, image=self._image, takefocus=0)
        label.pack()
        self.bind("<Enter>", lambda _: self._infos.show())
        self.bind("<Leave>", lambda _: self._infos.hide())
        self._pulse = _Pulse(label)
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
        self._app_name = app_name
        self.splash = _SplashWindow(self._splash_img)
        self._infos = _InfosWindow(app_name, app_version)
        self._logo = _LogoWindow(logo_path, self._infos)

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
