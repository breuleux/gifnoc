import time as stdtime
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from serieux import TaggedSubclass

from .. import define


@dataclass
class NormalTime:
    def now(self):
        return datetime.now()

    def sleep(self, seconds):  # pragma: no cover
        stdtime.sleep(seconds)


@dataclass
class FrozenTime(NormalTime):
    # Datetime to freeze time at
    time: datetime = field(default_factory=datetime.now)

    # How long to pause when sleeping, in actual seconds (default: 0)
    sleep_beat: float = 0

    def now(self):
        return self.time

    def sleep(self, seconds):
        if self.sleep_beat:  # pragma: no cover
            stdtime.sleep(self.sleep_beat)
        self.time += timedelta(seconds=seconds)


# The indirection with a type alias helps Pylance, for some reason
TSNormalTime = TaggedSubclass[NormalTime]
time = define(
    field="time",
    model=TSNormalTime,
    defaults={},
)
