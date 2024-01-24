import tkinter as tk
from math import cos, pi, sin
from tkinter import ttk
from typing import Any, Callable, Collection, Iterator, NamedTuple, Optional, Sequence

from .style import Style


# pylint: disable=too-many-ancestors
class HorizontalScale(ttk.Scale):
    _count = 0

    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        master: tk.BaseWidget,
        from_: int,
        to: int,
        bg: str,
        trough_color: str,
        trough_height: int,
        slider_width: int,
        slider_height: int,
        slider_color: str,
        slider_color_active: str,
        length: int,
    ) -> None:
        scale_name = f"custom{HorizontalScale._count}.Horizontal.TScale"
        slider_name = f"custom{HorizontalScale._count}.Horizontal.Scale.slider"
        through_name = f"custom{HorizontalScale._count}.Horizontal.Scale.trough"
        HorizontalScale._count += 1
        style = ttk.Style()
        # need to keep references of tk.PhotoImage
        self.through = tk.PhotoImage("through", width=1, height=slider_height, master=master)
        self.slider = tk.PhotoImage("slider", width=slider_width, height=slider_height, master=master)
        self.slider_active = tk.PhotoImage("slider2", width=slider_width, height=slider_height, master=master)
        self.set_img_color_middle(self.through, bg, trough_color, trough_height)
        self.set_img_color(self.slider, slider_color)
        self.set_img_color(self.slider_active, slider_color_active)
        style.element_create(slider_name, "image", self.slider, ("active", self.slider_active))
        style.element_create(through_name, "image", self.through)
        style.layout(
            scale_name,
            [
                (
                    through_name,
                    {
                        "sticky": "nswe",
                        "children": [(slider_name, {"side": "left", "sticky": ""})],
                    },
                )
            ],
        )
        super().__init__(master, from_=from_, to=to, style=scale_name, length=length)

    @staticmethod
    def set_img_color(img: tk.PhotoImage, color: str) -> None:
        img.put(color, to=(0, 0, img.width(), img.height()))  # type: ignore

    def set_img_color_middle(self, img: tk.PhotoImage, color: str, color2: str, height: int) -> None:
        self.set_img_color(img, color)
        middle = int(round((img.height() - height) / 2))
        img.put(color2, to=(0, middle, img.width(), middle + height))  # type: ignore


class Border(NamedTuple):
    bg: str
    size: float
    relief: str


def get_border(border: Border, **kwargs: Any) -> dict[str, Any]:
    return dict(highlightbackground=border.bg, highlightthickness=border.size, highlightcolor=border.bg, **kwargs)


class ScrollBar(NamedTuple):
    bg: str
    slider: str
    active_slider: str
    thickness: int


class _AutoScrollbar(ttk.Scrollbar):
    def set(self, first: float | str, last: float | str) -> None:
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(first, last)


class _VscrollCanvas(tk.Canvas):
    _count = 0

    """
    Canvas with an automatic vertical scrollbar
    use _VAutoScrollableCanvas.frame to populate it
    """

    def __init__(self, master: tk.BaseWidget, scrollbar: ScrollBar, **kwargs: Any) -> None:
        super().__init__(master, bd=0, highlightthickness=0, **kwargs)  # w/o border
        # set the vertical scrollbar
        style = self.set_scrollbar_style(scrollbar)
        vscrollbar = _AutoScrollbar(master, orient="vertical", style=style)
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
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_configure(self, _) -> None:
        self.frame.update_idletasks()
        w, h = self.frame.winfo_reqwidth(), self.frame.winfo_reqheight()
        self.config(scrollregion=(0, 0, w, h), width=w, height=h)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.yview_scroll(int(-1 * (event.delta / 12)), "units")

    @staticmethod
    def set_scrollbar_style(scrollbar: ScrollBar) -> str:
        """flat, no arrow, bg=color of slider"""

        style_name = f"custom{_VscrollCanvas._count}.Vertical.TScrollbar"
        _VscrollCanvas._count += 1
        style = ttk.Style()
        style.layout(
            style_name,
            [
                (
                    "Vertical.Scrollbar.trough",
                    {
                        "children": [
                            (
                                "Vertical.Scrollbar.thumb",
                                {"expand": "1", "sticky": "nswe"},
                            )
                        ],
                        "sticky": "ns",
                    },
                )
            ],
        )
        style.configure(
            style_name,
            background=scrollbar.slider,
            gripcount=0,
            bordercolor=scrollbar.bg,
            troughcolor=scrollbar.bg,
            relief="flat",
            lightcolor=scrollbar.bg,
            darkcolor=scrollbar.bg,
            arrowsize=scrollbar.thickness,
        )
        style.map(style_name, background=[("active", scrollbar.active_slider)])
        return style_name


class ListView(tk.Frame):
    """
    List view with styled content and auto scroll
    Note: set_headers should be called before set_rows
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        bg_headers: str,
        bg_rows: str,
        bg_separator: str,
        scrollbar: ScrollBar,
        pad: int,
    ) -> None:
        super().__init__(master)
        # headers
        self._frame_headers = tk.Frame(self, bg=bg_headers)
        self._frame_headers.pack(fill=tk.BOTH, expand=True)
        # headers separator
        sep = tk.Frame(self, bg=bg_separator)
        sep.pack(fill=tk.BOTH, expand=True)
        # rows
        frame_rows = tk.Frame(self)
        canvas = _VscrollCanvas(frame_rows, scrollbar, bg=bg_rows)
        self._frame_rows = canvas.frame
        frame_rows.pack(fill=tk.BOTH, expand=True)
        # for use later
        self._bg_headers = bg_headers
        self._bg_rows = bg_rows
        self._bg_separator = bg_separator
        self._pad = pad
        self._widths = []

    @staticmethod
    def _clear(what: tk.BaseWidget) -> None:
        for widget in what.winfo_children():
            widget.destroy()

    def set_headers(self, headers: Collection[Style]) -> None:
        self._clear(self._frame_headers)
        pad = self._pad
        n_column = len(headers)
        self._widths = [0] * n_column
        for column, text in enumerate(headers):
            label = tk.Label(self._frame_headers, bg=self._bg_headers, **text.to_tk)
            label.grid(row=0, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
            self._widths[column] = max(label.winfo_reqwidth() + pad * 2, self._widths[column])
        self.set_column_widths()

    def set_rows(self, rows: Sequence[Collection[Style]]) -> None:
        self._clear(self._frame_rows)
        pad = self._pad
        n_column = len(self._widths)
        for row, row_content in enumerate(rows):
            assert len(row_content) == n_column
            for column, text in enumerate(row_content):
                label = tk.Label(self._frame_rows, bg=self._bg_rows, **text.to_tk)
                label.grid(row=row * 2, column=column, ipadx=pad, ipady=pad, sticky=tk.NSEW)
                self._widths[column] = max(label.winfo_reqwidth() + pad * 2, self._widths[column])
                # row separator
                if row != len(rows) - 1:
                    sep = tk.Frame(self._frame_rows, bg=self._bg_separator)
                    sep.grid(row=row * 2 + 1, column=0, columnspan=n_column, sticky=tk.EW)
        if not rows:
            self._frame_rows.config(height=1)
        self.set_column_widths()

    def set_column_widths(self) -> None:
        for column, width in enumerate(self._widths):
            self._frame_headers.columnconfigure(column, minsize=width)
            self._frame_rows.columnconfigure(column, minsize=width)


class Button(tk.Button):
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
        border: Optional[Border] = None,
        attached_to: Optional[tk.Frame] = None,
        **kwargs: Any,
    ) -> None:
        # create a frame for the border, note: do not pack
        self._frame = tk.Frame(master, bg=bg, **(get_border(border) if border else {}))
        self._attached_to = attached_to if attached_to else self._frame
        active = dict(activebackground=bg, activeforeground=kwargs.get("fg", "white"))
        # create the button
        super().__init__(self._frame, bg=bg, bd=0, **active, **kwargs)
        super().pack(fill=tk.BOTH, expand=True)
        # handle mouseover
        self.bind("<Enter>", lambda _: self.config(bg=mouseover), add="+")
        self.bind("<Leave>", lambda _: self.config(bg=bg), add="+")

    def grid(self, **kwargs: Any) -> None:
        self._frame.grid(**kwargs)
        if self._attached_to:
            self._attached_to.grid()

    def grid_remove(self) -> None:
        self._frame.grid_remove()
        if self._attached_to:
            self._attached_to.grid_remove()

    def pack(self, **kwargs: Any) -> None:
        self._frame.pack(**kwargs)
        if self._attached_to:
            self._attached_to.pack()


class CheckBox(ttk.Checkbutton):
    _count = 0

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        bg: str,
        box_color: str,
        indicator_colors: tuple[str, str],
        size: tuple[int, int],
        **kwargs: Any,
    ) -> None:
        self._checked = tk.BooleanVar()
        self._changed_callback = None
        self._get_text = None
        style = ttk.Style()
        self.style_name = f"custom{CheckBox._count}.TCheckbutton"
        tickbox_name = f"custom{CheckBox._count}.tickbox"
        CheckBox._count += 1
        style.configure(
            self.style_name,
            indicatorrelief=tk.FLAT,
            borderwidth=0,
            background=bg,
            foreground=kwargs["fg"],
            font=kwargs["font"],
        )
        w, h = size
        y = max(0, int(kwargs["font"].split()[1]) - size[1])  # vertical alignement
        self.box = tk.PhotoImage("box", width=w, height=h + y, master=master)
        self.box_selected = tk.PhotoImage("box_selected", width=w, height=h + y, master=master)
        self.set_img_color(self.box, y, box_color, indicator_colors[0], False)
        self.set_img_color(self.box_selected, y, box_color, indicator_colors[1], True)
        style.element_create(tickbox_name, "image", self.box, ("selected", self.box_selected))
        style.layout(
            self.style_name,
            [
                (
                    "Checkbutton.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            (tickbox_name, {"side": "left", "sticky": ""}),
                            (
                                "Checkbutton.padding",
                                {
                                    "side": "left",
                                    "sticky": "w",
                                    "children": [("Checkbutton.label", {"sticky": "nswe"})],
                                },
                            ),
                        ],
                    },
                )
            ],
        )
        style.map(self.style_name, background=[("active", bg)])
        super().__init__(
            master,
            variable=self._checked,
            command=self._on_check_changed,
            takefocus=False,
            style=self.style_name,
            text=kwargs["text"],
            padding=(5, 0),
        )

    @staticmethod
    def set_img_color(img: tk.PhotoImage, y: int, fill_color: str, select_color: str, on: bool) -> None:
        w, h = img.width(), img.height()
        img.put(fill_color, to=(0, y, w, h))  # type: ignore
        to = (w - h + y + 1, y + 1, w - 1, h - 1) if on else (1, y + 1, h - y - 1, h - 1)
        img.put(select_color, to=to)  # type: ignore

    def _on_check_changed(self) -> None:
        is_checked = self._checked.get()
        style = ttk.Style()
        if self._get_text:
            text = self._get_text(is_checked).to_tk
            style.configure(
                self.style_name,
                foreground=text["fg"],
                font=text["font"],
            )
            self.config(text=text["text"])
        if self._changed_callback:
            self._changed_callback(is_checked)

    def set_callback(
        self, is_checked: bool, callback: Callable[[bool], None], get_text: Callable[[bool], Style]
    ) -> None:
        self._get_text = get_text
        self._changed_callback = callback
        self._checked.set(is_checked)
        self._on_check_changed()


GetWidgetT = Callable[[tk.Widget], tk.Widget]


# pylint: disable=too-many-ancestors
class RoundedBox(tk.Canvas):
    _rounded_box_tag = "canvas"
    minimum_steps = 10  # lower values give pixelated corners

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        radius: int,
        box_color: str,
        get_widget: GetWidgetT,
        max_height: Optional[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, bd=0, highlightthickness=0, **kwargs)
        self.radius = radius
        self.box_color = box_color
        self.max_height = max_height
        self.widget = get_widget(self)
        self.cos_sin_r = tuple(self.get_cos_sin())
        self.create_window(radius, radius, window=self.widget, anchor=tk.NW)

    # https://gist.github.com/honix/6433bcd40131f42f9502?permalink_comment_id=4832448#gistcomment-4832448
    def get_cos_sin(self) -> Iterator[tuple[float, float]]:
        radius, res = self.radius, max(RoundedBox.minimum_steps, self.radius)
        for i in range(0, res + 1):
            angle = pi * (i / res) * 0.5
            yield (cos(angle) - 1) * radius, (sin(angle) - 1) * radius

    # pylint: disable=too-many-arguments
    def create_rounded_box(self, x0: int, y0: int, x1: int, y1: int, color: str = "black") -> None:
        points = []
        for cos_r, sin_r in self.cos_sin_r:
            points.append((x1 + sin_r, y0 - cos_r))
        for cos_r, sin_r in self.cos_sin_r:
            points.append((x1 + cos_r, y1 + sin_r))
        for cos_r, sin_r in self.cos_sin_r:
            points.append((x0 - sin_r, y1 + cos_r))
        for cos_r, sin_r in self.cos_sin_r:
            points.append((x0 - cos_r, y0 - sin_r))
        self.delete(self._rounded_box_tag)
        self.create_polygon(points, fill=color, tags=self._rounded_box_tag)

    def update_widget(self) -> None:
        self.widget.update_idletasks()
        w, h = self.widget.winfo_reqwidth(), self.widget.winfo_reqheight()
        box_h = min(h, self.max_height) if self.max_height else h
        w_box, h_box = w + 2 * self.radius, box_h + 2 * self.radius
        self.create_rounded_box(0, 0, w_box, h_box, color=self.box_color)
        self.config(width=w_box, height=h_box)
        self.update_idletasks()


class RoundedBoxScroll(RoundedBox):
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        master: tk.BaseWidget,
        radius: int,
        box_color: str,
        get_widget: GetWidgetT,
        get_scrolling_widget: GetWidgetT,
        max_height: Optional[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, radius, box_color, get_widget, max_height, **kwargs)
        self.scroll = tk.Canvas(self, bg=self.box_color, bd=0, highlightthickness=0)
        self.scrolling_widget = get_scrolling_widget(self.scroll)
        self.scroll.create_window(0, 0, window=self.scrolling_widget, anchor=tk.NW)
        self.scroll_id = self.create_window(0, 0, window=self.scroll, anchor=tk.NW)
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def update_widget(self) -> None:
        self.widget.update_idletasks()
        w, h = self.widget.winfo_reqwidth(), self.widget.winfo_reqheight()

        self.scrolling_widget.update_idletasks()
        ws, hs = self.scrolling_widget.winfo_reqwidth(), self.scrolling_widget.winfo_reqheight()
        box_h = min(hs, self.max_height) if self.max_height else hs
        w_box, h_box = max(w, ws) + 2 * self.radius, h + box_h + 2 * self.radius

        self.scroll.config(scrollregion=(0, 0, w_box, hs), width=w_box, height=box_h)
        self.moveto(self.scroll_id, self.radius, self.radius + h)

        self.create_rounded_box(0, 0, w_box, h_box, color=self.box_color)
        self.config(width=w_box, height=h_box)
        self.update_idletasks()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.scroll:
            self.scroll.yview_scroll(-1 if event.delta > 0 else 1, "units")


# pylint: disable=too-many-ancestors
class HorizontalProgressBar(ttk.Progressbar):
    _count = 0

    def __init__(self, master: tk.BaseWidget, bg: str, fg: str, height: int, **kwargs: Any) -> None:
        style_name = f"custom{HorizontalProgressBar._count}.Horizontal.TProgressbar"
        bar_name = f"custom{HorizontalProgressBar._count}.Horizontal.Progressbar.pbar"
        HorizontalProgressBar._count += 1
        style = ttk.Style()
        self.pbar = tk.PhotoImage("pbar", width=1, height=height, master=master)  # keep reference
        self.pbar.put(fg, to=(0, 0, self.pbar.width(), self.pbar.height()))  # type: ignore
        style.element_create(bar_name, "image", self.pbar)
        style.layout(
            style_name,
            [
                (
                    "Horizontal.Progressbar.trough",
                    {
                        "sticky": "nswe",
                        "children": [(bar_name, {"side": "left", "sticky": "ns"})],
                    },
                )
            ],
        )
        style.configure(
            style_name,
            troughcolor=bg,
            bordercolor=bg,
            background=fg,
            lightcolor=bg,
            darkcolor=bg,
        )
        super().__init__(master, style=style_name, orient=tk.HORIZONTAL, **kwargs)
