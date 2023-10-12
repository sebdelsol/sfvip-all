from build_config import Build, Environments, Github, Readme

from .tools.cleaner import clean_old_build
from .tools.publisher import Publisher

if __name__ == "__main__":
    publisher = Publisher(Build, Environments, Github)
    if publisher.publish_all():
        clean_old_build(Build, Environments, Github, Readme)
    publisher.show_versions()
