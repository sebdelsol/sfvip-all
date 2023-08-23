from typing import Optional, Protocol


class Data(Protocol):
    @property
    def path(self) -> str:
        ...

    @property
    def src(self) -> Optional[tuple[str, int]]:
        ...


class Build(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str


class Nuitka(Protocol):
    args: list[str]


class Templates(Protocol):
    list: list[tuple[str, str]]


class Environments(Protocol):
    requirements: list[str]
    x86: str
    x64: str


class Github(Protocol):
    owner: str
    repo: str
