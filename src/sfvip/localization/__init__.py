import ctypes
import json
import locale
import logging
from pathlib import Path
from typing import Optional

from .languages import all_languages, code_to_languages, languages_typo
from .texts import Texts

logger = logging.getLogger(__name__)


def get_windows_language() -> str:
    # https://stackoverflow.com/a/25691701/3692322
    windll = ctypes.windll.kernel32
    return locale.windows_locale[windll.GetUserDefaultUILanguage()]


class _LOC(Texts):
    encoding = "utf-8"

    def __init__(self) -> None:
        lang, country = get_windows_language().split("_")
        language = code_to_languages.get(lang)
        if not language:
            language = code_to_languages.get(country)
            if not language:
                language = Texts.language
        self._language = language
        self._apply_language()

    def set_language(self, language: Optional[str]) -> None:
        if language:
            language = languages_typo.get(language.lower(), language.lower())
            if language in all_languages:
                self._language = language
                self._apply_language()

    def _apply_language(self) -> None:
        assert self._language
        translation_json = (Path("translations") / self._language).with_suffix(".json")
        if translation_json.exists():
            try:
                with translation_json.open("r", encoding=_LOC.encoding) as f:
                    translation: dict[str, str] = json.load(f)
                logger.info("%s translation loaded", self._language)
                for key, value in translation.items():
                    setattr(_LOC, key, value)
            except json.JSONDecodeError:
                logger.warning("can't load %s translation", self._language)


LOC = _LOC()
