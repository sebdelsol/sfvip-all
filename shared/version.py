from functools import total_ordering
from typing import Iterator, Optional, Self


@total_ordering
class Version:
    def __init__(self, version_str: Optional[str]) -> None:
        self._version = version_str or "0"
        try:
            self._digits = tuple(self._split())
        except (TypeError, ValueError):
            self._digits = (0,)

    def _split(self) -> Iterator[int | float]:
        for digit in self._version.split("."):
            if digit.startswith("0") and len(digit) > 1:
                yield float(f"0.{digit[1:]}")
            else:
                yield int(digit)

    def _to_len(self, n) -> tuple[int | float, ...]:
        assert n >= len(self._digits)
        return *self._digits, *((0,) * (n - len(self._digits)))

    def __repr__(self) -> str:
        return ".".join(str(digit).replace(".", "") for digit in self._digits)

    def __eq__(self, other: Self) -> bool:
        n = max(len(self._digits), len(other._digits))
        return self._to_len(n) == other._to_len(n)

    def __gt__(self, other: Self) -> bool:
        n = max(len(self._digits), len(other._digits))
        return self._to_len(n) > other._to_len(n)

    def force_len(self, n: int) -> Self:
        self._digits = self._to_len(n)
        return self
