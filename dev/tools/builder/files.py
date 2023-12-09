from abc import ABC, abstractmethod
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator, Sequence

from PIL import Image

from ..utils.color import Low, Ok, Title
from ..utils.dist import to_ico
from ..utils.protocols import CfgFile, CfgFileResize


class IncludeFiles(ABC):
    def __init__(self, files: Sequence[CfgFile | CfgFileResize], ico: str) -> None:
        ico_file = SimpleNamespace(src=ico, path=to_ico(ico), resize=None)
        self.files = ico_file, *files

    def _create_all(self) -> None:
        if self.files:
            for file in self.files:
                print(Title("Include"), Ok(file.path), end="")
                if isinstance(file, CfgFileResize):
                    print(Low(f" from {file.src}"), end="")
                    if file.resize:
                        print(Low(" - resized"), end="")
                        Image.open(file.src).resize(file.resize).save(file.path)
                    else:
                        Image.open(file.src).save(file.path)
                print()

    @property
    def all(self) -> Iterator[str]:
        self._create_all()
        for file in self.files:
            for file in self.get_file(Path(file.path)):
                yield file

    @abstractmethod
    def get_file(self, path: Path) -> Iterator[str]:
        ...
