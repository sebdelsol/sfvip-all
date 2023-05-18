import time
import tkinter as tk
from collections import namedtuple
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Self


class Rect(namedtuple("rect", "x y w h", defaults=[None] * 4)):
    def valid(self) -> bool:
        return all(attr is not None for attr in self)

    @classmethod
    def from_dict_keys(cls: type[Self], dct: dict, *keys: str) -> Self:
        assert len(keys) == 4
        return cls(*(dct.get(attr) for attr in keys))

    def keep_in(self, rect: Self) -> Self:
        return Rect(
            max(self.x, rect.x),
            max(self.y, rect.y),
            min(self.x + self.w, rect.w) - self.x,
            min(self.y + self.h, rect.h) - self.y,
        )

    def center_for(self, w: int, h: int) -> Self:
        return Rect(self.x + (self.w - w) * 0.5, self.y + (self.h - h) * 0.5, w, h)


class UI:
    """tk without a mainloop"""

    class Splash:
        _fade_dt = 0.025
        _bg = "black"

        def __init__(self, root: tk.Tk, splash_path: str) -> None:
            file = Path(__file__).parent.parent / splash_path
            self._image = tk.PhotoImage(file=file)  # keep a reference for tk
            self._root = root

        def show(self, rect: Rect) -> None:
            """show in the middle of rect"""
            if rect.valid():
                screen = Rect(0, 0, self._root.winfo_screenwidth(), self._root.winfo_screenheight())
                rect = rect.keep_in(screen)
                rect = rect.center_for(self._image.width(), self._image.height())
                self._root.geometry(f"{rect.w}x{rect.h}+{rect.x:.0f}+{rect.y:.0f}")
            else:
                self._root.eval("tk::PlaceWindow . Center")
            tk.Label(self._root, bg=UI.Splash._bg, image=self._image).pack()
            self._root.attributes("-transparentcolor", UI.Splash._bg, "-topmost", True)
            self._root.attributes("-alpha", 1.0)
            self._root.overrideredirect(True)
            self._root.deiconify()
            self._root.update()

        def hide(self, fade_duration: float = 0.5) -> None:
            """BLOCKING fade out, use when everything else is done"""
            if fade_duration > 0:
                dalpha = UI.Splash._fade_dt / fade_duration
                while (alpha := self._root.attributes("-alpha") - dalpha) > 0:
                    self._root.attributes("-alpha", alpha)
                    time.sleep(UI.Splash._fade_dt)
            self._root.withdraw()

    def __init__(self, title: str, splash_path) -> None:
        root = tk.Tk()
        root.withdraw()
        self.splash = UI.Splash(root, splash_path)
        root.wm_iconphoto(True, self.splash._image)
        self._title = title

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._title, message=message)

    def find_file(self, name: str, pattern: str) -> None:
        title = f"{self._title}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> None:
        return messagebox.askretrycancel(self._title, message=message)
