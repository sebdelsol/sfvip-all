import tkinter as tk


class _AutoScrollbar(tk.Scrollbar):
    def set(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(first, last)


class _VAutoScrollableCanvas(tk.Canvas):  # pylint: disable=too-many-ancestors
    """
    Canvas with an automatic vertical scrollbar
    use _VAutoScrollableCanvas.frame to populate it
    """

    def __init__(self, master, **kwargs) -> None:
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

    def _on_configure(self, _):
        w, h = self.frame.winfo_reqwidth(), self.frame.winfo_reqheight()
        self.config(scrollregion=(0, 0, w, h), width=w, height=h)

    def _on_mousewheel(self, event):
        self.yview_scroll(int(-1 * (event.delta / 12)), "units")


class _Button(tk.Button):
    """
    button with a colored border
    with a mouseover color
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self, master, bg: str, mouseover: str, bd_color: str, bd_width: float, bd_relief: str, **kwargs
    ) -> None:
        # create a frame for the border
        border = dict(highlightbackground=bd_color, highlightcolor=bd_color, bd=bd_width, relief=bd_relief)
        self._frame = tk.Frame(master, bg=bg, **border)
        active = dict(activebackground=bg, activeforeground=kwargs.get("fg", "white"))
        super().__init__(self._frame, bg=bg, bd=0, **active, **kwargs)
        self.pack(fill="both", expand=True)
        # handle mouseover
        self.bind("<Enter>", lambda _: self.config(bg=mouseover))
        self.bind("<Leave>", lambda _: self.config(bg=bg))

    def grid(self, **kwargs) -> None:
        self._frame.grid(**kwargs)
