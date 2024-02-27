from build_config import Github

from .tools.publisher import Publisher
from .tools.templater import Templater
from .tools.utils.protocols import CfgBuild, CfgEnvironments, CfgTemplates


def do_publish(build: CfgBuild, environments: CfgEnvironments, templates: CfgTemplates) -> None:
    publisher = Publisher(build, environments, Github)
    published = publisher.publish_all()
    publisher.show_versions()
    if published:
        Templater(build, environments, Github, publisher).create_all(templates)


if __name__ == "__main__":
    import build_config

    do_publish(build_config.Build, build_config.Environments, build_config.Templates)
