from src.config import ConfigLoader


class AppConfig(ConfigLoader):
    class Player:
        path: str | None = None
        auto_update_libmpv: bool = False

    class AllCategory:
        name: str = "All"
        inject_in_live: bool = True
