from build_config import Build, Github, Readme
from dev.cleaner import clean_old_build

if __name__ == "__main__":
    clean_old_build(Build, Github, Readme)
