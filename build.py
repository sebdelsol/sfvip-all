from build_config import Build, Environments, Github, Logo, Nuitka, Splash, Templates
from builder import Builder, Datas, Templater

if __name__ == "__main__":
    Builder(Build, Environments, Nuitka, Datas(Logo, Splash)).build_all()
    Templater(Build, Environments, Templates, Github).create_all()
