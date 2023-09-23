from pathlib import Path
from typing import Optional

from sfvip_all_config import AppConfig


# TODO https://stackoverflow.com/questions/10967551/how-do-i-dynamically-create-properties-in-python
class Config:
    def __init__(self, app_roaming: Path) -> None:
        self._config = AppConfig(app_roaming / "Config All.json")
        self._config.update()

    @property
    def all_category(self) -> type[AppConfig.AllCategory]:
        return self._config.AllCategory

    @property
    def player_path(self) -> Optional[str]:
        return self._config.Player.path

    @player_path.setter
    def player_path(self, player_path: Optional[str]) -> None:
        self._config.update_field("Player.path", player_path)

    @property
    def libmpv_auto_update(self) -> bool:
        return self._config.Player.Libmpv.auto_update

    @libmpv_auto_update.setter
    def libmpv_auto_update(self, libmpv_auto_update: bool) -> None:
        self._config.update_field("Player.Libmpv.auto_update", libmpv_auto_update)

    @property
    def libmpv_retry_minutes(self) -> int:
        return self._config.Player.Libmpv.retry_minutes

    @libmpv_retry_minutes.setter
    def libmpv_retry_minutes(self, retry_minutes: int) -> None:
        self._config.update_field("Player.Libmpv.retry_minutes", retry_minutes)
