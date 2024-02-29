import textwrap
from typing import Any, Optional, Self


class Style(str):
    """
    str with tk style
    Example Use:
        style = Style().font("Arial").font_size("12")
        text = style("a text").bigger(2).red.bold
        tk.Label(**text.to_tk)
        text2 = style("another text").green.italic
        tk.Button(**text2.to_tk)
    Do Not:
        tk.Button(text=text2) # check Style.to_tk
    """

    _known_font_styles = "bold", "italic", "overstrike"

    def __new__(cls, string: str = "", _: Optional[Self] = None) -> Self:
        instance = super().__new__(cls, string)
        return instance

    def __init__(self, _: str = "", style: Optional[Self] = None) -> None:
        if style is None:
            self._fg: str = "white"
            self._font: str = "Calibri"
            self._font_size: int = 10
            self._font_styles: set[str] = set()
            self._wrap: Optional[int] = None
            self._max_width: Optional[int] = None
        else:
            self._fg: str = style._fg
            self._font: str = style._font
            self._font_size: int = style._font_size
            self._font_styles: set[str] = set(style._font_styles)
            self._wrap: Optional[int] = style._wrap
            self._max_width: Optional[int] = style._max_width

    def __call__(self, text: Optional[str] = None) -> Self:
        return self.__class__(str(self) if text is None else text, self)

    @property
    def no_truncate(self) -> Self:
        self._max_width = None
        return self

    def wrap(self, wrap: int) -> Self:
        self._wrap = wrap
        return self

    def max_width(self, max_width: int) -> Self:
        self._max_width = max_width
        return self

    def font(self, font: str) -> Self:
        self._font = font
        return self

    def font_size(self, font_size: int) -> Self:
        self._font_size = font_size
        return self

    def bigger(self, dsize: int) -> Self:
        self._font_size += dsize
        return self

    def smaller(self, dsize: int) -> Self:
        self._font_size = max(1, self._font_size - dsize)
        return self

    def color(self, color: str) -> Self:
        self._fg = color
        return self

    def __getattr__(self, name: str) -> Self:
        """style or color"""
        if name in Style._known_font_styles:
            self._font_styles.add(name)
            self._font_styles = self._font_styles
        elif not name.startswith("_"):
            self._fg = name.replace("_", " ")  # lime_green -> lime green
        return self

    @property
    def to_tk(self) -> dict[str, Any]:
        # Note: self is callable and tk calls its kwargs in widget creation
        text = str(self)
        if self._wrap:
            text = "\n".join(textwrap.wrap(text, width=self._wrap))
        elif self._max_width and len(text) > self._max_width:
            assert self._max_width >= 3
            text = f"{text[:self._max_width-3]}..."
        return dict(text=text, fg=self._fg, font=self._font_str)

    def __repr__(self) -> str:
        max_width = f", max_width={self._max_width}" if self._max_width else ""
        return f'"{str(self)}" ({self._fg} {self._font_str}{max_width})'

    @property
    def _font_str(self) -> str:
        return f"{self._font} {self._font_size} {' '.join(self._font_styles)}".rstrip()

    # def __add__(self, text: str) -> Self:
    #     """needed for Style + str"""
    #     return self(str(self) + text)

    # def __radd__(self, text: str) -> Self:
    #     """needed for str + Style"""
    #     return self(text + str(self))

    # def __getattribute__(self, name: str) -> Any:
    #     """needed when using any regular str function"""
    #     attr = super().__getattribute__(name)
    #     # is it a str method ?
    #     if name in dir(str):

    #         def method(*args, **kwargs) -> Any:
    #             """keep str methods returned values of type Style"""
    #             value = attr(*args, **kwargs)
    #             if isinstance(value, str):
    #                 return self(value)
    #             if isinstance(value, (list, tuple)):
    #                 return type(value)(map(self, value))
    #             return value

    #         return method

    #     return attr
