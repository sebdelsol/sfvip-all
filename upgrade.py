from build_config import Build
from builder.env import PythonEnv
from builder.upgrader import Upgrader

if __name__ == "__main__":
    for env in Build.Environment.x64, Build.Environment.x86:
        python_env = PythonEnv(env)
        python_env.print()
        Upgrader(python_env).install_for(*Build.requirements)
        print()
