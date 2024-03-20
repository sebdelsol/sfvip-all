from pathlib import Path
from typing import Optional

from github import Auth, BadCredentialsException, Github, GithubException, UnknownObjectException
from github.GitRelease import GitRelease

from api_keys import GITHUB_TOKEN

from .env.envs import PythonEnv, PythonEnvs
from .utils.color import Ok, Title, Warn
from .utils.dist import Dist
from .utils.protocols import CfgBuild, CfgEnvironments, CfgGithub


class Release:
    def __init__(self, dist: Dist, github: CfgGithub) -> None:
        self.dist = dist
        try:
            with Github(auth=Auth.Token(GITHUB_TOKEN)) as git:
                user = git.get_user()
                assert user.login == github.owner
                self.repo = user.get_repo(github.repo)
        except BadCredentialsException:
            self.repo = None
            print(Warn("Can't access github"), Ok(f"{github.owner}/{github.repo}"))

    def get(self, version: str) -> Optional[GitRelease]:
        if not self.repo:
            return None
        tag = f"{self.dist.build_name}.{version}"
        try:
            release = self.repo.get_release(tag)
            print(Title("Update Release"), Ok(tag), end=" ", flush=True)
        except UnknownObjectException:
            try:
                release = self.repo.create_git_release(tag=tag, name=tag, message="", target_commitish="master")
                print(Title("Create release"), Ok(tag), end=" ", flush=True)
            except GithubException:
                release = None
                print(Warn("Can't create release"), Ok(tag), end=" ", flush=True)
        return release


class ReleaseCreator:
    def __init__(self, build: CfgBuild, environments: CfgEnvironments, github: CfgGithub) -> None:
        self.dist = Dist(build)
        self.release = Release(self.dist, github)
        self.all_python_envs = PythonEnvs(environments).all

    def add_installer(self, python_env: PythonEnv, release: Optional[GitRelease], version: str) -> Optional[str]:
        exe = self.dist.installer_exe(python_env, version)
        print(Ok(f". {exe.name}"), end=" ", flush=True)
        if not exe.is_file():
            print(Warn(". Missing"))
            return None
        if not release:
            print(Warn(". Has no release"))
            return None
        existing_assets = {Path(url := asset.browser_download_url).name: url for asset in release.get_assets()}
        if url := existing_assets.get(exe.name):
            print(Warn(". Already exists"))
            return None
        try:
            asset = release.upload_asset(path=str(exe.resolve()), name=exe.name)
            print(Title(". Added"))
            return asset.browser_download_url
        except GithubException:
            print(Warn(". Can't upload"))
            return None

    def create(self, python_env: PythonEnv, version: str) -> Optional[str]:
        release = self.release.get(version)
        return self.add_installer(python_env, release, version)
