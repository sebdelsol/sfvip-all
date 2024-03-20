from ctypes import (
    POINTER,
    Structure,
    WinError,
    byref,
    c_uint,
    c_uint16,
    c_void_p,
    cast,
    create_string_buffer,
    windll,
    wstring_at,
)
from typing import Optional


# returns the requested version information from the given file
# `what` is one of the predefined version information strings, such as "FileVersion" or "CompanyName"
# `language` should be an 8-character string combining both the language and
# codepage (such as "040904b0"); if None, the first language in the translation table is used instead
def get_version_string(filename: str, what: str, language: Optional[str] = None):
    class LANGANDCODEPAGE(Structure):
        _fields_ = [("wLanguage", c_uint16), ("wCodePage", c_uint16)]

    # getting the size in bytes of the file version info buffer
    size = windll.version.GetFileVersionInfoSizeW(filename, None)
    if size == 0:
        raise WinError()

    buffer = create_string_buffer(size)

    # getting the file version info data
    if windll.version.GetFileVersionInfoW(filename, None, size, buffer) == 0:
        raise WinError()

    # VerQueryValue() wants a pointer to a void* and DWORD; used both for
    # getting the default language (if necessary) and getting the actual data below
    value = c_void_p(0)
    value_size = c_uint(0)

    if language is None:
        # file version information can contain much more than the version
        # number (copyright, application name, etc.) and these are all translatable
        # the following arbitrarily gets the first language and codepage from
        # the list
        ret = windll.version.VerQueryValueW(
            buffer,
            r"\VarFileInfo\Translation",
            byref(value),
            byref(value_size),  # type: ignore
        )

        if ret == 0:
            raise WinError()

        # value points to a byte inside buffer, value_size is the size in bytes
        # of that particular section

        # casting the void* to a LANGANDCODEPAGE*
        lcp = cast(value, POINTER(LANGANDCODEPAGE))

        # formatting language and codepage to something like "040904b0"
        language = f"{lcp.contents.wLanguage:04x}{lcp.contents.wCodePage:04x}"

    # getting the actual data
    res = windll.version.VerQueryValueW(
        buffer, "\\StringFileInfo\\" + language + "\\" + what, byref(value), byref(value_size)
    )

    if res == 0:
        raise WinError()

    # value points to a string of value_size characters, minus one for the terminating null
    return wstring_at(value.value, value_size.value - 1)  # type: ignore
