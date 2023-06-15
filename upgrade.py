from build_config import Environments
from builder.env import PythonEnv
from builder.upgrader import Upgrader

if __name__ == "__main__":
    for env in Environments.x64, Environments.x86:
        python_env = PythonEnv(env)
        python_env.print()
        Upgrader(python_env).install_for(*Environments.requirements)
        print()
