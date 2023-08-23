from tap import Tap

from build_config import Environments
from builder.env import PythonEnv
from builder.upgrader import Upgrader


class Args(Tap):
    eager: bool = False  # eager to upgrade All packages


if __name__ == "__main__":
    args = Args().parse_args()

    for env in Environments.x64, Environments.x86:
        python_env = PythonEnv(env)
        python_env.print()
        Upgrader(python_env).install_for(*Environments.requirements, eager=args.eager)
        print()
