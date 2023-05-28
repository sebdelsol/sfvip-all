import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, NamedTuple, Self


class Rect(NamedTuple):
    _default = float("inf")
    x: float = _default
    y: float = _default
    w: float = _default
    h: float = _default
    maximized: bool = False

    def valid(self) -> bool:
        # pylint: disable=not-an-iterable
        return all(attr != Rect._default for attr in self)

    def kept_in(self, rect: Self) -> Self:
        return Rect(
            max(self.x, rect.x),
            max(self.y, rect.y),
            min(self.x + self.w, rect.w) - self.x,
            min(self.y + self.h, rect.h) - self.y,
        )

    def centered_for(self, w: int, h: int) -> Self:
        return Rect(self.x + (self.w - w) * 0.5, self.y + (self.h - h) * 0.5, w, h)

    def to_geometry(self) -> str:
        return f"{self.w}x{self.h}+{self.x:.0f}+{self.y:.0f}"


class UI(tk.Tk):
    """basic UI with a tk mainloop, the app has to run in a thread"""

    def __init__(self, app_name: str, splash_path: str) -> None:
        super().__init__()
        self.withdraw()
        file = Path(__file__).parent.parent / splash_path
        image = tk.PhotoImage(file=file)
        self._image = image  # keep a reference for tk
        self.wm_iconphoto(True, image)
        self.app_name = app_name

        class Splash:
            """use tk root as a splash screen"""

            _fade_dt_ms: int = 25
            _bg = "black"

            @staticmethod
            def show(rect: Rect) -> None:
                """show in the middle of rect"""
                if rect.valid() and not rect.maximized:
                    screen = Rect(0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
                    rect = rect.kept_in(screen).centered_for(image.width(), image.height())
                    self.geometry(rect.to_geometry())
                else:
                    self.after(0, self.eval, "tk::PlaceWindow . Center")
                tk.Label(self, bg=Splash._bg, image=image).pack()
                self.attributes("-transparentcolor", Splash._bg, "-topmost", True, "-alpha", 1.0)
                self.overrideredirect(True)
                self.deiconify()

            @staticmethod
            def hide(fade_duration_ms: int = 500):
                """fade out and withdraw"""
                dalpha = Splash._fade_dt_ms / fade_duration_ms if fade_duration_ms > 0 else 1.0

                def fade() -> None:
                    if (alpha := self.attributes("-alpha") - dalpha) > 0:
                        self.attributes("-alpha", alpha)
                        self.after(Splash._fade_dt_ms, fade)
                    else:
                        self.withdraw()

                fade()

        self.splash = Splash

    def run_in_thread(self, target: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        """
        run the target function in a thread,
        handle the mainloop and quit ui when done
        """

        def _run():
            try:
                target(*args, **kwargs)
            finally:
                self.after(0, self.quit)

        thread = threading.Thread(target=_run)
        thread.start()
        self.mainloop()
        thread.join()

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self.app_name, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self.app_name}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self.app_name, message=message)
