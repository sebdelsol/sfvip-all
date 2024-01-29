# nuitka-project: --include-module=mitmproxy_windows
# nuitka-project: --enable-plugin=tk-inter

from src import at_very_last, set_logging_and_exclude

set_logging_and_exclude("ipytv.playlist", "ipytv.channel", "mitmproxy.proxy.server")

if __name__ == "__main__":
    from shared import is_py_installer

    if is_py_installer():
        import multiprocessing

        # if it's a subprocess execution will stop here
        multiprocessing.freeze_support()

    # reduce what's imported in the subprocesses
    import logging
    import sys
    from pathlib import Path

    # pylint: disable=ungrouped-imports
    from build_config import Build, Github
    from shared import LogProcess
    from src.sfvip import AppInfo, run_app

    # for debug purpose only
    if len(sys.argv) > 1 and sys.argv[1] == "fakev0":
        Build.version = "0"

    app_dir = Path(__file__).parent
    logger = logging.getLogger(__name__)
    with LogProcess(logger, "Main"):
        run_app(
            at_very_last.register,
            AppInfo.from_build(Build, Github, app_dir=app_dir),
            keep_logs=3 * 2,
        )
