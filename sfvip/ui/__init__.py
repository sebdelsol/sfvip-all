import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Iterator, NamedTuple

from winapi import set_click_through

from .fx import _Fade, _Pulse
from .scrollable import _VAutoScrollableCanvas
from .sticky import Rect, WinState, _Offset, _StickyWindow
from .style import _Style

# TODO better infos headers
# TODO Relaunch button

WIDGET_BG = "#242424"
WIDGET_BORDER_COLOR = "#333333"

_STL = _Style(bg=WIDGET_BG, font="Calibri", font_size=12)
_STL_NAME = _STL.white
_STL_PROXY = _STL.light_green
_STL_UPSTREAM = _STL.color("#A0A0A0")
_ARROW = "➞", _STL.color("#707070").bigger(5)
_MAX_STR_LEN = 30


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str

    def get_info(self) -> Iterator[tuple[str, _Style]]:
        name = self.name[:_MAX_STR_LEN]
        proxy = self.proxy[:_MAX_STR_LEN]
        upstream = self.upstream[:_MAX_STR_LEN]

        yield (name, _STL_NAME) if proxy else (name, _STL_NAME.red.bold)
        yield _ARROW if proxy else ("", _STL)
        yield (proxy, _STL_PROXY) if proxy else ("No Proxy", _STL.red.bold)
        yield _ARROW if upstream else ("", _STL)
        yield (upstream, _STL_UPSTREAM) if upstream else ("", _STL)

    def valid(self) -> bool:
        return bool(self.proxy)


def _get_infos_headers(app_name: str, app_version: str) -> Iterator[tuple[str, _Style]]:
    yield "Account", _STL_NAME.bigger(2).bold
    yield f"{app_name} v{app_version} Proxy", _STL_PROXY.bigger(2).bold
    yield "Account Proxy", _STL_UPSTREAM.bigger(2).bold


def _get_infos_warn() -> tuple[str, _Style]:
    return "Relaunch Sfvip Player to have all proxies working", _STL.bigger(1).red.bold


def _are_infos_valid(infos: list[Info]) -> bool:
    return all(info.valid() for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _max_height = 300
    _border_size = 2
    _padx = 10

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__(
            _InfosWindow._offset,
            bg=WIDGET_BG,
            highlightbackground=WIDGET_BORDER_COLOR,
            highlightthickness=_InfosWindow._border_size,
            highlightcolor=WIDGET_BORDER_COLOR,
        )
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        canvas = _VAutoScrollableCanvas(self, bg=WIDGET_BG)
        self._frame = frame = canvas.frame
        self._headers = list(_get_infos_headers(app_name, app_version))
        self._fade = _Fade(self)
        self._bind_mouse_hover(frame, canvas, canvas.scrollbar)

    def set(self, infos: list[Info]) -> bool:
        # clear the frame
        for widget in self._frame.winfo_children():
            widget.destroy()
        # populate
        row = 0
        padx = _InfosWindow._padx
        if not (valid := _are_infos_valid(infos)):
            text, style = _get_infos_warn()
            tk.Label(self._frame, text=text, **style()).grid(row=0, columnspan=6, padx=padx)
            row = 1
        for column, (text, style) in enumerate(self._headers):
            tk.Label(self._frame, text=text, **style()).grid(row=row, column=column * 2, padx=padx)
        for drow, info in enumerate(infos):
            for column, (text, style) in enumerate(info.get_info()):
                tk.Label(self._frame, text=text, **style()).grid(row=row + drow + 1, column=column, padx=padx)
        # enable resizing
        self.geometry("")
        return valid

    def _bind_mouse_hover(self, *widgets: tk.Widget) -> None:
        def show(_):
            """keep showing only when already there"""
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

    _pulse_warn = _Pulse.Args(WIDGET_BG, "#880000", frequency=0.75)
    _pulse_ok = _Pulse.Args(WIDGET_BG, "#006000", frequency=0.5)
    _offset = _Offset(regular=(2, 2), maximized=(0, 0))

    def __init__(self, logo_path: Path, infos: _InfosWindow) -> None:
        super().__init__(_LogoWindow._offset)
        self._infos = infos
        self._image = tk.PhotoImage(file=logo_path)  # keep a reference for tkinter
        label = tk.Label(self, bg=_LogoWindow._pulse_ok.color1, image=self._image)
        label.bind("<Enter>", lambda _: self._infos.show())
        label.bind("<Leave>", lambda _: self._infos.hide())
        label.pack()
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
        self.withdraw()
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

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._app_name, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._app_name}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._app_name, message=message)
