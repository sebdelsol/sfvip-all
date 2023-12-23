import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from shared import get_bitness_str
from translations.loc import LOC

from ..app_info import AppInfo
from ..ui.window import ProgressWindow
from ..utils.downloader import download_and_unpack, exceptions
from .cpu import Cpu
from .libmpv_dll import LibmpvDll

logger = logging.getLogger(__name__)


class _PlayerUpdater:
    _url = "https://raw.githubusercontent.com/K4L4Uz/SFVIP-Player/master/Update_{bitness}.zip"

    def __init__(self, player_exe: Path, bitness: bool) -> None:
        self._player_exe = player_exe
        self._download_url = _PlayerUpdater._url.format(bitness=get_bitness_str(bitness))

    def download(self, timeout: int, progress: ProgressWindow) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "player update"
            if download_and_unpack(self._download_url, archive, self._player_exe.parent, timeout, progress):
                if self._player_exe.exists():
                    logger.info("Player exe found")
                    return True
        return False


def download_player(player_name: str, app_info: AppInfo, timeout: int) -> Optional[str]:
    def download() -> bool:
        if _PlayerUpdater(player_exe, player_bitness).download(timeout, progress):
            return LibmpvDll(player_exe, timeout).download_latest(progress)
        return False

    player_bitness = Cpu.is64
    # in parent dir so it will be kept when uninstalling
    player_dir = app_info.current_dir.parent / f"{player_name.capitalize()} {get_bitness_str(player_bitness)}"
    player_exe = player_dir / f"{player_name}.exe"
    progress = ProgressWindow(f"{LOC.Download} {player_dir.name}")
    if progress.run_in_thread(download, *exceptions):
        return str(player_exe)
    shutil.rmtree(player_dir, ignore_errors=True)
    logger.warning("Player download failed")


def update_player(player_exe: Path, player_bitness: bool, timeout: int) -> bool:
    def download() -> bool:
        return _PlayerUpdater(exe, player_bitness).download(timeout, progress)

    with tempfile.TemporaryDirectory() as temp_dir:
        exe = Path(temp_dir) / player_exe.name
        progress = ProgressWindow(f"{LOC.Download} {player_exe.name}")
        if progress.run_in_thread(download, *exceptions):
            try:
                shutil.copytree(temp_dir, player_exe.parent, dirs_exist_ok=True)
                return True
            except shutil.Error:
                pass
        logger.warning("Player download failed")
        return False
