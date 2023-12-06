import sys

import build_config

from .tools.env.create import CreatePythonEnv

if __name__ == "__main__":
    calling_module = sys.modules[__name__]
    CreatePythonEnv(build_config.Environments).create_and_install(calling_module)
