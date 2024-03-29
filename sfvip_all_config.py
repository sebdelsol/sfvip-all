from src.config_loader import ConfigLoader


class AppDefaultConfig(ConfigLoader):
    class App:
        auto_update: bool = True
        retry_minutes: int = 10
        requests_timeout: int = 3
        show_proxies: bool = False
        n_logs_showed: int = 5

    class Player:
        exe: str | None = None
        auto_update: bool = True
        retry_minutes: int = 10
        requests_timeout: int = 5

    class Libmpv:
        auto_update: bool = True
        retry_minutes: int = 10
        requests_timeout: int = 3

    class EPG:
        url: str | None = None
        confidence: int = 30
        requests_timeout: int = 5
        prefer_internal: bool = True
