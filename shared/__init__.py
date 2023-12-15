from typing import Literal


def get_bitness_str(is_64: bool) -> Literal["x64", "x86"]:
    return "x64" if is_64 else "x86"
