import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # reduce what's imported in the proxies process
    from pathlib import Path

    from build_config import Build, Logo, Splash
    from src.sfvip import AppInfo, remove_old_exe_logs, run_app

    logger.info("main process started")
    app_dir = Path(__file__).parent
    run_app(AppInfo(Build.name, Build.version), app_dir / Splash.path, app_dir / Logo.path)
    remove_old_exe_logs(Build.name, keep=6)
    logger.info("main process exit")
