import platform
import sys
import tkinter as tk
from typing import Callable, NamedTuple, Optional, Sequence

from .fx import _Fade
from .sticky import _Offset, _StickyWindow
from .style import _Style
from .widgets import _Border, _Button, _get_border, _ListView, _set_vscrollbar_style


class AppInfo(NamedTuple):
    name: str
    version: str
    app_64bit: bool = sys.maxsize == (2**63) - 1
    os_64bit: bool = platform.machine().endswith("64")

    @property
    def bitness(self) -> str:
        return "x64" if self.os_64bit else "x86"


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str

    @property
    def is_valid(self) -> bool:
        return bool(self.proxy)


class _InfoTheme:
    pad = 2
    bg_headers = "#242424"
    bg_rows = "#2A2A2A"
    separator = "#303030"
    border = _Border(bg="#808080", size=1, relief="")
    button = dict(bg="#1F1E1D", mouseover="#3F3F41", border=_Border(bg="white", size=0.75, relief="groove"))
    listview = dict(bg_headers=bg_headers, bg_rows=bg_rows, bg_separator=separator)
    listview_scrollbar = dict(bg=bg_rows, slider="white", active_slider="grey")


class _InfoStyle:
    stl = _Style().font("Calibri").font_size(12).max_width(30)
    arrow = stl("➜").color("#555555").bigger(5)
    upstream = stl.copy().color("#A0A0A0")
    proxy = stl.copy().white
    name = upstream.copy()
    blank = stl("")
    app_warn = stl.copy().smaller(2).no_truncate
    app = stl.copy().smaller(2)


def _get_infos_headers(app_name: str) -> tuple[_Style, ...]:
    return (
        _InfoStyle.name("User").bigger(2).bold,
        _InfoStyle.blank,
        _InfoStyle.proxy(f"{app_name} Proxy").bigger(2).bold,
        _InfoStyle.blank,
        _InfoStyle.upstream("User Proxy").bigger(2).bold,
    )


def _get_row(info: Info) -> tuple[_Style, ...]:
    return (
        _InfoStyle.name(info.name) if info.name else _InfoStyle.name("-").grey,
        _InfoStyle.arrow if info.name else _InfoStyle.blank,
        _InfoStyle.proxy(info.proxy) if info.proxy else _InfoStyle.stl("No Proxy").red,
        _InfoStyle.arrow if info.upstream else _InfoStyle.blank,
        _InfoStyle.upstream(info.upstream) if info.upstream else _InfoStyle.stl("-").grey,
    )


def _get_button_relaunch() -> _Style:
    return _InfoStyle.stl("Click to relaunch... to fix the proxies").no_truncate.white


def _get_app_info(app_info: AppInfo) -> _Style:
    return _InfoStyle.app(f"{app_info.name} v{app_info.version} {app_info.bitness}").grey


def _get_app_warn(app_info: AppInfo) -> _Style:
    if app_info.app_64bit != app_info.os_64bit:
        warn = f"You should use the {app_info.bitness} version"
        return _InfoStyle.app_warn(warn).red
    warn = "Search your whole catalog"
    return _InfoStyle.app_warn(warn).lime_green


def _are_infos_valid(infos: Sequence[Info]) -> bool:
    return all(info.is_valid for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(-36, 36), maximized=(2, 35))
    _max_height = 300

    def __init__(self, app_info: AppInfo) -> None:
        border = _get_border(_InfoTheme.border)
        super().__init__(_InfosWindow._offset, **border, bg=_InfoTheme.bg_headers)
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        # create a frame for hovering detection
        hover_frame = tk.Frame(self, bg=_InfoTheme.bg_headers)
        hover_frame.pack(fill="both", expand=True)
        self._bind_mouse_hover(hover_frame)
        # create the widgets
        self._create_widgets(hover_frame, _get_app_info(app_info), _get_app_warn(app_info))
        self._listview.set_headers(_get_infos_headers(app_info.name))
        self._fade = _Fade(self)

    def _create_widgets(self, frame: tk.Frame, app_info: _Style, app_warn: _Style) -> None:
        pad = _InfoTheme.pad
        _set_vscrollbar_style(**_InfoTheme.listview_scrollbar)
        # widgets
        self._relaunch_button = _Button(frame, **_InfoTheme.button, **_get_button_relaunch().to_tk)
        self._listview = _ListView(frame, **_InfoTheme.listview, pad=pad)
        app_info_label = tk.Label(frame, bg=_InfoTheme.bg_headers, **app_info.to_tk)
        app_warn_label = tk.Label(frame, bg=_InfoTheme.bg_headers, **app_warn.to_tk)
        separator = tk.Frame(frame, bg=_InfoTheme.separator)
        # layout
        app_info_label.grid(row=0, padx=pad, sticky=tk.W)
        app_warn_label.grid(row=0, column=1, padx=pad, sticky=tk.W)
        self._relaunch_button.grid(row=0, column=2, padx=pad, pady=pad, sticky=tk.EW)
        self._relaunch_button.grid_remove()
        self._listview.grid(row=2, columnspan=3, sticky=tk.NSEW)
        separator.grid(row=1, columnspan=3, sticky=tk.EW)
        frame.columnconfigure(2, weight=1)
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

    def set(self, infos: Sequence[Info], player_relaunch: Optional[Callable[[], None]]) -> bool:
        rows = [_get_row(info) for info in infos]
        if not rows:
            rows = [_get_row(Info("", "-", ""))]
        self._listview.set_rows(rows)
        # add relaunch if not valid
        valid = _are_infos_valid(infos)
        if not valid and player_relaunch:
            self._set_relaunch(player_relaunch)
        else:
            self._relaunch_button.grid_remove()
        # enable resizing
        self.geometry("")
        return valid

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True, wait_ms=100)
