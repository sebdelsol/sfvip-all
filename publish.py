from build_config import Build, Github
from dev.cleaner import clean_old_build
from dev.publisher import Publisher

if __name__ == "__main__":
    publisher = Publisher(Build, Github)
    if publisher.publish_all():
        clean_old_build(Build, Github)
    publisher.show_versions()
