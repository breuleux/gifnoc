from datetime import datetime, timedelta

import pytest

import gifnoc
from gifnoc.std import time


def test_normal_time():
    assert abs((time.now() - datetime.now()).total_seconds()) < 1


@pytest.mark.timeout(1)
def test_frozen_time():
    anchor = datetime(year=2024, month=1, day=1)
    with gifnoc.use({"time": {"class": "FrozenTime", "time": "2024-01-01T00:00"}}):
        assert time.now() == anchor
        time.sleep(24 * 60 * 60)
        assert time.now() == anchor + timedelta(days=1)
