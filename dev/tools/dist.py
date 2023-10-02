from .env import get_bitness_str
from .protocols import CfgBuild


def get_dist_name(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/{build.version}/{get_bitness_str(is_64)}/{build.name}"


def get_dist_name_from_version(build: CfgBuild, is_64: bool, version: str) -> str:
    return f"{build.dir}/{version}/{get_bitness_str(is_64)}/{build.name}"


def get_dist_temp(build: CfgBuild, is_64: bool) -> str:
    return f"{build.dir}/temp/{get_bitness_str(is_64)}"