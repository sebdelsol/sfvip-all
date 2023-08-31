from typing import Protocol, Sequence, runtime_checkable


class CfgFile(Protocol):
    path: str


@runtime_checkable
class CfgFileResize(CfgFile, Protocol):
    src: str
    resize: tuple[int, int]


class CfgBuild(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str

    @property
    def files(self) -> Sequence[CfgFile | CfgFileResize]:
        ...

    @property
    def nuitka(self) -> Sequence[str]:
        ...


class _CfgTemplate(Protocol):
    src: str
    dst: str


class CfgTemplates(Protocol):
    @property
    def all(self) -> Sequence[_CfgTemplate]:
        ...

    owner: str
    repo: str


class _CfgEnvironment(Protocol):
    path: str

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
