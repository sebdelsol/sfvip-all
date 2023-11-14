from build_config import Translations
from src.sfvip.localization import LOC
from src.sfvip.localization.texts import Texts

from .tools.translator import translate

if __name__ == "__main__":
    translate(Texts, LOC.all_languages, Translations)
