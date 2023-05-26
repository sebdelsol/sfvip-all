from config_loader import ConfigLoader


# pylint: disable=invalid-name
class DefaultAppConfig(ConfigLoader):
    class player:
        path: str | None = None

    class all_category:
        name: str = "All"
        inject_in_live: bool = True
