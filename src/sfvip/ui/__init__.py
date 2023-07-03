import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Optional, Sequence

from .infos import AppInfo, Info, _InfosWindow
from .logo import _LogoWindow
from .splash import _SplashWindow
from .sticky import Rect, WinState


class UI(tk.Tk):
    """basic UI with a tk mainloop, the app has to run in a thread"""

    def __init__(self, app_info: AppInfo, splash_path: Path, logo_path: Path) -> None:
        super().__init__()
        self.withdraw()  # we rely on some _StickyWindow instead
        self._splash_img = tk.PhotoImage(file=splash_path)  # keep a reference for tk
        self.wm_iconphoto(True, self._splash_img)
        self.splash = _SplashWindow(self._splash_img)
        self._infos = _InfosWindow(app_info)
        self._logo = _LogoWindow(logo_path, self._infos)
        self._title = f"{app_info.name} v{app_info.version} {app_info.bitness}"

    def run_in_thread(self, target: Callable[..., None], *exceptions: type[Exception]) -> None:
        """
        run the target function in a thread,
        handle the mainloop and quit ui when done
        any exceptions is re-raised in the main thread
        """

        ui = self

        class RaiseCatchedExceptionThread(threading.Thread):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self._catched: Optional[Exception] = None

            def run(self) -> None:
                try:
                    super().run()
                except exceptions as exception:
                    self._catched = exception
                finally:
                    ui.after(0, ui.quit)

            def join(self, timeout: Optional[float] = None) -> None:
                super().join(timeout)
                if self._catched is not None:
                    raise self._catched

        thread = RaiseCatchedExceptionThread(target=target)
        thread.start()
        self.mainloop()
        thread.join()

    def set_infos(self, infos: Sequence[Info], player_relaunch: Optional[Callable[[], None]] = None) -> None:
        ok = self._infos.set(infos, player_relaunch)
        self._logo.set_pulse(ok=ok)

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._title, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._title}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._title, message=message)
