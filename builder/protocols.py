from typing import Optional, Protocol


class Data(Protocol):
    @property
    def path(self) -> str:
        ...

    @property
    def src(self) -> Optional[tuple[str, int]]:
        ...


class ConfigBuild(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str


class ConfigNuitka(Protocol):
    args: list[str]


class ConfigTemplates(Protocol):
    list: list[tuple[str, str]]


class ConfigEnvironments(Protocol):
    requirements: list[str]
    x86: str
    x64: str


class ConfigGithub(Protocol):
    owner: str
    repo: str
