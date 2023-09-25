from src.config_loader import ConfigLoader


class AppConfig(ConfigLoader):
    class App:
        auto_update: bool = True
        retry_minutes: int = 10
        requests_timeout: int = 3

    class Player:
        path: str | None = None

        class Libmpv:
            auto_update: bool = True
            retry_minutes: int = 10
            requests_timeout: int = 3

    class AllCategory:
        name: str = "All"
        inject_in_live: bool = True
