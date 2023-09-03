from functools import partial
from typing import Protocol

from colorama import Fore, Style, init

init(autoreset=True)


def _to_style(style: str, txt: str = "") -> str:
    return f"{style}{txt}"


class ToStyle(Protocol):
    def __call__(self, txt: str = "") -> str:
        ...


class Stl:
    title = partial(_to_style, Fore.GREEN + Style.BRIGHT)
    warn = partial(_to_style, Fore.RED + Style.BRIGHT)
    high = partial(_to_style, Fore.YELLOW)
    low = partial(_to_style, Fore.CYAN)
