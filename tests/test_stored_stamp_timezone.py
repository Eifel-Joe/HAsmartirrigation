"""A stored naive stamp means the zone the PROCESS was in when it was written.

``datetime.now()`` with no argument returns a naive stamp in the process's
zone; ``dt_util.now()`` returns an aware one in HA's configured zone. The two
are equal only on HA OS and Supervised, which is why this went unnoticed -- see
docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md.
"""

import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import helpers, sensor, weather_aggregate

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


def test_naive_stamp_is_read_in_the_process_zone(monkeypatch):
    """A container running UTC wrote 12:00; that is 12:00 UTC, not 12:00 Berlin."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware("2026-09-21T12:00:00")

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_naive_stamp_follows_the_process_zone_not_has(monkeypatch):
    """Same bytes, different process zone -- a different instant."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: BERLIN)

    got = helpers.as_stored_aware("2026-09-21T12:00:00")

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=BERLIN)
    assert got.astimezone(UTC).hour == 10


def test_aware_stamp_passes_through_untouched(monkeypatch):
    """An offset on disk is self-describing; nothing may reinterpret it."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware("2026-09-21T12:00:00+02:00")

    assert got.utcoffset() == datetime.timedelta(hours=2)
    assert got.astimezone(UTC).hour == 10


def test_datetime_instances_are_accepted_like_strings(monkeypatch):
    """The store hands back live objects before a restart, strings after one."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware(datetime.datetime(2026, 9, 21, 12, 0))

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_none_passes_through_silently():
    """An unset watermark is normal, not an error (see helpers.as_datetime)."""
    assert helpers.as_stored_aware(None) is None
