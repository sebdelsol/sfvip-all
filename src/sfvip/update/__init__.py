import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional
from urllib.error import ContentTooShortError, HTTPError, URLError

from .cpu import Cpu
from .libmpv import LibmpvDll
from .progress import Progress

logger = logging.getLogger(__name__)


class PlayerUpdate:
    bitness = "x64" if Cpu.is64 else "x86"
    _url = f"https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"

    @staticmethod
    def download(player_exe: Path, progress: Progress) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "player update"
            progress.download_and_unpack(PlayerUpdate._url, archive, player_exe.parent)
            if player_exe.exists():
                logger.info("player exe found")
                return True
        return False


def download_player(player_name: str) -> Optional[str]:
    def run() -> bool:
        if PlayerUpdate.download(player_exe, progress):
            progress.msg("Check latest libmpv")
            libmpv_dll = LibmpvDll(player_exe)
            if libmpv := libmpv_dll.check():
                return libmpv_dll.download(libmpv, progress)
        return False

    exceptions = OSError, URLError, HTTPError, ContentTooShortError, ValueError, shutil.ReadError
    exe_dir = Path(sys.argv[0]).parent
    player_dir = exe_dir / f"{player_name.capitalize()} {PlayerUpdate.bitness}"
    progress = Progress(f"Download {player_dir.name}", 400, *exceptions)
    player_exe = player_dir / f"{player_name}.exe"
    try:
        if progress.run_in_thread(run, *exceptions, mainloop=True):
            return str(player_exe)
    except exceptions as err:
        logger.warning("player download exception %s", err)
    shutil.rmtree(player_dir, ignore_errors=True)
    logger.warning("player download failed")
