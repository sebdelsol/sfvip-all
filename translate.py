from build_config import Translations
from dev.translator import translate
from src.sfvip.localization.languages import all_languages
from src.sfvip.localization.texts import Texts

translate(Texts, all_languages, Translations)
