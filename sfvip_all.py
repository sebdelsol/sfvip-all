import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # reduce what's imported in the 2nd process
    import os
    import sys
    from pathlib import Path

    from build_config import Build
    from sfvip import sfvip
    from sfvip_all_config import DefaultAppConfig

    def remove_old_exe_logs(keep: int) -> None:
        if "__compiled__" in globals():
            # launched as an exe build by nuitka ? logs files are in the exe dir
            path = Path(sys.argv[0]).parent
            log_files = [file for file in path.iterdir() if file.match(f"{Build.name} - *.log")]
            if len(log_files) > keep:
                logger.info("keep the last %d logs", keep)
                log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                for log in log_files[keep:]:
                    try:
                        log.unlink(missing_ok=False)
                    except PermissionError:
                        pass

    def run() -> None:
        # use a different config json filename than sfvip player just in case
        config_json = Path(os.environ["APPDATA"]) / Build.name / "Config All.json"
        main_dir = Path(__file__).parent
        sfvip(
            DefaultAppConfig(config_json),
            Build.name,
            Build.version,
            main_dir / Build.splash,
            main_dir / Build.Logo.path,
        )

    logger.info("main process started")
    run()
    remove_old_exe_logs(keep=6)
    logger.info("main process exit")

else:
    logger.info("proxies process started")
