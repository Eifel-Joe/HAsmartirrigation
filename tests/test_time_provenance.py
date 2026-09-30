"""The two time provenances, named -- and, since the store's 14.2 migration, one clock.

A naive timestamp on these paths used to mean one of two different things:

- a **stored** stamp was written by a bare ``datetime.now()``, so naive meant the zone
  the PROCESS was in;
- a **client** row is a site-local clock time that came out of a weather API, so naive
  means HA's configured zone, and always did.

The two agree on HA OS and Supervised, which is why the seam went unnoticed; on Docker or
Core without ``TZ=`` they differed by the whole UTC offset. Stored stamps are now written
on HA's clock (``local_naive_now()``) and the store migration moved the older ones, so
both provenances read the same way. The names stay: every call site still says which kind
it holds.

Coercion normalises to the NAIVE form both paths use -- it does not make anything aware.
An aware stamp inside the live estimate's blanket ``except`` would raise
``can't compare offset-naive and offset-aware`` there, i.e. silently disable the estimate.
"""

import datetime
import os
import pathlib
import subprocess
import sys
import zoneinfo

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import helpers
from custom_components.irrigation_plus.helpers import (
    STAMP_FROM_CLIENT,
    STAMP_FROM_STORE,
    coerce_stamp,
)

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


@pytest.fixture
def split_zones(monkeypatch):
    """The container at UTC, the user at Europe/Berlin -- the case that separates them.

    HA's own setter is used for the zone, and it is restored to UTC rather than to
    whatever was found: the test plugin's cleanup check asserts UTC at teardown, and
    monkeypatch would faithfully put back a leaked value from an earlier test.
    """
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(UTC)


def test_an_aware_instant_is_read_on_has_clock_under_either_provenance(split_zones):
    """One aware instant, both provenances, one answer: 12:00 on the user's clock.

    Stored stamps are on HA's clock now, so the store provenance reads an aware one
    there too -- the answer the client provenance always gave. On the process's clock
    it was 10:00, the whole offset away.
    """
    instant = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    stored = coerce_stamp(instant, STAMP_FROM_STORE)
    client = coerce_stamp(instant, STAMP_FROM_CLIENT)

    assert stored == datetime.datetime(2026, 9, 21, 12, 0)
    assert client == datetime.datetime(2026, 9, 21, 12, 0)
    assert stored.tzinfo is None and client.tzinfo is None


def test_a_naive_value_is_returned_unchanged_under_either_provenance(split_zones):
    """A naive stamp is already in the frame, so nothing moves it.

    Every stamp a writer produces is naive on HA's clock, and so is every stamp the
    store migration leaves; coercing one again must not shift it.
    """
    naive = datetime.datetime(2026, 9, 21, 12, 0)

    assert coerce_stamp(naive, STAMP_FROM_STORE) == naive
    assert coerce_stamp(naive, STAMP_FROM_CLIENT) == naive
    assert coerce_stamp("2026-09-21T12:00:00", STAMP_FROM_STORE) == naive
    assert coerce_stamp("2026-09-21T12:00:00", STAMP_FROM_CLIENT) == naive


def test_local_naive_now_is_has_wall_clock_without_a_zone(split_zones):
    """The clock every weather-buffer stamp is written in and compared against."""
    with freeze_time("2026-09-21 10:00:00"):
        now = helpers.local_naive_now()

    assert now == datetime.datetime(2026, 9, 21, 12, 0)
    assert now.tzinfo is None


def test_the_process_zone_is_read_with_its_own_rules():
    """Each date at its own offset, not today's offset for every date.

    ``datetime.now().astimezone().tzinfo`` is a FIXED offset frozen at the moment of the
    call; in summer it reads a January stamp an hour off. The process zone cannot be set
    on Windows (no ``time.tzset()``), so this compares with what the C library says for
    each date. On a machine at UTC both are 0 and the check is idle; where the zone has
    DST it catches the fixed offset.
    """
    tz = helpers._process_timezone()

    for day in (
        datetime.datetime(2026, 1, 15, 12, 0),
        datetime.datetime(2026, 7, 15, 12, 0),
    ):
        assert tz.utcoffset(day) == day.astimezone().utcoffset(), day


# Run by the test below in a fresh interpreter: the offsets, in hours, that the process
# zone gives a date in January and one in July.
PRINT_THE_PROCESS_ZONE_OFFSETS = """
import datetime
from custom_components.irrigation_plus import helpers
tz = helpers._process_timezone()
for month in (1, 7):
    print(tz.utcoffset(datetime.datetime(2026, month, 15, 12, 0)).total_seconds() / 3600)
"""


def test_a_fresh_process_reads_its_zone_per_date():
    """The same property where the suite runs at UTC -- on CI, and under ``TZ=UTC``.

    The test above is idle there. A fresh interpreter reads ``TZ`` when it starts, on
    Windows too, so a child started at ``EST5EDT`` -- a POSIX zone string with US rules --
    has DST whatever the parent's zone: -5 h in January, -4 h in July. Today's fixed
    offset, UTC, or a fixed standard offset each read at least one of the dates wrong.
    """
    child = subprocess.run(
        [sys.executable, "-c", PRINT_THE_PROCESS_ZONE_OFFSETS],
        cwd=pathlib.Path(__file__).resolve().parent.parent,
        env={**os.environ, "TZ": "EST5EDT"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert child.returncode == 0, child.stderr
    assert child.stdout.split()[-2:] == ["-5.0", "-4.0"]


def test_coercing_without_naming_a_provenance_is_an_error():
    """No default provenance, so a caller cannot stay silent about which kind it holds.

    That is the requirement this function exists to satisfy: a future reader must not
    be able to coerce a forecast row as if it were a buffer stamp.
    """
    with pytest.raises(TypeError):
        coerce_stamp(datetime.datetime(2026, 9, 21, 12, 0))


def test_an_unusable_value_is_no_stamp_rather_than_a_raise(split_zones):
    """None and junk give None.

    ``parse_datetime`` lets ``fromisoformat``'s ValueError out, and these call sites
    sit inside a blanket ``except`` that turns a raise into the live estimate quietly
    going unavailable with a plausible "last calculated" still on display. A value
    this cannot read is no stamp, and the caller keeps whatever fallback it has.
    """
    assert coerce_stamp(None, STAMP_FROM_STORE) is None
    assert coerce_stamp("not a date", STAMP_FROM_STORE) is None
    assert coerce_stamp("not a date", STAMP_FROM_CLIENT) is None
    assert coerce_stamp(object(), STAMP_FROM_STORE) is None


def test_the_two_provenances_are_distinct_values():
    """They are compared by identity in the coercion, so they must not collapse."""
    assert STAMP_FROM_STORE != STAMP_FROM_CLIENT


def test_an_unknown_provenance_is_refused(split_zones):
    """A typo'd provenance must not silently pick one of the two rules."""
    with pytest.raises(ValueError):
        coerce_stamp(datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC), "site-local")
