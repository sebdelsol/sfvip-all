import json
import sys
from pathlib import Path
from typing import Optional

from deep_translator import DeeplTranslator, GoogleTranslator
from tap import Tap

from secret import DEEPL_KEY

from .tools.color import Low, Ok, Title, Warn
from .tools.protocols import CfgFile, CfgTexts


class Args(Tap):
    force: bool = False  # force to update translations
    language: str = ""  # language to update, all by default


deepl_kwargs = dict(api_key=DEEPL_KEY, use_free_api=True)
deepl_supported_langs = DeeplTranslator(**deepl_kwargs).get_supported_languages()  # type: ignore


class Translator:
    separator = "\n"
    prefix = "- "

    def __init__(self, source: str, target: str) -> None:
        """prefer DeepL if available"""
        if source in deepl_supported_langs and target in deepl_supported_langs:
            self.translator = DeeplTranslator(source, target, **deepl_kwargs)  # type: ignore
        else:
            self.translator = GoogleTranslator(source, target)

    @property
    def name(self) -> str:
        return self.translator.__class__.__name__

    def translate(self, *texts: str) -> Optional[list[str]]:
        """
        translate all texts as a whole to give context
        add a prefix to all textes keep Capitalization
        """
        to_translate = Translator.separator.join(f"{Translator.prefix}{text}" for text in texts)
        translation: str = self.translator.translate(to_translate)
        if translation:
            prefix_len = len(Translator.prefix)
            translations = [text[prefix_len:] for text in translation.split(Translator.separator)]
            if len(translations) == len(texts):
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
            to_translate = texts.as_dict().values()
            if target_language == texts.language:
                translation = to_translate
                name = "No translator"
            else:
                translator = Translator(texts.language, target_language)
                translation = translator.translate(*to_translate)
                name = translator.name
            if translation:
                print(Title("Translate to"), Ok(target_language), Low(name))
                with json_file.open("w", encoding="utf-8") as f:
                    json.dump(dict(zip(texts.as_dict(), translation)), f, indent=2)
            else:
                print(Warn("Translation failed for"), Ok(target_language), Low(name))
        else:
            print(Warn("Already translated to"), Ok(target_language))
