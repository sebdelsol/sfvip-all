from typing import Protocol

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()


class ToStyle(Protocol):  # to handle hint for the callable default parameter
    def __call__(self, txt: str = "") -> str:
        ...


def _use_style(style: str) -> ToStyle:
    return lambda txt="": f"{style}{txt}{Style.RESET_ALL}" if txt else style


Title = _use_style(Fore.YELLOW + Style.BRIGHT)
Warn = _use_style(Fore.RED + Style.BRIGHT)
Ok = _use_style(Fore.GREEN + Style.BRIGHT)
Low = _use_style(Fore.CYAN)
