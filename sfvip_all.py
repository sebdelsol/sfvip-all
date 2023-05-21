if __name__ == "__main__":
    import os
    from pathlib import Path

    from build_config import Build
    from sfvip import sfvip
    from sfvip_all_config import DefaultAppConfig

    app_config_file = Path(os.environ["APPDATA"]) / Build.name / "Config.json"
    app_config = DefaultAppConfig(app_config_file)
    sfvip(app_config, Build.name, Build.splash)
