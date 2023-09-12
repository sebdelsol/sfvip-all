from typing import Protocol

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()


class ToStyle(Protocol):  # to handle hint for the callable default parameter
    def __call__(self, txt: str = "") -> str:
        ...


def _use_style(style: str) -> ToStyle:
    return lambda txt="": f"{style}{txt}{Style.RESET_ALL}" if txt else style


class Stl:
    title = _use_style(Fore.GREEN + Style.BRIGHT)
    warn = _use_style(Fore.RED + Style.BRIGHT)
    high = _use_style(Fore.YELLOW)
    low = _use_style(Fore.CYAN)
