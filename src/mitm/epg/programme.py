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


class Schedule(NamedTuple):
    start: int
    end: int

    @classmethod
    def from_programme(cls, programme: InternalProgramme, now: float) -> Optional[Self]:
        if programme.start and programme.stop:
            start = cls._get_timestamp(programme.start)
            end = cls._get_timestamp(programme.stop)
            if start and end and end >= now:
                return cls(start, end)
        return None

    @staticmethod
    def _get_timestamp(date: str) -> Optional[int]:
        try:
            return round(datetime.strptime(date, r"%Y%m%d%H%M%S %z").timestamp())
        except ValueError:
            return None

    @staticmethod
    def _get_date(timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp).strftime(r"%Y-%m-%d %H:%M")

    @staticmethod
    def _get_hour(timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp).strftime(r"%H:%M")

    def get_start_date(self) -> str:
        return self._get_date(self.start)

    def get_end_date(self) -> str:
        return self._get_hour(self.end)


class EPGprogrammeXC(dict[str, str]):
    @classmethod
    def from_programme(cls, programme: InternalProgramme, now: float) -> Optional[Self]:
        if schedule := Schedule.from_programme(programme, now):
            return cls(
                title=cls.get_text(programme.title),
                description=cls.get_text(programme.desc),
                start_timestamp=str(schedule.start),
                stop_timestamp=str(schedule.end),
                start=schedule.get_start_date(),
                end=schedule.get_end_date(),
            )
        return None

    @staticmethod
    def get_text(text: str) -> str:
        return base64.b64encode(text.replace("\\", "").encode()).decode()


class EPGprogrammeMAC(dict[str, str | int]):
    @classmethod
    def from_programme(cls, programme: InternalProgramme, now: float) -> Optional[Self]:
        if schedule := Schedule.from_programme(programme, now):
            return cls(
                name=cls.get_text(programme.title),
                descr=cls.get_text(programme.desc),
                duration=schedule.end - schedule.start,
                start_timestamp=str(schedule.start),
                stop_timestamp=str(schedule.end),
                time=schedule.get_start_date(),
                time_to=schedule.get_end_date(),
            )
        return None

    @staticmethod
    def get_text(text: str) -> str:
        return text.replace("\\", "")


class EPGprogrammeM3U(NamedTuple):
    title: str
    descr: str
    start: str
    end: str
    start_timestamp: int
    duration: int

    @classmethod
    def from_programme(cls, programme: InternalProgramme, now: float) -> Optional[Self]:
        if schedule := Schedule.from_programme(programme, now):
            return cls(
                title=cls.get_text(programme.title),
                descr=cls.get_text(programme.desc),
                start=schedule.get_start_date(),
                end=schedule.get_end_date(),
                start_timestamp=schedule.start,
                duration=schedule.end - schedule.start,
            )
        return None

    @staticmethod
    def get_text(text: str) -> str:
        return text.replace("\\", "")


EPGprogramme = EPGprogrammeXC | EPGprogrammeMAC | EPGprogrammeM3U
