import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import atexit
    from typing import Callable

    class AtVeryLast:
        def __init__(self) -> None:
            self._last_action = None
            atexit.register(self._at_last)

        def _at_last(self) -> None:
            if self._last_action:
                self._last_action()

        def register(self, last_action: Callable[[], None]) -> None:
            self._last_action = last_action

    # done before everything else is imported
    # to be sure it'll be the very last to execute
    at_very_last = AtVeryLast()

    # reduce what's imported in the proxies process
    import sys
    from pathlib import Path

    from build_config import Build, Github, Logo, Splash
    from src.sfvip import AppInfo, run_app

    # TODO ask before hard relaunch
    # for debug purpose only
    if len(sys.argv) > 1 and sys.argv[1] == "fakev0":
        Build.version = "0"

    logger.info("main process started")
    app_dir = Path(__file__).parent
    run_app(
        at_very_last.register,
        AppInfo.from_build(Build, Github),
        app_dir / Splash.path,
        app_dir / Logo.path,
        keep_logs=6,
    )
    logger.info("main process exit")
