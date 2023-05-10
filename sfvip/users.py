import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Callable, Self


class Users:
    """handle the users' database to add and remove the proxy setting"""

    _playlist_ext = ".m3u", ".m3u8"

    def __init__(self, config_dir: Path) -> None:
        self._database = config_dir / "Database.json"
        self.accessed_time = None

    @staticmethod
    def _is_playlist(user: dict) -> bool:
        path = Path(user["Address"])
        return path.suffix in Users._playlist_ext or path.exists()

    def _open(self, mode: str) -> IO:
        return self._database.open(mode=mode, encoding="utf-8")

    def _set_proxy(self, proxy_url: str) -> None:
        if self._database.exists():
            with self._open("r") as f:
                users = json.load(f)
            if users := [user for user in users if not self._is_playlist(user)]:
                for user in users:
                    user["HttpProxy"] = proxy_url
                with self._open("w") as f:
                    json.dump(users, f, indent=2, separators=(",", ":"))

    def restore_proxy(self, timeout: int = 5) -> None:
        if self.accessed_time:

            def wait(condition: Callable[[], bool]) -> Callable[[], bool]:
                def loop() -> bool:
                    while time.time() - self.accessed_time <= timeout:
                        if condition():
                            return True
                        time.sleep(0.1)
                    return False

                return loop

            def database_accessed() -> bool:
                return os.path.getatime(self._database) >= self.accessed_time

            def database_closed() -> bool:
                try:
                    os.rename(self._database, self._database)
                    return True
                except OSError:
                    return False

            # wait for the database to be accessed once and closed
            if wait(database_accessed)():
                if wait(database_closed)():
                    self._set_proxy("")

    @contextmanager
    def set_proxy(self, port: int) -> Self:
        self._set_proxy(f"http://127.0.0.1:{port}")
        self.accessed_time = os.path.getatime(self._database) + 0.001
        yield self
        self.restore_proxy()  # better safe than sorry
