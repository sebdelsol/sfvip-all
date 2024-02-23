from typing import Optional

from build_config import Github, Translations
from translations.loc import LOC

from .tools.builder import Builder
from .tools.publisher import Publisher
from .tools.templater import Templater
from .tools.utils.protocols import CfgBuild, CfgEnvironments, CfgTemplate, CfgTemplates


def do_build(
    build: CfgBuild,
    environments: CfgEnvironments,
    templates: CfgTemplates,
    readme: CfgTemplate,
    publisher: Optional[Publisher] = None,
) -> None:
    LOC.set_tranlastions(Translations.path)
    if Builder(build, environments, LOC, publisher).build_all():
        Templater(build, environments, Github).create_all(templates)
        if publisher:
            publisher.show_versions()
    else:
        Templater(build, environments, Github).create(readme)


if __name__ == "__main__":
    import build_config

    PUBLISHER = Publisher(build_config.Build, build_config.Environments, Github)
    do_build(build_config.Build, build_config.Environments, build_config.Templates, build_config.Readme, PUBLISHER)
