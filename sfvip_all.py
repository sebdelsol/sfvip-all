import os
from pathlib import Path

from build_config import Build

# nuitka ?
if "__compiled__" in globals():
    # onefile ?
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        import sys

        # hack to make multiprocessing work with nuitka when the exe has been renamed
        # by forcing the built exe name on sys.argv[0]
        exe = Path(sys.argv[0]).parent / f"{Build.name}.exe"
        sys.argv[0] = str(exe.resolve())

if __name__ == "__main__":
    from sfvip import sfvip
    from sfvip_all_config import DefaultAppConfig

    app_config_file = Path(os.environ["APPDATA"]) / Build.name / "Config.json"
    app_config = DefaultAppConfig(app_config_file)
    sfvip(app_config, Build.name, Build.splash)
