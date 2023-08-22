import argparse

from build_config import Environments
from builder.env import PythonEnv
from builder.upgrader import Upgrader

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eager", action="store_true", help="eager to upgrade All package")
    eager = parser.parse_args().eager

    for env in Environments.x64, Environments.x86:
        python_env = PythonEnv(env)
        python_env.print()
        Upgrader(python_env).install_for(*Environments.requirements, eager=eager)
        print()
