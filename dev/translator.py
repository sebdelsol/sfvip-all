import json
import sys
from pathlib import Path
from typing import Optional

from deep_translator import DeeplTranslator, GoogleTranslator
from tap import Tap

from secret import DEEPL_KEY

from .tools.color import Low, Ok, Title, Warn
from .tools.protocols import CfgFile, CfgTexts


# comments are turned into argparse help
class Args(Tap):
    force: bool = False  # force to update translations
    language: str = ""  # language to update, all by default


deepl_kwargs = dict(api_key=DEEPL_KEY, use_free_api=True)
deepl_supported_langs = DeeplTranslator(**deepl_kwargs).get_supported_languages()  # type: ignore


class Translator:
    marker_replace = "%s", "000"
    separator = ";"  # DO NOT use it in the texts (best separator found)

    def __init__(self, source: str, target: str) -> None:
        """prefer DeepL if it supports those languages"""
        if source in deepl_supported_langs and target in deepl_supported_langs:
            self.translator = DeeplTranslator(source, target, **deepl_kwargs)  # type: ignore
        else:
            self.translator = GoogleTranslator(source, target)

    @property
    def name(self) -> str:
        return self.translator.__class__.__name__.replace("Translator", "")

    def translate(self, *texts: str) -> Optional[list[str]]:
        """
        translate all texts as a bundle to keep its context
        replace %s with our own non translated marker
        """
        marker, marker_replacement = Translator.marker_replace
        # save where markers are
        is_markers = [marker in text for text in texts]
        bundle = Translator.separator.join(texts).replace(marker, marker_replacement)
        translation: str = self.translator.translate(bundle)
        if translation:
            translation = translation.replace(marker_replacement, marker)
            translations = list(filter(None, translation.split(Translator.separator)))
            if len(translations) == len(texts):
                # check markers are where they should be
                if all((marker in text) == is_marker for text, is_marker in zip(translations, is_markers)):
                    return translations
        return None


class IsNewer:
    def __init__(self, obj: type) -> None:
        module_file = sys.modules[obj.__module__].__file__
        assert module_file
        self.obj_mtime = Path(module_file).stat().st_mtime

    def than(self, file: Path) -> bool:
        return not file.exists() or file.stat().st_mtime < self.obj_mtime


def translate(texts: CfgTexts, all_languages: tuple[str, ...], translation_dir: CfgFile) -> None:
    assert isinstance(texts, type)
    is_newer_texts = IsNewer(texts)
    args = Args().parse_args()
    languages = [args.language] if args.language and args.language in all_languages else all_languages
    for target_language in languages:
        json_file = Path(translation_dir.path) / f"{target_language}.json"
        if args.force or is_newer_texts.than(json_file):
            texts_values = texts.as_dict().values()
            if target_language == texts.language:
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
