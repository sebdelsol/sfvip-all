from src.config import ConfigLoader


class AppConfig(ConfigLoader):
    class Player:
        path: str | None = None

        class Libmpv:
            auto_update: bool = False
            retry_minutes: int = 10

    class AllCategory:
        name: str = "All"
        inject_in_live: bool = True
