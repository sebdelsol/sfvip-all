import tkinter as tk
from typing import Callable, NamedTuple, Optional

from .fx import _Fade
from .sticky import _Offset, _StickyWindow
from .style import _Style
from .widgets import _Button, _ListView, _set_border, _set_vscrollbar_style


class Info(NamedTuple):
    name: str
    proxy: str
    upstream: str


class _InfoTheme:
    pad = 2
    bg_headers = "#242424"
    bg_rows = "#2A2A2A"
    separator = "#303030"
    border = dict(bg="#808080", size=1)
    button = dict(bg="#1F1E1D", mouseover="#3F3F41", bd_color="white", bd_size=0.75, bd_relief="groove")
    listview = dict(bg_headers=bg_headers, bg_row=bg_rows, bg_separator=separator)
    listview_scrollbar = dict(bg=bg_rows, slider="white", active_slider="grey")


class _InfoStyle:
    stl = _Style().font("Calibri").font_size(12).max_width(30)
    arrow = stl("➞").color("#707070").bigger(5)
    upstream = stl.color("#A0A0A0")
    proxy = stl.white
    name = upstream
    blank = stl("")


def _get_infos_headers(app_name: str) -> tuple[_Style, ...]:
    return (
        _InfoStyle.name("User Name").bigger(2).bold,
        _InfoStyle.blank,
        _InfoStyle.proxy(f"{app_name} Proxy").bigger(2).bold,
        _InfoStyle.blank,
        _InfoStyle.upstream("User Proxy").bigger(2).bold,
    )


def _get_row(info: Info) -> tuple[_Style, ...]:
    return (
        _InfoStyle.name(info.name),
        _InfoStyle.arrow,
        _InfoStyle.proxy(info.proxy) if info.proxy else _InfoStyle.stl("No Proxy").red,
        _InfoStyle.arrow if info.upstream else _InfoStyle.blank,
        _InfoStyle.upstream(info.upstream) if info.upstream else _InfoStyle.stl("-").grey,
    )


def _get_button_relaunch() -> _Style:
    return _InfoStyle.stl("Click to relaunch... to fix the proxies").no_truncate.white


def _get_version(app_name: str, app_version: str) -> _Style:
    return _InfoStyle.stl(f"{app_name} v{app_version}").smaller(2).grey


def is_valid(info: Info) -> bool:
    return bool(info.proxy)


def _are_infos_valid(infos: list[Info]) -> bool:
    return all(is_valid(info) for info in infos)


class _InfosWindow(_StickyWindow):
    """installed proxies infos"""

    _offset = _Offset(regular=(5, 37), maximized=(3, 35))
    _max_height = 300

    def __init__(self, app_name: str, app_version: str) -> None:
        border = _set_border(**_InfoTheme.border)  # type:ignore
        super().__init__(_InfosWindow._offset, **border, bg=_InfoTheme.bg_headers)
        self.attributes("-alpha", 0.0)
        self.maxsize(-1, _InfosWindow._max_height)
        # create a frame for hovering detection
        hover_frame = tk.Frame(self, bg=_InfoTheme.bg_headers)
        hover_frame.pack(fill="both", expand=True)
        self._bind_mouse_hover(hover_frame)
        # create the widgets
        self._create_widgets(hover_frame, _get_version(app_name, app_version))
        self._listview.set_headers(_get_infos_headers(app_name))
        self._fade = _Fade(self)

    def _create_widgets(self, frame: tk.Frame, version_style: _Style) -> None:
        pad = _InfoTheme.pad
        _set_vscrollbar_style(**_InfoTheme.listview_scrollbar)
        # widgets
        self._relaunch_button = _Button(frame, **_InfoTheme.button, **_get_button_relaunch().to_tk)
        self._listview = _ListView(frame, **_InfoTheme.listview, pad=pad)
        version = tk.Label(frame, bg=_InfoTheme.bg_headers, **version_style.to_tk)
        separator = tk.Frame(frame, bg=_InfoTheme.separator)
        # layout
        version.grid(row=0, padx=pad, sticky=tk.W)
        self._relaunch_button.grid(row=0, column=1, padx=pad, pady=pad, sticky=tk.EW)
        self._relaunch_button.grid_remove()
        self._listview.grid(row=2, columnspan=2, sticky=tk.NSEW)
        separator.grid(row=1, columnspan=2, sticky=tk.EW)
        frame.columnconfigure(1, weight=1)
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
        rows = [_get_row(info) for info in infos]
        self._listview.set_rows(rows)
        # add relaunch if not valid
        valid = _are_infos_valid(infos)
        if not valid and player_relaunch:
            self._set_relaunch(player_relaunch)
        # enable resizing
        self.geometry("")
        return valid

    def show(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=False)

    def hide(self) -> None:
        self._fade.fade(fade_duration_ms=250, out=True, wait_ms=100)
