from datetime import datetime, timedelta
from random import Random

import pytest

import gifnoc
from gifnoc.std import random, time


def test_normal_time():
    assert abs((time.now() - datetime.now()).total_seconds()) < 1


@pytest.mark.timeout(1)
def test_frozen_time():
    anchor = datetime(year=2024, month=1, day=1)
    with gifnoc.use({"time": {"class": "FrozenTime", "time": "2024-01-01T00:00"}}):
        assert time.now() == anchor
        time.sleep(24 * 60 * 60)
        assert time.now() == anchor + timedelta(days=1)


def test_seeded_random():
    seed = 1234
    rng = Random()
    rng.seed(seed)
    with gifnoc.use({"random": {"seed": seed}}):
        assert rng.random() == random.random()
        assert rng.randint(1, 100) == random.randint(1, 100)
        seq = list(range(10))
        seq2 = list(range(10))
        rng.shuffle(seq)
        random.shuffle(seq2)
        assert seq == seq2
        assert rng.choice(range(100)) == random.choice(range(100))
        assert rng.randrange(100) == random.randrange(100)
        assert rng.uniform(0, 1) == random.uniform(0, 1)
