import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, NamedTuple, Self, Sequence

from winapi import set_click_through

# TODO handle always on top
# TODO use sfvip player caption bar color
# TODO scrollbar if to much infos


class _Offset(NamedTuple):
    x: int = 0
    y: int = 0
    centered: bool = False


class Rect(NamedTuple):
    _default = float("inf")
    x: float = _default
    y: float = _default
    w: float = _default
    h: float = _default

    def valid(self) -> bool:
        # pylint: disable=not-an-iterable
        return all(attr != Rect._default for attr in self)

    def position(self, offset: _Offset, w: int, h: int) -> Self:
        if offset.centered:
            return Rect(self.x + (self.w - w) * 0.5, self.y + (self.h - h) * 0.5, w, h)
        return Rect(self.x + offset.x, self.y + offset.y, w, h)

    def to_geometry(self) -> str:
        return f"{self.w}x{self.h}+{self.x:.0f}+{self.y:.0f}"


class _Sticky(tk.Toplevel):
    """follow position, hide & show when needed"""

    _instances = []

    def __init__(self, offset: _Offset, **kwargs) -> None:
        _Sticky._instances.append(self)
        super().__init__(**kwargs)
        self.withdraw()
        self.overrideredirect(True)
        self._offset = offset

    @staticmethod
    def instances() -> list["_Sticky"]:
        return _Sticky._instances

    def follow(self, rect: Rect, is_minimized: bool, no_border: bool) -> None:
        if no_border or is_minimized:
            self.withdraw()
        elif rect.valid():
            rect = rect.position(self._offset, self.winfo_reqwidth(), self.winfo_reqheight())
            self.attributes("-topmost", "true")
            self.geometry(rect.to_geometry())
            self.deiconify()

    def stop_following(self) -> None:
        self.withdraw()


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


def insert_between(iterable: Sequence, delimiter: Any) -> list:
    with_delimiter = ([elt] if i == 0 else [delimiter, elt] for i, elt in enumerate(iterable) if elt)
    return sum(with_delimiter, [])


class _Infos(_Sticky):
    """infos : app + a list to show with arrows in between"""

    _bg = "#242424"
    _offset = _Offset(5, 37)

    _arrow = "➞"
    _border = "grey"
    _font = "Calibri"
    _font_size = 12

    _kw = dict(fg="white", bg=_bg, padx=0, pady=0, font=(_font, _font_size))
    _kw_arrow = _kw | dict(fg="grey", font=(_font, _font_size + 3))
    _kw_title = _kw | dict(font=(_font, _font_size + 1))

    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__(_Infos._offset, bg=_Infos._bg)
        border = dict(highlightbackground=_Infos._border, highlightcolor=_Infos._border, highlightthickness=2)
        self.frame = tk.Frame(self, bg=_Infos._bg, **border)
        self.frame.pack()
        self._fade = _Fade(self)
        self.attributes("-alpha", 0.0)
        self._title = f"{app_name.upper()} v{app_version}"

    def clear(self) -> None:
        for item in self.frame.winfo_children():
            item.destroy()

    def set(self, infos: list[list[str]]) -> None:
        self.clear()
        for row, info in enumerate(infos):
            info = infos[row] = insert_between(info, _Infos._arrow)
            for column, text in enumerate(info):
                kw = _Infos._kw_arrow if column % 2 else _Infos._kw
                tk.Label(self.frame, text=text, **kw).grid(row=row + 1, column=column)
        n_column = len(max(infos, key=len)) if infos else 1
        tk.Label(self.frame, text=self._title, **_Infos._kw_title).grid(row=0, columnspan=n_column)

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True)


class _Logo(_Sticky):
    """logo, mouse hover to show infos"""

    _bg = "black"
    _offset = _Offset(0, 0)

    def __init__(self, logo_path: str, infos: _Infos) -> None:
        super().__init__(_Logo._offset, bg=_Logo._bg)
        self._infos = infos
        logo_file = Path(__file__).parent.parent / logo_path
        self._image = tk.PhotoImage(file=logo_file)  # keep a reference for tkinter
        label = tk.Label(self, bg=_Logo._bg, image=self._image, padx=0, pady=0)
        label.bind("<Enter>", lambda _: self._infos.show())
        label.bind("<Leave>", lambda _: self._infos.hide())
        label.pack()


class _Splash(_Sticky):
    """splash screen"""

    _bg = "black"
    _offset = _Offset(centered=True)

    def __init__(self, image: tk.PhotoImage) -> None:
        super().__init__(_Splash._offset, bg=_Splash._bg)
        tk.Label(self, bg=_Splash._bg, image=image).pack()
        self.attributes("-transparentcolor", _Splash._bg)
        set_click_through(self.winfo_id())
        self._fade = _Fade(self)

    def show(self, rect: Rect) -> None:
        self.follow(rect, False, False)

    def hide(self, fade_duration_ms) -> None:
        self._fade.fade(fade_duration_ms, out=True)

    def stop_following(self) -> None:
        super().stop_following()
        self.attributes("-alpha", 1.0)


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
        self.infos = _Infos(app_name, app_version)
        self._logo = _Logo(logo_path, self.infos)

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

    @staticmethod
    def follow(rect: Rect, is_minimized: bool, no_border: bool) -> None:
        for sticky in _Sticky.instances():
            sticky.follow(rect, is_minimized, no_border)

    @staticmethod
    def stop_following() -> None:
        for sticky in _Sticky.instances():
            sticky.stop_following()

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._app_name, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._app_name}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._app_name, message=message)
