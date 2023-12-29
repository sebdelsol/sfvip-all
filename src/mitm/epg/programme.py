import base64
import logging
from datetime import datetime
from typing import NamedTuple, Optional, Self

logger = logging.getLogger(__name__)


class InternalProgramme(NamedTuple):
    start: str
    stop: str
    title: str
    desc: str


class EPGprogramme(dict[str, str]):
    @classmethod
    def from_programme(cls, programme: InternalProgramme, now: float) -> Optional[Self]:
        if programme.start and programme.stop:
            start = cls.get_timestamp(programme.start)
            end = cls.get_timestamp(programme.stop)
            if start and end and end >= now:
                return cls(
                    title=cls.get_text(programme.title),
                    description=cls.get_text(programme.desc),
                    start_timestamp=str(start),
                    stop_timestamp=str(end),
                    start=cls.get_date(start),
                    end=cls.get_date(end),
                )
        return None

    @staticmethod
    def get_text(text: str) -> str:
        return base64.b64encode(text.replace("\\", "").encode()).decode()

    @staticmethod
    def get_timestamp(date: str) -> Optional[int]:
        try:
            return round(datetime.strptime(date, r"%Y%m%d%H%M%S %z").timestamp())
        except ValueError:
            return None

    @staticmethod
    def get_date(timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp).strftime(r"%Y-%m-%d %H:%M:%S")
