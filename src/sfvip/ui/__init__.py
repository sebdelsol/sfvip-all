import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional, Sequence

from .infos import AppInfo, Info, _InfosWindow
from .logo import _LogoWindow, _PulseReason
from .splash import _SplashWindow
from .thread import ThreadUI


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

    def run_in_thread(self, target: Callable[[], None], *exceptions: type[Exception]) -> None:
        ThreadUI(self, *exceptions, create_mainloop=True).start(target)

    def set_infos(self, infos: Sequence[Info], player_relaunch: Optional[Callable[[], None]] = None) -> None:
        ok = self._infos.set(infos, player_relaunch)
        self._logo.set_pulse(ok=ok, reason=_PulseReason.PROXIES)

    def set_libmpv_auto_update(self, is_checked: bool, callback: Callable[[bool], None]) -> None:
        self._infos.set_libmpv_auto_update(is_checked, callback)

    def set_libmpv_download(self, version: str, download: Callable[[], None]) -> None:
        self._infos.set_libmpv_download(version, download)
        self._logo.set_pulse(ok=False, reason=_PulseReason.DOWNLOAD)

    def set_libmpv_downloading(self) -> None:
        self._logo.set_pulse(ok=True, reason=_PulseReason.DOWNLOAD)

    def set_libmpv_version(self, version: str) -> None:
        self._infos.set_libmpv_version(version)

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self._title, message=message)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._title}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> bool:
        return messagebox.askretrycancel(self._title, message=message)

    def askyesno(self, message: str) -> bool:
        return messagebox.askyesno(self._title, message=message)
