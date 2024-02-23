from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from github import Auth, Github, GithubException, UnknownObjectException
from github.GitRelease import GitRelease

from api_keys import GITHUB_TOKEN
from shared import BitnessT

from .env.envs import PythonEnv, PythonEnvs
from .scanner.file import ScanFile
from .utils.color import Low, Ok, Title, Warn
from .utils.dist import Dist, repr_size
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub


class InstallerRelease(NamedTuple):
    bitness: BitnessT
    scan: ScanFile | type[ScanFile] = ScanFile
    url: str = ""


class Release:
    def __init__(self, dist: Dist, github: CfgGithub) -> None:
        self.dist = dist
        with Github(auth=Auth.Token(GITHUB_TOKEN)) as git:
            user = git.get_user()
            assert user.login == github.owner
            self.repo = user.get_repo(github.repo)

    def get(self, version: str) -> Optional[GitRelease]:
        tag = f"{self.dist.build_name}.{version}"
        try:
            release = self.repo.get_release(tag)
            print(Title("Update Release"), Ok(tag))
        except UnknownObjectException:
            try:
                release = self.repo.create_git_release(
                    tag=tag,
                    name=tag,
                    message="",
                    target_commitish="master",
                )
                print(Title("Create release"), Ok(tag))
            except GithubException:
                release = None
                print(Warn("Can't create release"), Ok(tag))
        return release


class ReleaseCreator:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.dist = Dist(build)
        self.release = Release(self.dist, github)
        self.all_python_envs = PythonEnvs(environments).all

    def add_installer(self, python_env: PythonEnv, release: Optional[GitRelease]) -> InstallerRelease:
        exe = self.dist.installer_exe(python_env)
        bitness = python_env.bitness
        if not exe.is_file():
            print(Warn(". Missing"), Low(str(exe.name)))
            return InstallerRelease(bitness)
        scan_file = ScanFile(exe)
        if not scan_file.clean:
            print(Warn(". Not clean"), Low(str(exe.name)))
            return InstallerRelease(bitness)
        if not release:
            return InstallerRelease(bitness)
        existing_assets = {Path(url := asset.browser_download_url).name: url for asset in release.get_assets()}
        if url := existing_assets.get(exe.name):
            print(Warn(". Already exists"), Low(str(exe.name)))
            return InstallerRelease(bitness, scan_file, url)
        try:
            asset = release.upload_asset(path=str(exe.resolve()), name=exe.name)
            print(Title(". Add"), Ok(str(exe.name)), Low(repr_size(exe)))
            return InstallerRelease(bitness, scan_file, asset.browser_download_url)
        except GithubException:
            print(Warn(". Can't upload"), Low(str(exe.name)))
            return InstallerRelease(bitness)

    def create_all(self, version: str) -> Iterator[InstallerRelease]:
        release = self.release.get(version)
        for python_env in self.all_python_envs:
            yield self.add_installer(python_env, release)

    def create(self, python_env: PythonEnv, version: str) -> InstallerRelease:
        release = self.release.get(version)
        return self.add_installer(python_env, release)
