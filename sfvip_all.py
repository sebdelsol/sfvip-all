import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # reduce what's imported in the proxies process
    import os
    from pathlib import Path

    from build_config import Build
    from sfvip_all_config import DefaultAppConfig
    from src.sfvip import AppInfo, remove_old_exe_logs, run_app

    logger.info("main process started")
    config_path = Path(os.environ["APPDATA"]) / Build.name / "Config All.json"
    main_dir = Path(__file__).parent
    run_app(
        DefaultAppConfig(config_path),
        AppInfo(Build.name, Build.version, Build.Python.is_64bit, Build.System.is_64bit),
        main_dir / Build.splash,
        main_dir / Build.Logo.path,
    )
    remove_old_exe_logs(Build.name, keep=6)
    logger.info("main process exit")

else:
    logger.info("proxies process started")
