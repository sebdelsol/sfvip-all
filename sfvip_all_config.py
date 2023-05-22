from config_loader import ConfigLoader


# pylint: disable=invalid-name
class DefaultAppConfig(ConfigLoader):
    class player:
        path: str | None = None

    class all_cat:
        inject: tuple[str, ...] = "series", "vod"
        name: str = "All"
        id: int = 0
