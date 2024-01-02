import ctypes
import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional, Sequence

from ...mitm.epg.update import EPGProgress
from .infos import AppInfo, Info, InfosWindow
from .logo import LogoWindow, PulseReason
from .progress import ProgressBar
from .splash import SplashWindow
from .thread import ThreadUI
from .window import AskWindow, MessageWindow, Window

# avoid blurry text
ctypes.windll.shcore.SetProcessDpiAwareness(1)


class UI(tk.Tk):
    """basic UI with a tk mainloop, the app has to run in a thread"""

    def __init__(self, app_info: AppInfo) -> None:
        super().__init__()
        self.withdraw()  # we rely on some StickyWindow instead
        self._splash_img = tk.PhotoImage(file=app_info.splash)  # keep a reference for tk
        self.wm_iconphoto(True, self._splash_img)
        self.progress_bar = ProgressBar()
        self.splash = SplashWindow(self._splash_img)
        self._infos = InfosWindow(app_info)
        self._logo = LogoWindow(app_info.logo, self._infos)
        Window.set_logo(app_info.logo)
        self._title = f"{app_info.name} v{app_info.version} {app_info.bitness}"
        self._has_quit = False

    def quit(self) -> None:
        if not self._has_quit:
            self._has_quit = True
            Window.quit_all()
            ThreadUI.quit()
            super().quit()

    def run_in_thread(self, target: Callable[[], None], *exceptions: type[Exception]) -> None:
        ThreadUI(self, *exceptions).start(target)

    def set_infos(self, infos: Sequence[Info], player_relaunch: Optional[Callable[[int], None]] = None) -> None:
        ok = self._infos.set(infos, player_relaunch)
        self._logo.set_pulse(ok=ok, reason=PulseReason.RESTART_FOR_PROXIES)

    def set_epg_url_update(self, epg_url: Optional[str], callback: Callable[[str], None]) -> None:
        self._infos.set_epg_url_update(epg_url, callback)

    def set_epg_status(self, epg_status: EPGProgress) -> None:
        self._infos.set_epg_status(epg_status)

    def set_app_auto_update(self, is_checked: bool, callback: Callable[[bool], None]) -> None:
        self._infos.set_app_auto_update(is_checked, callback)

    def set_app_updating(self) -> None:
        self._logo.set_pulse(ok=True, reason=PulseReason.UPDATE_APP)

    def set_app_update(
        self,
        action_name: Optional[str] = None,
        action: Optional[Callable[[], None]] = None,
        version: Optional[str] = None,
    ) -> None:
        self._infos.set_app_update(action_name, action, version)
        self._logo.set_pulse(ok=action is None, reason=PulseReason.UPDATE_APP)

    def set_libmpv_auto_update(self, is_checked: bool, callback: Callable[[bool], None]) -> None:
        self._infos.set_libmpv_auto_update(is_checked, callback)

    def set_libmpv_updating(self) -> None:
        self._logo.set_pulse(ok=True, reason=PulseReason.UPDATE_LIBMPV)

    def set_libmpv_update(
        self,
        action_name: Optional[str] = None,
        action: Optional[Callable[[], None]] = None,
        version: Optional[str] = None,
    ) -> None:
        self._infos.set_libmpv_update(action_name, action, version)
        self._logo.set_pulse(ok=action is None, reason=PulseReason.UPDATE_LIBMPV)

    def set_libmpv_version(self, version: Optional[str]) -> None:
        self._infos.set_libmpv_version(version)

    def set_player_version(self, version: Optional[str]) -> None:
        self._infos.set_player_version(version)

    def set_player_auto_update(self, is_checked: bool, callback: Callable[[bool], None]) -> None:
        self._infos.set_player_auto_update(is_checked, callback)

    def set_player_updating(self) -> None:
        self._logo.set_pulse(ok=True, reason=PulseReason.UPDATE_PLAYER)

    def set_player_update(
        self,
        action_name: Optional[str] = None,
        action: Optional[Callable[[], None]] = None,
        version: Optional[str] = None,
    ) -> None:
        self._infos.set_player_update(action_name, action, version)
        self._logo.set_pulse(ok=action is None, reason=PulseReason.UPDATE_PLAYER)

    def showinfo(self, message: str, force_create: bool = False) -> None:
        def _showinfo() -> bool:
            message_win.wait_window()
            return True

        message_win = MessageWindow(self._title, message, force_create=force_create)
        message_win.run_in_thread(_showinfo)

    def ask(self, message: str, ok: str, cancel: str) -> Optional[bool]:
        def _ask() -> Optional[bool]:
            ask_win.wait_window()
            return ask_win.ok

        ask_win = AskWindow(self._title, message, ok, cancel)
        return ask_win.run_in_thread(_ask)

    def find_file(self, name: str, pattern: str) -> str:
        title = f"{self._title}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])
