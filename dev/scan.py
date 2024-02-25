from build_config import Github

from .tools.publisher import Publisher
from .tools.scanner import VirusScanner
from .tools.templater import Templater
from .tools.utils.protocols import CfgBuild, CfgEnvironments, CfgTemplates


def do_scan(build: CfgBuild, environments: CfgEnvironments, templates: CfgTemplates) -> None:
    publisher = Publisher(build, environments, Github)
    VirusScanner().scan_all(build, environments, publisher)
    Templater(build, environments, Github, publisher).create(templates, "Readme")


if __name__ == "__main__":
    import build_config

    do_scan(build_config.Build, build_config.Environments, build_config.Templates)
