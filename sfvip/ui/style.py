from typing import Any, Self


class _Style(str):
    """
    str with tk style
    Example Use:
        style = _Style().font("Arial").font_size("12")
        text = style("a text).bigger(2).red.bold
        tk.Label(**text.to_tk)
        text2 = style("another text).green.italic
        tk.Button(**text2.to_tk)
    Do Not:
        tk.Button(text=text2) # see _Style.to_tk why

    """

    _known_font_styles = "bold", "italic"

    def __init__(self, _="") -> None:
        self._fg = "white"
        self._font = "Calibri"
        self._font_size = 10
        self._font_styles = set()

    def font(self, font: str) -> Self:
        return self._set_in_a_copy("_font", font)

    def font_size(self, font_size: int) -> Self:
        return self._set_in_a_copy("_font_size", font_size)

    def bigger(self, dsize: int) -> Self:
        return self._set_in_a_copy("_font_size", self._font_size + dsize)

    def smaller(self, dsize: int) -> Self:
        return self._set_in_a_copy("_font_size", max(1, self._font_size - dsize))

    def color(self, color: str) -> Self:
        return self._set_in_a_copy("_fg", color)

    def __getattr__(self, name: str) -> Self:
        """style or color"""
        if name in _Style._known_font_styles:
            self._font_styles.add(name)
            return self._set_in_a_copy("_font_styles", self._font_styles)
        if not name.startswith("_"):
            return self._set_in_a_copy("_fg", name.replace("_", " "))
        return self

    @property
    def to_tk(self) -> dict[str, Any]:
        return dict(text=str(self), fg=self._fg, font=self._font_str)

    def __repr__(self) -> str:
        # Note: self is callable and tk calls the given kwargs when creating a widget
        return f'"{str(self)}" ({self._fg} {self._font_str})'

    @property
    def _font_str(self) -> str:
        return f"{self._font} {self._font_size} {' '.join(self._font_styles)}".rstrip()

    def __call__(self, text: str) -> Self:
        a_copy = _Style(text)
        a_copy._fg = self._fg
        a_copy._font = self._font
        a_copy._font_size = self._font_size
        a_copy._font_styles = set(self._font_styles)
        return a_copy

    def _set_in_a_copy(self, name: str, value: Any) -> Self:
        a_copy = self(str(self))
        setattr(a_copy, name, value)
        return a_copy

    def __add__(self, txt):
        """Style + str"""
        return self(str(self) + txt)

    def __radd__(self, txt):
        """str + Style"""
        return self(txt + str(self))

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        # is it a str method ?
        if name in dir(str):

            def method(*args, **kwargs):
                """keep str methods returned values self style"""
                value = attr(*args, **kwargs)
                if isinstance(value, str):
                    return self(value)
                if isinstance(value, (list, tuple)):
                    return type(value)(map(self, value))
                return value

            return method

        return attr
