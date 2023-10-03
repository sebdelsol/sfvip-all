import json
import sys
from pathlib import Path
from typing import Optional

from deep_translator import DeeplTranslator, GoogleTranslator
from deep_translator.base import BaseTranslator
from tap import Tap

from secret import DEEPL_KEY

from .tools.color import Low, Ok, Title, Warn
from .tools.protocols import CfgFile, CfgTexts

deepl_kwargs = dict(api_key=DEEPL_KEY, use_free_api=True)


class Args(Tap):
    force_update: bool = False  # force to update translations


class Translator:
    separator = "\n"

    def __init__(self, translator: BaseTranslator) -> None:
        self.translator = translator

    def translate(self, *texts: str) -> Optional[list[str]]:
        to_translate = self.separator.join(f"- {text}" for text in texts)
        translated: str = self.translator.translate(to_translate)
        if translated:
            translated_texts = [text[2:] for text in translated.split(self.separator)]
            if len(translated_texts) == len(texts):
                return translated_texts
        return None


def get_class_mtime(obj: type) -> float:
    module_file = sys.modules[obj.__module__].__file__
    assert module_file
    return Path(module_file).stat().st_mtime


def translate(texts: CfgTexts, all_languages: tuple[str, ...], translation_dir: CfgFile) -> None:
    args = Args().parse_args()
    supported_langs = DeeplTranslator(**deepl_kwargs).get_supported_languages()  # type: ignore
    assert isinstance(texts, type)
    texts_mtime = get_class_mtime(texts)
    for target_language in all_languages:
        to_translate = texts.as_dict().values()

        _json = (Path(translation_dir.path) / target_language).with_suffix(".json")
        if args.force_update or not _json.exists() or _json.stat().st_mtime < texts_mtime:
            if target_language == texts.language:
                translated = to_translate
                translator_name = "No translator"
            else:
                translator_kwargs = dict(source=texts.language, target=target_language)
                translator = (
                    DeeplTranslator(**translator_kwargs, **deepl_kwargs)  # type: ignore
                    if texts.language in supported_langs and target_language in supported_langs
                    else GoogleTranslator(**translator_kwargs)  # type: ignore
                )
                translator_name = translator.__class__.__name__
                translated = Translator(translator).translate(*to_translate)
            if translated:
                print(Title("Translate to"), Ok(target_language), Low(translator_name))
                translation = dict(zip(texts.as_dict(), translated))
                with _json.open("w", encoding="utf-8") as f:
                    json.dump(translation, f, indent=2)
            else:
                print(Warn("No translation for"), Ok(target_language), Low(translator_name))
        else:
            print(Warn("Already translated to"), Ok(target_language))
