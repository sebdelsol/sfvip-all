from pathlib import Path

from build_config import Build, Environments, Github, Readme, Templates, Translations
from src.sfvip.localization import LOC

from .tools.builder import Builder
from .tools.cleaner import clean_old_build
from .tools.publisher import Publisher
from .tools.templater import Templater

if __name__ == "__main__":
    LOC.set_tranlastions(Path(Translations.path))
    if Builder(Build, Environments, Github, LOC).build_all():
        Templater(Build, Environments, Github).create_all(Templates)
        Publisher(Build, Environments, Github).show_versions()
        clean_old_build(Build, Environments, Github, Readme)
    else:
        Templater(Build, Environments, Github).create(Readme)
