from build_config import Build, Github
from dev.publisher import Publisher

if __name__ == "__main__":
    Publisher(Build, Github).publish_all()
