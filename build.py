from build_config import Build, Environments, Github, Logo, Splash
from builder import Builder, Datas, Templates

if __name__ == "__main__":
    datas = Datas(Logo, Splash)
    Builder(Build, Environments, datas).build_all()
    Templates(Build, Environments, Github).create_all()
