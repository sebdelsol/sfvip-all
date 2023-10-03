import logging
import threading
import tkinter as tk
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable, Iterator, Optional, TypeVar

from ..localization import LOC
from .style import _Style
from .thread import ThreadUI
from .widgets import _Border, _Button, _get_border

logger = logging.getLogger(__name__)
Treturn = TypeVar("Treturn")


class _Theme:
    text = _Style().font("Calibri").font_size(10).max_width(30).no_truncate.white
    wait = text.copy().bigger(6)
    bg = "#2A2A2A"
    border = _Border(bg="#808080", size=1, relief="")
    space = 30


def _get_bar_style() -> str:
    bg = "#242424"
    fg = "#1c8cbc"
    bar_style_name = "bar.Horizontal.TProgressbar"
    style = ttk.Style()
    style.configure(bar_style_name, troughcolor=bg, bordercolor=bg, background=fg, lightcolor=fg, darkcolor=fg)
    return bar_style_name


class _Title:
    bg = "#242424"
    quit = _Theme.text("x").bigger(5)
    title = _Theme.text.copy().bigger(10)
    button = dict(bg=bg, mouseover="red")
    pad = 10


class _Ask:
    bg = _Theme.bg
    button = dict(bg="#1F1E1D", border=_Border(bg="#3F3F41", size=0.75, relief="groove"))
    button_pad = 7
    text = _Theme.text.copy().bigger(5)
    space = 20


class _Window(tk.Toplevel):
    _instances: set["_Window"] = set()
    _instances_lock = threading.RLock()
    _has_quit = False
    _image: tk.PhotoImage

    @classmethod
    def set_logo(cls, logo_path: Path) -> None:
        cls._image = tk.PhotoImage(file=logo_path)

    @classmethod
    def quit_all(cls) -> None:
        with cls._instances_lock:
            cls._has_quit = True
            for instance in cls._instances.copy():
                instance.destroy()

    def __init__(self, *args: Any, force: bool = False, **kwargs: Any) -> None:
        with _Window._instances_lock:
            if not _Window._has_quit or force:
                super().__init__(*args, **kwargs)
                _Window._instances.add(self)
                self._destroyed = False

    def destroy(self) -> None:
        with _Window._instances_lock:
            if not self._destroyed:
                _Window._instances.discard(self)
                self._destroyed = True
                super().destroy()

    @property
    def destroyed(self) -> bool:
        return self._destroyed or _Window._has_quit

    def run_in_thread(self, func: Callable[[], Optional[bool]], *exceptions: type[Exception]) -> Optional[bool]:
        try:
            return ThreadUI(self, *exceptions).start(func)
        except exceptions as err:
            logger.warning("%s %s %s", func.__name__, type(err).__name__, err)
        finally:
            self.destroy()
        return False


class _TitleBarWindow(_Window):
    def __init__(self, title: str, width: int, *args: Any, **kwargs: Any) -> None:
        border = _get_border(_Theme.border)
        super().__init__(*args, **border, **kwargs)
        self.minsize(width, -1)
        self.overrideredirect(True)  # turns off title bar, geometry
        self.attributes("-topmost", True)
        self.resizable(False, False)
        title_bar = tk.Frame(self, bg=_Title.bg)
        logo = tk.Label(title_bar, bg=_Title.bg, image=_Window._image)
        title_txt = tk.Label(title_bar, bg=_Title.bg, **_Title.title(title).to_tk)
        close_button = _Button(title_bar, **_Title.button, **_Title.quit.to_tk, command=self.destroy)
        title_bar.pack(expand=True, fill=tk.BOTH)
        logo.grid(row=0, column=0)
        title_txt.grid(row=0, column=1)
        close_button.grid(row=0, column=2)
        title_bar.columnconfigure(1, weight=1)
        self._grip_widgets(logo, title_txt)
        if isinstance(self.master, tk.Tk):
            self.master.eval(f"tk::PlaceWindow {str(self)} center")

    def _grip_widgets(self, *widgets: tk.Widget) -> None:
        def click_window(event: tk.Event) -> None:
            nonlocal click_x, click_y
            click_x, click_y = event.x, event.y

        def move_window(event: tk.Event) -> None:
            self.geometry(f"+{self.winfo_x() + event.x - click_x}+{self.winfo_y() + event.y - click_y}")

        click_x, click_y = 0, 0
        for widget in widgets:
            widget.bind("<Button-1>", click_window)
            widget.bind("<B1-Motion>", move_window)


class MessageWindow(_TitleBarWindow):
    # pylint: disable=too-many-arguments
    def __init__(self, title: str, message: str, width: int = 400, force: bool = False) -> None:
        super().__init__(title=title, width=width, bg=_Theme.bg, force=force)
        label = tk.Label(self, bg=_Ask.bg, **_Ask.text(message).to_tk)
        ok_button = _Button(
            self, **_Ask.button, width=10, mouseover="lime green", **_Ask.text("Ok").to_tk, command=self.destroy
        )
        label.pack(pady=_Ask.space)
        ok_button.pack(padx=_Ask.button_pad, pady=_Ask.button_pad)


class AskWindow(_TitleBarWindow):
    # pylint: disable=too-many-arguments
    def __init__(self, title: str, message: str, ok: str, cancel: str, width: int = 400) -> None:
        super().__init__(title=title, width=width, bg=_Theme.bg)
        self._ok = None
        frame = tk.Frame(self, bg=_Ask.bg)
        label = tk.Label(frame, bg=_Ask.bg, **_Ask.text(message).to_tk)
        width = max(len(ok), len(cancel), 10)
        ok_button = _Button(
            frame, **_Ask.button, width=width, mouseover="lime green", **_Ask.text(ok).to_tk, command=self._on_ok
        )
        cancel_button = _Button(
            frame, **_Ask.button, width=width, mouseover="red", **_Ask.text(cancel).to_tk, command=self._on_cancel
        )
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        label.grid(row=0, columnspan=2, pady=_Ask.space, sticky=tk.EW)
        pad = _Ask.button_pad
        ok_button.grid(row=1, column=0, padx=pad, pady=pad, sticky=tk.E)
        cancel_button.grid(row=1, column=1, padx=pad, pady=pad, sticky=tk.W)

    def _on_ok(self) -> None:
        self._ok = True
        self.destroy()

    def _on_cancel(self) -> None:
        self._ok = False
        self.destroy()

    @property
    def ok(self) -> Optional[bool]:
        return self._ok


class ProgressMode(Enum):
    PERCENT = "determinate"
    UNKNOWN = "indeterminate"


class ProgressWindow(_TitleBarWindow):
    def __init__(self, title: str, width: int = 400) -> None:
        super().__init__(title=title, width=width, bg=_Theme.bg)
        wait = tk.Label(self, bg=_Theme.bg, **_Theme.wait(LOC.PleaseWait).to_tk)
        self._label = tk.Label(self, bg=_Theme.bg, text="")
        self._progressbar = ttk.Progressbar(self, style=_get_bar_style(), orient=tk.HORIZONTAL, length=width)
        self._progress_mode = None
        self._set_progress_mode(ProgressMode.UNKNOWN)
        wait.pack(pady=(_Theme.space / 2, 0))
        self._progressbar.pack(expand=True, fill=tk.BOTH)
        self._label.pack(pady=(0, _Theme.space))

    def msg(self, text: str) -> None:
        self._label.config(**_Theme.text(text).to_tk)

    def _set_progress_mode(self, mode: ProgressMode) -> None:
        if self._progress_mode != mode:
            if mode == ProgressMode.UNKNOWN:
                self._progressbar.start(10)
            else:
                self._progressbar.stop()
            self._progressbar["mode"] = mode.value
            self._progress_mode = mode

    @contextmanager
    def show_percent(self) -> Iterator[Callable[[float], None]]:
        def set_progress(percent: float) -> None:
            self._set_progress_mode(ProgressMode.PERCENT)
            self._progressbar["value"] = max(0, min(percent, 100))

        yield set_progress
        self._set_progress_mode(ProgressMode.UNKNOWN)
