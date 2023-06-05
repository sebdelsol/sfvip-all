from typing import Any, Optional, Self


class _Style:
    _known_font_styles = "bold", "italic"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        bg: str = "black",
        fg: str = "white",
        font: str = "Calibri",
        font_size: int = 10,
        font_styles: Optional[set[str]] = None,
    ) -> None:
        self._bg = bg
        self._fg = fg
        self._font = font
        self._font_size = font_size
        self._font_styles = set() if font_styles is None else set(font_styles)

    def _copy(self) -> Self:
        return _Style(self._bg, self._fg, self._font, self._font_size, self._font_styles)

    def bigger(self, dsize: int) -> Self:
        style = self._copy()
        style._font_size += dsize
        return style

    def color(self, color: str) -> Self:
        style = self._copy()
        style._fg = color  # pylint: disable=protected-access
        return style

    def __getattr__(self, name: str) -> Self:
        style = self._copy()
        if name in _Style._known_font_styles:
            style._font_styles.add(name)
        else:
            style._fg = name.replace("_", " ")
        return style

    def __call__(self) -> dict[str, Any]:
        font = f"{self._font} {' '.join(self._font_styles)}" if self._font_styles else self._font
        return dict(bg=self._bg, fg=self._fg, font=(font, self._font_size))
