from build_config import Environments
from dev.tools.env import EnvArgs
from dev.upgrader import Upgrader


# comments are automatically turned into argparse help
class Args(EnvArgs):
    noeager: bool = False  # upgrade only needed packages


if __name__ == "__main__":
    args = Args().parse_args()
    for python_env in args.get_python_envs(Environments):
        print(python_env)
        if python_env.check():
            Upgrader(python_env).check(eager=not args.noeager)
