from build_config import Build, Environments, Github, Readme

from .tools.cleaner import clean_old_build

if __name__ == "__main__":
    clean_old_build(Build, Environments, Github, Readme)
