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
    def auto_update_libmpv(self) -> bool:
        return self._config.Player.auto_update_libmpv

    @auto_update_libmpv.setter
    def auto_update_libmpv(self, auto_update_libmpv: bool) -> None:
        self._config.update_field("Player.auto_update_libmpv", auto_update_libmpv)
