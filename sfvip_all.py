import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

if __name__ == "__main__":
    # faster startup for the 2nd process
    import os
    import sys
    from pathlib import Path

    from build_config import Build
    from sfvip import sfvip
    from sfvip_all_config import DefaultAppConfig

    def remove_old_logs(keep: int) -> None:
        if "__compiled__" in globals():  # launched as an exe build by nuitka ?
            path = Path(sys.argv[0]).parent
            logs = [file for file in path.iterdir() if file.match(f"{Build.name} - *.log")]
            if len(logs) > keep:
                logs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                logging.info("keep the last %d logs", keep)
                for log in logs[keep:]:
                    try:
                        log.unlink(missing_ok=False)
                    except PermissionError:
                        pass

    def run() -> None:
        app_config_file = Path(os.environ["APPDATA"]) / Build.name / "Config.json"
        app_config = DefaultAppConfig(app_config_file)
        sfvip(app_config, Build.name, Build.splash)

    logging.info("main process")
    run()
    remove_old_logs(keep=6)
    logging.info("clean exit")

else:
    logging.info("2nd process")
