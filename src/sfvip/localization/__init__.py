import ctypes
import json
import locale
import logging
from pathlib import Path
from typing import Optional, Sequence

from .languages import code_to_languages, languages_typo
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
        self._translations = None

    @property
    def all_languages(self) -> Sequence[str]:
        return tuple(code_to_languages.values())

    def set_tranlastions(self, translations: Path) -> None:
        self._translations = translations

    def set_language(self, language: Optional[str]) -> None:
        if language:
            language = languages_typo.get(language.lower(), language.lower())
            if language in self.all_languages:
                self._language = language
        self._apply_language()

    def _apply_language(self) -> None:
        if self._translations is None:
            logger.warning("no translations found")
            return
        translation_json = self._translations / f"{self._language}.json"
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
