from pathlib import Path

from src.config_loader import ConfigLoader


class ScanFile(ConfigLoader):
    engine: str = "unknown"
    signature: str = "unknown"
    clean: bool = False

    def __init__(self, file: Path) -> None:
        super().__init__(file.with_suffix(".scan"), check_newer=False)
        self.update()

    def set(self, engine: str, signature: str, is_clean: bool) -> None:
        self.engine = engine
        self.signature = signature
        self.clean = is_clean
