import random as stdrandom
from dataclasses import dataclass

from serieux import TaggedSubclass

from .. import define


@dataclass
class NormalRandom:
    seed: int | None = None

    def __post_init__(self):
        self.__random = stdrandom.Random()
        if self.seed is not None:
            self.__random.seed(self.seed)

    def random(self):
        return self.__random.random()

    def randint(self, a, b):
        return self.__random.randint(a, b)

    def choice(self, seq):
        return self.__random.choice(seq)

    def shuffle(self, x):
        return self.__random.shuffle(x)

    def randrange(self, *args):
        return self.__random.randrange(*args)

    def uniform(self, a, b):
        return self.__random.uniform(a, b)


random = define(
    field="random",
    model=TaggedSubclass[NormalRandom],
    defaults={},
)
