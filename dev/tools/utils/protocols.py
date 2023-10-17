from typing import Optional, Protocol, Sequence, runtime_checkable


class CfgFile(Protocol):
    path: str


@runtime_checkable
class CfgFileResize(CfgFile, Protocol):
    src: str
    resize: Optional[tuple[int, int]]


class CfgBuild(Protocol):
    ico: str
    main: str
    name: str
    company: str
    version: str
    dir: str
    logs_dir: str
    enable_console: bool
    install_finish_page: bool

    @property
    def install_cmd(self) -> Sequence[str]:
        ...

    @property
    def uninstall_cmd(self) -> Sequence[str]:
        ...

    @property
    def files(self) -> Sequence[CfgFile | CfgFileResize]:
        ...


class CfgGithub(Protocol):
    owner: str
    repo: str


class CfgTemplate(Protocol):
    src: str
    dst: str


class CfgTemplates(Protocol):
    @property
    def all(self) -> Sequence[CfgTemplate]:
        ...


class _CfgEnvironment(Protocol):
    path: str

    @property
    def constraints(self) -> Sequence[str]:
        ...


class CfgEnvironments(Protocol):
    @property
    def requirements(self) -> Sequence[str]:
        ...

    # pylint: disable=invalid-name
    @property
    def X86(self) -> _CfgEnvironment:
        ...

    @property
    def X64(self) -> _CfgEnvironment:
        ...


class CfgTexts(Protocol):
    language: str

    @staticmethod
    def as_dict() -> dict[str, str]:
        ...


class CfgLOC(Protocol):
    @property
    def AlreadyRunning(self) -> str:  # pylint: disable=invalid-name
        ...

    @property
    def all_languages(self) -> Sequence[str]:
        ...

    def set_language(self, language: Optional[str]) -> None:
        ...


# class CfgAppUpdate(Protocol):
#     def __call__(self, url: str, md5: str, version: str) -> Self:
#         ...

#     @property
#     def url(self) -> str:
#         ...

#     @property
#     def md5(self) -> str:
#         ...

#     @property
#     def version(self) -> str:
#         ...

#     @classmethod
#     def from_json(cls, json: Optional[Any]) -> Optional[Self]:
#         ...


# class _CfgAppUpdateLocation:
#     def __call__(self, build: CfgBuild, github: CfgGithub) -> Self:
#         ...

#     @property
#     def github(self) -> str:
#         ...

#     @property
#     def file(self) -> str:
#         ...

#     @property
#     def url(self) -> str:
#         ...


# class CfgAppLastestUpdate(Protocol):
#     def __call__(self, url: str) -> Self:
#         ...

#     def get(self, timeout: int) -> Optional[CfgAppUpdate]:
#         ...


# class CfgApp:
#     AppUpdateLocation: _CfgAppUpdateLocation
#     AppUpdate: CfgAppUpdate
#     AppLastestUpdate: CfgAppLastestUpdate
#     compute_md5: Callable[[Path], str]
