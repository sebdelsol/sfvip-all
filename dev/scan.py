from build_config import Build, Environments, Github, Templates

from .tools.publisher import Publisher
from .tools.scanner import VirusScanner
from .tools.templater import Templater

if __name__ == "__main__":
    publisher = Publisher(Build, Environments, Github)
    VirusScanner().scan_all(Build, Environments, publisher)
    Templater(Build, Environments, Github, publisher).create(Templates, "Readme")
