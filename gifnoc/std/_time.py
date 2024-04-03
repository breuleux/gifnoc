import time as stdtime
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..interface import define
from ..type_wrappers import TaggedSubclass


@dataclass
class NormalTime:
    def now(self):
        return datetime.now()

    def sleep(self, seconds):
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
        if self.sleep_beat:
            stdtime.sleep(self.sleep_beat)
        self.time += timedelta(seconds=seconds)


time = define(
    field="time",
    model=TaggedSubclass[NormalTime],
)
