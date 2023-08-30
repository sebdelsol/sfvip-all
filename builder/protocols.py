from typing import Optional, Protocol, Sequence


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
    @property
    def args(self) -> Sequence[str]:
        ...


class CfgTemplates(Protocol):
    @property
    def all(self) -> Sequence[tuple[str, str]]:
        ...


class CfgGithub(Protocol):
    owner: str
    repo: str


class _CfgEnvironment(Protocol):
    @property
    def path(self) -> str:
        ...

    @property
    def requirements(self) -> Sequence[str]:
        ...


class CfgEnvironments(Protocol):
    @property
    def x86(self) -> _CfgEnvironment:
        ...

    @property
    def x64(self) -> _CfgEnvironment:
        ...
