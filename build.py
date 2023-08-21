from build_config import Build, Environments, Github, Logo, Nuitka, Splash, Templates
from builder import Builder, CreateTemplates, Datas

if __name__ == "__main__":
    datas = Datas(Logo, Splash)
    Builder(Build, Environments, Nuitka, datas).build_all()
    CreateTemplates(Build, Environments, Templates, Github).create_all()
