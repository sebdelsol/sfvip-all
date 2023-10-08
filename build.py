from build_config import Build, Environments, Github, Readme, Templates
from dev.builder import Builder
from dev.cleaner import clean_old_build
from dev.publisher import Publisher
from dev.templater import Templater
from src.sfvip.localization.languages import all_languages

if __name__ == "__main__":
    if Builder(Build, Environments, Github, all_languages).build_all():
        Templater(Build, Environments, Github).create_all(Templates)
        Publisher(Build, Github).show_versions()
        clean_old_build(Build, Github)
    else:
        Templater(Build, Environments, Github).create(Readme)
