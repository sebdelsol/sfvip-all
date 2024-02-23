from build_config import Build, Environments, Github

from .tools.publisher import Publisher

if __name__ == "__main__":
    publisher = Publisher(Build, Environments, Github)
    publisher.publish_all()
    publisher.show_versions()
