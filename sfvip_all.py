import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # reduce what's imported in the proxies process
    import os
    import platform
    import sys
    from pathlib import Path

    from build_config import Build
    from sfvip_all_config import AppConfig
    from src.sfvip import AppInfo, remove_old_exe_logs, run_app

    logger.info("main process started")
    config_path = Path(os.environ["APPDATA"]) / Build.name / "Config All.json"
    main_dir = Path(__file__).parent
    run_app(
        AppConfig(config_path),
        AppInfo(
            name=Build.name,
            version=Build.version,
            app_64bit=sys.maxsize == (2**63) - 1,
            os_64bit=platform.machine().endswith("64"),
        ),
        main_dir / Build.splash,
        main_dir / Build.Logo.path,
    )
    remove_old_exe_logs(Build.name, keep=6)
    logger.info("main process exit")

else:
    logger.info("proxies process started")
