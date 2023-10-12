from build_config import Translations
from src.sfvip.localization import LOC
from src.sfvip.localization.texts import Texts

from .tools.translator import translate

translate(Texts, LOC.all_languages, Translations)
