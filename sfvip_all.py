if __name__ == "__main__":
    import sfvip_all_config as Config
    from build_config import Build
    from sfvip import run

    run(Config, Build.name)
