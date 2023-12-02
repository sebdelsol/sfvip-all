import build_config

from .tools.env.create import CreatePythonEnv

if __name__ == "__main__":
    CreatePythonEnv(build_config.Environments).create_and_install()
