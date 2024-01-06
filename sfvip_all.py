# nuitka-project: --include-module=mitmproxy_windows
# nuitka-project: --enable-plugin=tk-inter
# nuitka-project: --nofollow-import-to=numpy

from src import set_logging

set_logging()

if __name__ == "__main__":
    # reduce what's imported in the proxies process
    import logging
    import sys
    from pathlib import Path

    # pylint: disable=ungrouped-imports
    from build_config import Build, Github
    from src import at_very_last, is_py_installer
    from src.sfvip import AppInfo, run_app

    if is_py_installer():
        import multiprocessing

        multiprocessing.freeze_support()

    # for debug purpose only
    if len(sys.argv) > 1 and sys.argv[1] == "fakev0":
        Build.version = "0"

    logging.info("Main process started")
    run_app(
        at_very_last.register,
        AppInfo.from_build(Build, Github, app_dir=Path(__file__).parent),
        keep_logs=6,
    )
    logging.info("Main process exit")
