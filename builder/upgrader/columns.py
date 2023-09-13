from enum import Enum
from functools import cached_property
from typing import Any, Callable, Generic, Sequence, TypeVar

T = TypeVar("T")


class Justify(Enum):
    LEFT = "<"
    RIGHT = ">"


class Columns(Generic[T]):
    def __init__(self, objs: Sequence[T]) -> None:
        self._objs = objs
        self._columns: list[list[str]] = []

    def _add_column(self, objs: Sequence[Any], to_str: Callable[[Any], str], justify: Justify) -> None:
        txts = [to_str(obj) for obj in objs]
        len_txt = len(max(txts, key=len))
        self._columns.append([f"{txt:{justify.value}{len_txt}}" for txt in txts])

    def add_attr_column(self, to_str: Callable[[T], str], justify: Justify) -> None:
        self._add_column(self._objs, to_str, justify)

    def add_no_column(self, to_str: Callable[[int], str], justify: Justify) -> None:
        self._add_column(range(len(self._objs)), to_str, justify)

    @cached_property
    def rows(self) -> list[str]:
        return [" ".join(row) for row in zip(*self._columns)]
