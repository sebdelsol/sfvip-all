from loader import Loader


# pylint: disable=invalid-name
class DefaultAppConfig(Loader):
    class player:
        path: str | None = None

    class all_cat:
        inject: tuple[str, ...] = "series", "vod"
        name: str = "All"
        id: int = 0
