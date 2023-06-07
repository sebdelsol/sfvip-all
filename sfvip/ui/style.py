from typing import Any, Self


class _Style(str):
    """
    str with tk style
    Example Use:
        style = _Style().font("Arial").font_size("12")
        text = style("a text").bigger(2).red.bold
        tk.Label(**text.to_tk)
        text2 = style("another text").green.italic
        tk.Button(**text2.to_tk)
    Do Not:
        tk.Button(text=text2) # check _Style.to_tk
    """

    _known_font_styles = "bold", "italic"

    def __init__(self, _="") -> None:
        self._fg = "white"
        self._font = "Calibri"
        self._font_size = 10
        self._font_styles = set()

    def __call__(self, text: str) -> Self:
        """return a COPY with a new text"""
        a_copy = _Style(text)
        a_copy._fg = self._fg
        a_copy._font = self._font
        a_copy._font_size = self._font_size
        a_copy._font_styles = set(self._font_styles)
        return a_copy

    def _update(self, name: str, value: Any) -> Self:
        """return a modified COPY"""
        a_copy = self(str(self))
        setattr(a_copy, name, value)
        return a_copy

    def font(self, font: str) -> Self:
        return self._update("_font", font)

    def font_size(self, font_size: int) -> Self:
        return self._update("_font_size", font_size)

    def bigger(self, dsize: int) -> Self:
        return self._update("_font_size", self._font_size + dsize)

    def smaller(self, dsize: int) -> Self:
        return self._update("_font_size", max(1, self._font_size - dsize))

    def color(self, color: str) -> Self:
        return self._update("_fg", color)

    def __getattr__(self, name: str) -> Self:
        """style or color"""
        if name in _Style._known_font_styles:
            self._font_styles.add(name)
            return self._update("_font_styles", self._font_styles)
        if not name.startswith("_"):
            return self._update("_fg", name.replace("_", " "))
        return self

    @property
    def to_tk(self) -> dict[str, Any]:
        # Note: self is callable (see __ call__)
        # and tk calls its kwargs if possible in widget creation
        return dict(text=str(self), fg=self._fg, font=self._font_str)

    def __repr__(self) -> str:
        return f'"{str(self)}" ({self._fg} {self._font_str})'

    @property
    def _font_str(self) -> str:
        return f"{self._font} {self._font_size} {' '.join(self._font_styles)}".rstrip()

    # def __add__(self, txt):
    #     """_Style + str"""
    #     return self(str(self) + txt)

    # def __radd__(self, txt):
    #     """str + _Style"""
    #     return self(txt + str(self))

    # def __getattribute__(self, name):
    #     """check when using any str function"""
    #     attr = super().__getattribute__(name)
    #     # is it a str method ?
    #     if name in dir(str):

    #         def method(*args, **kwargs):
    #             """keep str methods returned values of type _Style"""
    #             value = attr(*args, **kwargs)
    #             if isinstance(value, str):
    #                 return self(value)
    #             if isinstance(value, (list, tuple)):
    #                 return type(value)(map(self, value))
    #             return value

    #         return method

    #     return attr
