import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from ..ui.progress import ProgressWindow
from .cpu import Cpu
from .download import download_and_unpack, download_in_thread
from .libmpv import LibmpvDll

logger = logging.getLogger(__name__)


class _PlayerUpdate:
    bitness = "x64" if Cpu.is64 else "x86"
    _url = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"

    def __init__(self, player_exe: Path) -> None:
        self._player_exe = player_exe

    def download(self, progress: ProgressWindow) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "player update"
            if download_and_unpack(_PlayerUpdate._url, archive, self._player_exe.parent, progress):
                if self._player_exe.exists():
                    logger.info("player exe found")
                    return True
        return False


def download_player(player_name: str) -> Optional[str]:
    def download(progress: ProgressWindow) -> bool:
        if _PlayerUpdate(player_exe).download(progress):
            return LibmpvDll(player_exe).download_latest(progress)
        return False

    exe_dir = Path(sys.argv[0]).parent
    player_dir = exe_dir / f"{player_name.capitalize()} {_PlayerUpdate.bitness}"
    player_exe = player_dir / f"{player_name}.exe"
    if download_in_thread(f"Download {player_dir.name}", download, create_mainloop=True):
        return str(player_exe)
    shutil.rmtree(player_dir, ignore_errors=True)
    logger.warning("player download failed")
