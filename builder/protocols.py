from typing import Optional, Protocol


class Data(Protocol):
    @property
    def path(self) -> str:
        ...

    @property
    def src(self) -> Optional[tuple[str, int]]:
        ...


class CfgBuild(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str


class CfgNuitka(Protocol):
    args: list[str]


class CfgTemplates(Protocol):
    list: list[tuple[str, str]]


class CfgEnvironments(Protocol):
    requirements: list[str]
    x86: str
    x64: str


class CfgGithub(Protocol):
    owner: str
    repo: str
