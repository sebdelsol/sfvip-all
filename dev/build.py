from build_config import Github, Translations
from translations.loc import LOC

from .tools.builder import Builder
from .tools.publisher import Publisher
from .tools.templater import Templater
from .tools.utils.protocols import CfgBuild, CfgEnvironments, CfgTemplates


def do_build(build: CfgBuild, environments: CfgEnvironments, templates: CfgTemplates) -> None:
    LOC.set_tranlastions(Translations.path)
    publisher = Publisher(build, environments, Github)
    if Builder(build, environments, LOC, publisher).build_all():
        publisher.show_versions()
    Templater(build, environments, Github, publisher).create_all(templates)


if __name__ == "__main__":
    import build_config

    do_build(build_config.Build, build_config.Environments, build_config.Templates)
