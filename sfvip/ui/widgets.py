import tkinter as tk
from tkinter import ttk
from typing import Any, Collection

from pyparsing import Sequence

from .style import _Style


def _set_vscrollbar_style(bg: str, slider: str, active_slider: str) -> None:
    """flat, no arrow, bg=color of slider"""
    style = ttk.Style()
    style.theme_use("clam")
    style.layout(
        "Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
                    "sticky": "ns",
                },
            )
        ],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=slider,
        gripcount=0,
        bordercolor=bg,
        troughcolor=bg,
        relief="flat",
        lightcolor=bg,
        darkcolor=bg,
    )
    style.map("Vertical.TScrollbar", background=[("active", active_slider)])


def _set_border(bg: str, size: float, **kwargs: str) -> dict[str, Any]:
    return dict(highlightbackground=bg, highlightthickness=size, highlightcolor=bg, **kwargs)


# pylint: disable=too-many-ancestors
class _AutoScrollbar(ttk.Scrollbar):
    def set(self, first, last) -> None:
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(first, last)


class _VscrollCanvas(tk.Canvas):
    """
    Canvas with an automatic vertical scrollbar
    use _VAutoScrollableCanvas.frame to populate it
    """

    def __init__(self, master: tk.BaseWidget, **kwargs) -> None:
        super().__init__(master, bd=0, highlightthickness=0, **kwargs)  # w/o border
        # set the vertical scrollbar
        vscrollbar = _AutoScrollbar(master, orient="vertical")
        self.config(yscrollcommand=vscrollbar.set, yscrollincrement="2")
        vscrollbar.config(command=self.yview)
        self.scrollbar = vscrollbar
        # position everything
        vscrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.grid(row=0, column=0, sticky=tk.NSEW)
        # Making the canvas expandable
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        # creating the frame attached to self
        self.frame = tk.Frame(self, bg=self["bg"])
        self.create_window(0, 0, anchor=tk.NW, window=self.frame)
        # set the scroll region when the frame content changes
        self.frame.bind("<Configure>", self._on_configure)
        # bind the mousewheel
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_configure(self, _) -> None:
        w, h = self.frame.winfo_reqwidth(), self.frame.winfo_reqheight()
        self.config(scrollregion=(0, 0, w, h), width=w, height=h)

    def _on_mousewheel(self, event) -> None:
        self.yview_scroll(int(-1 * (event.delta / 12)), "units")


class _Button(tk.Button):
    """
    button with a colored border
    with a mouseover color
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        bg: str,
        mouseover: str,
        bd_color: str,
        bd_size: float,
        bd_relief: str,
        **kwargs
    ) -> None:
        # create a frame for the border, note: do not pack
        border = _set_border(bg=bd_color, size=bd_size, relief=bd_relief)
        self._frame = tk.Frame(master, bg=bg, **border)
        active = dict(activebackground=bg, activeforeground=kwargs.get("fg", "white"))
        # create the button
        super().__init__(self._frame, bg=bg, bd=0, **active, **kwargs)
        super().pack(fill="both", expand=True)
        # handle mouseover
        self.bind("<Enter>", lambda _: self.config(bg=mouseover), add="+")
        self.bind("<Leave>", lambda _: self.config(bg=bg), add="+")

    def grid(self, **kwargs) -> None:
        self._frame.grid(**kwargs)

    def grid_remove(self) -> None:
        self._frame.grid_remove()

    def pack(self, **kwargs) -> None:
        self._frame.pack(**kwargs)


class _ListView(tk.Frame):
    """
    List view with styled content and auto scroll
    Note: set_headers should be called before set_rows
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        bg_headers: str,
        bg_row: str,
        bg_separator: str,
        pad: int,
    ) -> None:
        super().__init__(master)
        # headers
        self._frame_headers = tk.Frame(self, bg=bg_headers)
        self._frame_headers.pack(fill="both", expand=True)
        # headers separator
        sep = tk.Frame(self, bg=bg_separator)
        sep.pack(fill="both", expand=True)
        # rows
        frame_rows = tk.Frame(self)
        canvas = _VscrollCanvas(frame_rows, bg=bg_separator)
        self._frame_rows = canvas.frame
        frame_rows.pack(fill="both", expand=True)
        # for use later
        self._bg_headers = bg_headers
        self._bg_row = bg_row
        self._bg_separator = bg_separator
        self._pad = pad
        self._widths = []

    @staticmethod
    def _clear(what: tk.BaseWidget) -> None:
        for widget in what.winfo_children():
            widget.destroy()

    def set_headers(self, headers: Collection[_Style]) -> None:
        self._clear(self._frame_headers)
        pad = self._pad
        n_column = len(headers)
        self._widths = [0] * n_column
        for column, text in enumerate(headers):
            label = tk.Label(self._frame_headers, bg=self._bg_headers, **text.to_tk)
            label.grid(row=0, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
            self._widths[column] = max(label.winfo_reqwidth() + pad * 2, self._widths[column])
        self.set_column_widths()

    def set_rows(self, rows: Sequence[Collection[_Style]]) -> None:
        self._clear(self._frame_rows)
        pad = self._pad
        n_column = len(self._widths)
        for row, row_content in enumerate(rows):
            assert len(row_content) == n_column
            for column, text in enumerate(row_content):
                label = tk.Label(self._frame_rows, bg=self._bg_row, **text.to_tk)
                label.grid(row=row * 2, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
                self._widths[column] = max(label.winfo_reqwidth() + pad * 2, self._widths[column])
                # row separator
                if row != len(rows) - 1:
                    sep = tk.Frame(self._frame_rows, bg=self._bg_separator)
                    sep.grid(row=row * 2 + 1, column=0, columnspan=n_column, sticky=tk.EW)
        self.set_column_widths()

    def set_column_widths(self) -> None:
        for column, width in enumerate(self._widths):
            self._frame_headers.columnconfigure(column, minsize=width)
            self._frame_rows.columnconfigure(column, minsize=width)
