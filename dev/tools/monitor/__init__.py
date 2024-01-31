import msvcrt

from ..utils.color import Title, ToStyle


def _line_clear() -> None:
    print("\033[2K", end="")


def _line_back() -> None:
    print("\033[F", end="")


def clear_lines(n: int) -> None:
    for _ in range(n):
        _line_clear()
        _line_back()
        _line_clear()


def flushed_input(*text: str, to_style: ToStyle = Title) -> str:
    while msvcrt.kbhit():
        msvcrt.getch()
    print(*text, end="", sep="")
    return input(to_style()).lower()
