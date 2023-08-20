from build_config import Environments, Github
from builder import Builder, Datas, Templates
from builder.color import Stl


class Build:
    main = "sfvip_user_proxy/sfvip_user_proxy.py"
    dir = "sfvip_user_proxy/build"
    name = "SfvipUserProxy"
    version = "0.2"
    company = ""
    ico = ""


class UserProxyBuilder(Builder):
    def _get_nuitka_args(self, dist_temp: str) -> tuple[str, ...]:
        return (
            f"--onefile-tempdir-spec=%CACHE_DIR%/{self.build.name}",
            f"--output-filename={self.build.name}.exe",
            f"--output-dir={dist_temp}",
            "--assume-yes-for-downloads",
            "--enable-console",
            "--standalone",
            self.compiler,
            "--onefile",
            self.build.main,
        )


class UserProxyTemplates(Templates):
    def create_all(self) -> None:
        print(Stl.title("create"), Stl.high("post"))
        self._apply_template(
            "sfvip_user_proxy/post_template.txt",
            f"{self.build.dir}/{self.build.version}/post.txt",
        )


if __name__ == "__main__":
    UserProxyBuilder(Build, Environments, Datas()).build_all()
    UserProxyTemplates(Build, Environments, Github).create_all()
