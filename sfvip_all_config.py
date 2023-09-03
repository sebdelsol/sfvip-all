from src.config import ConfigLoader


class AppConfig(ConfigLoader):
    class Player:
        path: str | None = None

    class AllCategory:
        name: str = "All"
        inject_in_live: bool = True
