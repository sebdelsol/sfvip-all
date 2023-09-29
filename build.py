from build_config import Build, Environments, Github, Templates
from dev.builder import Builder
from dev.cleaner import clean_old_build
from dev.publisher import Publisher
from dev.templater import Templater

if __name__ == "__main__":
    Builder(Build, Environments, Github).build_all()
    Templater(Build, Environments, Templates, Github).create_all()
    Publisher(Build, Github).show_published_version()
    clean_old_build(Build, Github)
