import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from ..tools.downloader import download_and_unpack, exceptions
from ..ui.window import ProgressWindow
from .cpu import Cpu
from .libmpv_dll import LibmpvDll

logger = logging.getLogger(__name__)


class _PlayerUpdater:
    bitness = "x64" if Cpu.is64 else "x86"
    _url = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"

    def __init__(self, player_exe: Path) -> None:
        self._player_exe = player_exe

    def download(self, timeout: int, progress: ProgressWindow) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "player update"
            if download_and_unpack(_PlayerUpdater._url, archive, self._player_exe.parent, timeout, progress):
                if self._player_exe.exists():
                    logger.info("player exe found")
                    return True
        return False


def download_player(player_name: str, timeout: int) -> Optional[str]:
    def download() -> bool:
        if _PlayerUpdater(player_exe).download(timeout, progress):
            return LibmpvDll(player_exe, timeout).download_latest(progress)
        return False

    exe_dir = Path(sys.argv[0]).parent
    player_dir = exe_dir / f"{player_name.capitalize()} {_PlayerUpdater.bitness}"
    player_exe = player_dir / f"{player_name}.exe"
    progress = ProgressWindow(f"Download {player_dir.name}")
    if progress.run_in_thread(download, *exceptions):
        return str(player_exe)
    shutil.rmtree(player_dir, ignore_errors=True)
    logger.warning("player download failed")
