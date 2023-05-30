import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

if __name__ == "__main__":
    # reduce what's imported in the 2nd process
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
        # use a different config json filename than sfvip player just in case
        config_json = Path(os.environ["APPDATA"]) / Build.name / "Config All.json"
        config = DefaultAppConfig(config_json)
        sfvip(config, Build.name, Build.splash)

    logging.info("main process started")
    run()
    remove_old_logs(keep=6)
    logging.info("main process exit")

else:
    logging.info("proxies process started")
