from build_config import Translations
from translations.loc import LOC, Texts

from .tools.translator import translate

if __name__ == "__main__":
    translate(Texts, LOC.all_languages, Translations)
