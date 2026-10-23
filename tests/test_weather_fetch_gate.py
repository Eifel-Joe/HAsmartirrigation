"""The freshness check the four weather clients share."""

import datetime
from datetime import timedelta

from freezegun import freeze_time

from custom_components.irrigation_plus.weathermodules.fetch_gate import (
    cache_lifetime,
    is_fresh,
)


def test_cache_lifetime_has_a_floor_of_sixty_seconds():
    assert cache_lifetime(0) == 60
    assert cache_lifetime(59) == 60
    assert cache_lifetime(599) == 599


@freeze_time("2026-10-23 12:00:00")
def test_is_fresh_matches_the_clients_old_rule():
    now = datetime.datetime.now()
    assert is_fresh(None, 599, False) is False
    assert is_fresh(now, 599, True) is False  # override_cache
    assert is_fresh(now - timedelta(seconds=598), 599, False) is True
    assert is_fresh(now - timedelta(seconds=599), 599, False) is False
    assert is_fresh(now - timedelta(seconds=59), 0, False) is True  # floor
