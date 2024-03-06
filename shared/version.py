from functools import total_ordering
from itertools import zip_longest
from typing import Optional, Self


@total_ordering
class Version:
    def __init__(self, version: Optional[str], length: Optional[int] = None) -> None:
        try:
            self._digits = tuple(
                float(f"0.{digit[1:]}") if digit.startswith("0") and len(digit) > 1 else int(digit)
                for digit in (version or "0").split(".")
            )
        except (TypeError, ValueError, AttributeError):
            self._digits = (0,)
        if length:
            self._digits = *self._digits[:length], *((0,) * (length - len(self._digits)))

    def __str__(self) -> str:
        return ".".join(str(digit).replace(".", "") for digit in self._digits)

    __repr__ = __str__

    def __eq__(self, other: Self) -> bool:
        return tuple.__eq__(*zip(*zip_longest(self._digits, other._digits, fillvalue=0)))

    def __gt__(self, other: Self) -> bool:
        return tuple.__gt__(*zip(*zip_longest(self._digits, other._digits, fillvalue=0)))

    def __hash__(self) -> int:
        return hash(str(self))
