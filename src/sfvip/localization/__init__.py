import ctypes
import json
import locale
import logging
from pathlib import Path
from typing import Optional, Self

from .languages import all_languages, code_to_languages, languages_typo
from .texts import Texts

logger = logging.getLogger(__name__)


def _get_windows_language() -> str:
    # https://stackoverflow.com/a/25691701/3692322
    windll = ctypes.windll.kernel32
    return locale.windows_locale[windll.GetUserDefaultUILanguage()]


def _get_default_language() -> str:
    lang_code, country_code = _get_windows_language().split("_")
    language = code_to_languages.get(lang_code)
    if not language:
        language = code_to_languages.get(country_code)
        if not language:
            language = Texts.language
    return language


class _LOC(Texts):
    _encoding = "utf-8"

    def __init__(self) -> None:
        self._language = _get_default_language()

    def set_language(self, language: Optional[str]) -> Self:
        if language:
            language = languages_typo.get(language.lower(), language.lower())
            if language in all_languages:
                self._language = language
        return self

    def apply_language(self, translations: Path) -> None:
        translation_json = translations / f"{self._language}.json"
        try:
            with translation_json.open("r", encoding=_LOC._encoding) as f:
                translation: dict[str, str] = json.load(f)
            logger.info("%s translation loaded", self._language)
            for key, value in translation.items():
                if hasattr(_LOC, key):
                    setattr(_LOC, key, value)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("can't load %s translation", self._language)


LOC = _LOC()
