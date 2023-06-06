import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, NamedTuple, Optional

from winapi import set_click_through

from .fx import _Fade, _Pulse
from .sticky import Rect, WinState, _Offset, _StickyWindow
from .style import _Style
from .widget import _Button, _VAutoScrollableCanvas

WIDGET_BG = "#242424"
WIDGET_BG2 = "#2A2A2A"
WIDGET_BD_COLOR = "#333333"
BUTTON_COLOR = "#1F1E1D"
BUTTON_HIGHLIGHT_COLOR = "#3F3F41"

_STL = _Style().font("Calibri").font_size(12)
_ARROW = _STL("➞").color("#707070").bigger(5)
_STL_UPSTREAM = _STL.color("#A0A0A0")
_STL_PROXY = _STL.light_green
_STL_NAME = _STL.white
_MAX_STR_LEN = 30
_BLANK = _STL("")


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str

    def get_info(self) -> tuple[_Style, ...]:
        name = self.name[:_MAX_STR_LEN]
        proxy = self.proxy[:_MAX_STR_LEN]
        upstream = self.upstream[:_MAX_STR_LEN]
        return (
            _STL_NAME(name),  # type: ignore
            _ARROW,
            _STL_PROXY(proxy) if proxy else _STL("No Proxy").red,
            _ARROW if upstream else _STL(""),
            _STL_UPSTREAM(upstream) if upstream else _STL("-").grey,
        )

    def valid(self) -> bool:
        return bool(self.proxy)


def _get_infos_headers(app_name: str, app_version: str) -> tuple[_Style, ...]:
    return (
        _STL_NAME("User Name").bigger(2).bold.italic,  # type: ignore
        _BLANK,
        _STL_PROXY(f"{app_name} v{app_version} Proxy").bigger(3).bold,  # type: ignore
        _BLANK,
        _STL_UPSTREAM("User Proxy").bigger(2).bold.italic,
    )


def _get_button_relaunch() -> _Style:
    return _STL("Click to relaunch Sfvip Player... and fix the proxies").bigger(1).white.bold


def _are_infos_valid(infos: list[Info]) -> bool:
    return all(info.valid() for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _max_height = 300
    _border_size = 2
    _pad = 5

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__(
            _InfosWindow._offset,
            highlightbackground=WIDGET_BD_COLOR,
            highlightthickness=_InfosWindow._border_size,
            highlightcolor=WIDGET_BD_COLOR,
        )
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        canvas = _VAutoScrollableCanvas(self, bg=WIDGET_BG2)
        self._frame = canvas.frame
        self._headers = list(_get_infos_headers(app_name, app_version))
        self._fade = _Fade(self)
        self._bind_mouse_hover(canvas, canvas.scrollbar, canvas.frame)

    def set(self, infos: list[Info], player_relaunch: Optional[Callable[[], None]]) -> bool:
        # clear the frame
        for widget in self._frame.winfo_children():
            widget.destroy()
        # populate
        row = 0
        pad = _InfosWindow._pad
        valid = _are_infos_valid(infos)
        # relaunch button
        if not valid and player_relaunch:
            button = self._set_relaunch(player_relaunch)
            button.grid(columnspan=6, padx=pad, pady=pad, sticky=tk.EW)
            row += 1
        # headers
        for column, text in enumerate(self._headers):
            label = tk.Label(self._frame, bg=WIDGET_BG, **text.to_tk)
            label.grid(row=row, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
        row += 1
        # proxies
        for row_index, info in enumerate(infos):
            for column, text in enumerate(info.get_info()):
                bg = WIDGET_BG if row_index % 2 else WIDGET_BG2
                label = tk.Label(self._frame, bg=bg, **text.to_tk)
                label.grid(row=row + row_index, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
        # enable resizing
        self.geometry("")
        return valid

    def _set_relaunch(self, player_relaunch: Callable[[], None]) -> tk.Button:
        text = _get_button_relaunch()
        border = dict(bd_color="white", bd_width=0.75, bd_relief="groove")
        buttonstyle = dict(bg=BUTTON_COLOR, mouseover=BUTTON_HIGHLIGHT_COLOR)
        button = _Button(self._frame, **buttonstyle, **border, **text.to_tk)

        def relaunch(_) -> None:
            button.unbind("<Button-1>")
            # give time for the button feedback and ask for instant relaunch
            self.after(100, player_relaunch, 0)

        button.bind("<Button-1>", relaunch)
        return button

    def _bind_mouse_hover(self, *widgets: tk.Widget) -> None:
        def show(_):
            """keep showing only when already there to avoid showing again when fading out"""
            if self.attributes("-alpha") == 1.0:
                self.show()

        for widget in widgets:
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", lambda _: self.hide())

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True, wait_ms=100)


class _LogoWindow(_StickyWindow):
    """logo, mouse hover to show infos"""

    _pulse_warn = _Pulse.Args(WIDGET_BG, "#990000", frequency=1)
    _pulse_ok = _Pulse.Args(WIDGET_BG, "#006000", frequency=0.33)
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
