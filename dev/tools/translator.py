import json
import re
import sys
from pathlib import Path
from typing import NamedTuple, Optional, Self, Sequence

from deep_translator import DeeplTranslator, GoogleTranslator
from deep_translator.exceptions import ServerException
from tap import Tap

from api_keys import DEEPL_KEY

from .utils.color import Low, Ok, Title, Warn
from .utils.protocols import CfgFile, CfgTexts


# comments are turned into argparse help
class Args(Tap):
    force: bool = False  # force to update translations
    language: str = ""  # language to update, all by default


class Marker(NamedTuple):
    marker: str
    replacement: str
    count: int


class MarkedText:
    var = "{}"
    ignore = "[]"
    replacement = "{:03}"

    regex = "|".join(f"{re.escape(marker[0])}.*?{re.escape(marker[1])}" for marker in (var, ignore))
    findall = re.compile(regex).findall

    def __init__(self, text: str) -> None:
        self.text = text
        self.markers: list[Marker] = []

    def prepare(self) -> Self:
        for i, marker in enumerate(MarkedText.findall(self.text)):
            count = self.text.count(marker)
            replacement = MarkedText.replacement.format(i)
            self.text = self.text.replace(marker, replacement)
            self.markers.append(Marker(marker, replacement, count))
        return self

    def finalize(self, translation: str) -> Optional[str]:
        for marker in self.markers:
            if marker.count != translation.count(marker.replacement):
                return None
            translation = translation.replace(marker.replacement, marker.marker)
        return self.ignored(translation).strip()

    @staticmethod
    def ignored(text: str) -> str:
        for char in MarkedText.ignore:
            text = text.replace(char, "")
        return text


class Translator:
    separator = "\n"  # DO NOT use it in the texts (best separator found)

    def __init__(self, source: str, target: str) -> None:
        """prefer DeepL if it supports those languages"""
        deepl_kwargs = dict(api_key=DEEPL_KEY, use_free_api=True)
        deepl_supported_langs = DeeplTranslator(**deepl_kwargs).get_supported_languages()  # type: ignore
        if source in deepl_supported_langs and target in deepl_supported_langs:
            self.translator = DeeplTranslator(source, target, **deepl_kwargs)  # type: ignore
        else:
            self.translator = GoogleTranslator(source, target)

    @property
    def name(self) -> str:
        return self.translator.__class__.__name__.replace("Translator", "")

    @staticmethod
    def no_translate(*texts: str) -> list[str]:
        return [MarkedText.ignored(text) for text in texts]

    def translate(self, *texts: str) -> Optional[list[str]]:
        """translate all texts as a bundle to keep its context"""
        marked_texts = [MarkedText(text).prepare() for text in texts]
        bundle = Translator.separator.join(marked.text for marked in marked_texts)
        try:
            translated = self.translator.translate(bundle)
        except ServerException:
            return None
        if translated:
            translations = translated.split(Translator.separator)
            # check markers are where they should be
            translations = [
                finalized_translation
                for translation, marked in zip(translations, marked_texts)
                if (finalized_translation := marked.finalize(translation))
            ]
            if len(translations) == len(marked_texts):
                return translations
        return None


class IsNewer:
    def __init__(self, obj: type) -> None:
        module_file = sys.modules[obj.__module__].__file__
        assert module_file
        self.obj_mtime = Path(module_file).stat().st_mtime

    def than(self, file: Path) -> bool:
        return not file.exists() or file.stat().st_mtime < self.obj_mtime


def translate(texts: CfgTexts, all_languages: Sequence[str], translation_dir: CfgFile) -> None:
    is_newer_texts = IsNewer(texts.__class__)
    args = Args().parse_args()
    languages = [args.language] if args.language and args.language in all_languages else all_languages
    for target_language in languages:
        json_file = Path(translation_dir.path) / f"{target_language}.json"
        if args.force or is_newer_texts.than(json_file):
            texts_values = texts.as_dict().values()
            if target_language == texts.language:
                texts_values = Translator.no_translate(*texts_values)
                using = "already translated"
            else:
                translator = Translator(texts.language, target_language)
                texts_values = translator.translate(*texts_values)
                using = f"with {translator.name}"
            if texts_values:
                print(Title("Translate to"), Ok(target_language), Low(using))
                with json_file.open("w", encoding="utf-8") as f:
                    json.dump(dict(zip(texts.as_dict(), texts_values)), f, ensure_ascii=False, indent=2)
            else:
                print(Warn("Translation failed for"), Ok(target_language), Low(using))
        else:
            print(Warn("Already translated to"), Ok(target_language))
