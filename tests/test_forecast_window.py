"""Expected precipitation over a run's calendar days.

Every number below is hand-computed. Series follow the clients' convention: a
rate in mm/h covering the interval that ENDS at its stamp. Time zones are passed
explicitly; nothing here reads Home Assistant's.
"""

import datetime
import math
import zoneinfo

import pytest

from custom_components.irrigation_plus.const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_PRECIPITATION,
)
from custom_components.irrigation_plus.forecast_window import expected_rain

UTC = datetime.timezone.utc
PLUS2 = datetime.timezone(datetime.timedelta(hours=2))
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


def _utc(*args):
    return datetime.datetime(*args, tzinfo=UTC)


def _hourly(first_hour_start, hours, rate):
    """``hours`` samples of ``rate``, stamped at the END of each hour."""
    return [
        (first_hour_start + datetime.timedelta(hours=i + 1), rate) for i in range(hours)
    ]


def _day(start, mm):
    return {
        FORECAST_DAY_START: start,
        FORECAST_DAY_END: start + datetime.timedelta(days=1),
        MAPPING_PRECIPITATION: mm,
    }


def test_the_rest_of_the_run_day_counts_from_the_evaluation():
    # 06:00 local (+02) on the 13th is 04:00 UTC; the local 13th ends 22:00 UTC.
    at = _utc(2026, 9, 13, 4, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=PLUS2,
        hourly=_hourly(_utc(2026, 9, 12, 22, 0), 24, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(18.0)
    assert rain.run_date_covered is True
    assert rain.complete is True


def test_the_evening_before_looks_at_the_run_date():
    # Evaluated 20:00 local on the 12th for a run at 06:00 local on the 13th.
    # Heavy rain late on the 12th is not on the run's date and must not count.
    hourly = _hourly(_utc(2026, 9, 12, 18, 0), 4, 5.0) + _hourly(
        _utc(2026, 9, 12, 22, 0), 24, 1.0
    )
    rain = expected_rain(
        run_start=_utc(2026, 9, 13, 4, 0),
        evaluated_at=_utc(2026, 9, 12, 18, 0),
        days=1,
        tz=PLUS2,
        hourly=hourly,
        daily=[],
    )
    assert rain.mm == pytest.approx(24.0)


def test_a_three_hourly_slot_across_midnight_is_split():
    # Local 13th (+02) is 12th 22:00Z .. 13th 22:00Z. The slot stamped 14th 00:00Z
    # covers 21:00Z .. 00:00Z, so one of its three hours falls inside.
    stamps = [
        _utc(2026, 9, 13, 0, 0) + datetime.timedelta(hours=3 * k) for k in range(9)
    ]
    hourly = [(s, 0.0) for s in stamps[:-1]] + [(stamps[-1], 3.0)]
    at = _utc(2026, 9, 12, 22, 0)
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=PLUS2, hourly=hourly, daily=[]
    )
    assert rain.mm == pytest.approx(3.0)
    assert rain.complete is True


def test_a_day_with_the_clocks_going_back_has_25_hours():
    # Local midnight of 2026-10-25 is 24th 22:00Z; the next local midnight is
    # 25th 23:00Z, because the clocks go back an hour that night.
    at = _utc(2026, 10, 24, 22, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=BERLIN,
        hourly=_hourly(at, 30, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(25.0)
    assert rain.complete is True


def test_24_hours_of_forecast_do_not_cover_a_25_hour_day():
    # The series stops at 25th 22:00Z, an hour before the local day ends. Measured
    # in wall-clock time the day would look like 24 hours and the missing hour
    # would pass unnoticed.
    at = _utc(2026, 10, 24, 22, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=BERLIN,
        hourly=_hourly(at, 24, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(24.0)
    assert rain.run_date_covered is False
    assert rain.complete is False


def test_a_day_with_the_clocks_going_forward_has_23_hours():
    # Local midnight of 2026-03-29 is 28th 23:00Z; the next is 29th 22:00Z.
    at = _utc(2026, 3, 28, 23, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=BERLIN,
        hourly=_hourly(at, 30, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(23.0)
    assert rain.complete is True


def test_a_gap_in_the_series_is_a_hole_not_a_stretch_of_the_next_rate():
    # Open-Meteo and Pirate Weather drop an hour without a value. The rows ending
    # 07:00..12:00 are missing; the 13:00 row forecasts 2 mm/h for 12:00-13:00.
    # Stretched back over the gap it would read as 14 mm, and the gap as forecast.
    at = _utc(2026, 9, 13, 0, 0)
    stamps = [at + datetime.timedelta(hours=h) for h in range(1, 25)]
    series = [
        (s, 2.0 if s.hour == 13 else 0.0) for s in stamps if not 7 <= s.hour <= 12
    ]
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=UTC, hourly=series, daily=[]
    )
    assert rain.mm == pytest.approx(2.0)
    assert rain.run_date_covered is False
    assert rain.complete is False


@pytest.mark.parametrize(
    "rates", [(4.0, 0.0), (0.0, 4.0)], ids=["high-first", "low-first"]
)
def test_a_duplicated_stamp_keeps_its_highest_rate(rates):
    # Whichever of the two rows a client lists last must not decide.
    at = _utc(2026, 9, 13, 0, 0)
    series = _hourly(at, 24, 0.0)
    stamp = series[5][0]
    series[5:6] = [(stamp, rates[0]), (stamp, rates[1])]
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=UTC, hourly=series, daily=[]
    )
    assert rain.mm == pytest.approx(4.0)
    assert rain.complete is True


def test_a_negative_rate_counts_as_a_dry_covered_hour():
    # A negative rate is a model artifact, not a missing hour: it must neither
    # subtract water nor leave a hole that stops the guard deciding.
    at = _utc(2026, 9, 13, 0, 0)
    series = _hourly(at, 24, 1.0)
    series[2] = (series[2][0], -5.0)  # 02:00-03:00 dry
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=UTC, hourly=series, daily=[]
    )
    assert rain.mm == pytest.approx(23.0)
    assert rain.run_date_covered is True
    assert rain.complete is True


def test_a_non_number_rate_counts_as_no_forecast():
    at = _utc(2026, 9, 13, 0, 0)
    series = _hourly(at, 24, 1.0)
    series[10] = (series[10][0], math.nan)  # 10:00-11:00 unknown
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=UTC, hourly=series, daily=[]
    )
    assert rain.mm == pytest.approx(23.0)
    assert rain.run_date_covered is False
    assert rain.complete is False


@pytest.mark.parametrize(("late", "covered"), [(0.5, True), (2.0, False)])
def test_a_series_starting_just_after_the_evaluation(late, covered):
    # The first sample reaches back one step. What is left before it counts as
    # covered within a second of the evaluation, and not beyond.
    at = _utc(2026, 9, 13, 0, 0)
    first = at + datetime.timedelta(seconds=late)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=UTC,
        hourly=_hourly(first, 25, 0.0),
        daily=[],
    )
    assert rain.run_date_covered is covered
