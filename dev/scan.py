from build_config import Build, Environments, Github, Readme

from .tools.scanner import VirusScanner
from .tools.templater import Templater

if __name__ == "__main__":
    VirusScanner().scan_all(Build, Environments)
    Templater(Build, Environments, Github).create(Readme)
