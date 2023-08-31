from build_config import Build, Environments, Templates
from builder import Builder, Templater

if __name__ == "__main__":
    Builder(Build, Environments).build_all()
    Templater(Build, Environments, Templates).create_all()
