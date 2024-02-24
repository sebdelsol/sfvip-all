from build_config import Github, Translations
from translations.loc import LOC

from .tools.builder import Builder
from .tools.publisher import Publisher
from .tools.release import ReleaseCreator
from .tools.templater import Templater, get_template_by_name
from .tools.utils.protocols import CfgBuild, CfgEnvironments, CfgTemplates


def do_build(
    build: CfgBuild,
    environments: CfgEnvironments,
    templates: CfgTemplates,
    publish: bool = False,
) -> None:
    LOC.set_tranlastions(Translations.path)
    release = ReleaseCreator(build, environments, Github)
    publisher = Publisher(build, environments, Github, release) if publish else None
    if Builder(build, environments, LOC, publisher).build_all():
        Templater(build, environments, Github, release).create_all(templates)
        if publisher:
            publisher.show_versions()
    elif readme := get_template_by_name(templates, "Readme"):
        Templater(build, environments, Github, release).create(readme)


if __name__ == "__main__":
    import build_config

    do_build(build_config.Build, build_config.Environments, build_config.Templates, True)
