"""Tests for o1.py, the oracle of the Eifel-Joe#61 live verification."""
from datetime import datetime, timedelta, timezone

import pytest

import o1

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def rows(rate_at=lambda k: 1.0, first=-30, last=40, drop=()):
    """Hourly rows [unix, rate] for stamps T0 + k h, k in [first, last]."""
    return [
        [int((T0 + k * H).timestamp()), rate_at(k)]
        for k in range(first, last + 1)
        if k not in drop
    ]


def test_an_aligned_window_sums_24_whole_hours():
    series = o1.hourly_series(rows())
    assert o1.window_mm(series, T0 + 2 * H, T0) == pytest.approx(24.0)


def test_a_rate_covers_the_hour_ending_at_its_stamp_pro_rata():
    # only the stamp T0+5h rains (6 mm/h), i.e. the interval (T0+4h, T0+5h]
    series = o1.hourly_series(rows(lambda k: 6.0 if k == 5 else 0.0))
    start = T0 + 4 * H + timedelta(minutes=33)
    assert o1.window_mm(series, start, T0) == pytest.approx(6.0 * 27 / 60)
    end_inside = T0 + 4 * H + timedelta(minutes=27) - 24 * H
    assert o1.window_mm(series, end_inside, end_inside) == pytest.approx(6.0 * 27 / 60)


def test_the_part_before_the_evaluation_is_cut_off():
    series = o1.hourly_series(rows())
    assert o1.window_mm(series, T0, T0 + 6 * H) == pytest.approx(18.0)


def test_a_window_beyond_the_series_is_refused():
    series = o1.hourly_series(rows())
    with pytest.raises(ValueError, match="not covered"):
        o1.window_mm(series, T0 + 30 * H, T0)


def test_a_hole_inside_the_window_is_refused_and_one_outside_is_not():
    series = o1.hourly_series(rows(drop={10}))
    with pytest.raises(ValueError, match="hole"):
        o1.window_mm(series, T0, T0)
    assert o1.window_mm(series, T0 + 11 * H, T0) == pytest.approx(24.0)


def test_negative_is_dry_and_a_duplicate_stamp_keeps_the_maximum():
    r = rows(lambda k: -1.0)
    r.append([int((T0 + 3 * H).timestamp()), 2.0])
    series = o1.hourly_series(r)
    assert o1.window_mm(series, T0, T0) == pytest.approx(2.0)


def test_a_raw_log_line_is_parsed_from_the_python_repr():
    line = (
        "\x1b[37m2026-10-07 09:12:01.123 DEBUG (SyncWorker_3) "
        "[custom_components.irrigation_plus.weathermodules.PirateWeatherClient] "
        "PirateWeatherClient get_data called API https://api.pirateweather.net/forecast/***/52.5,13.4"
        "?units=si and received {'currently': {'time': 1, 'icon': None}, 'hourly': {'data': "
        "[{'time': 1791331200, 'precipIntensity': 0.25, 'precipType': 'rain'}, "
        "{'time': 1791334800, 'precipIntensity': 0}]}, 'flags': {'units': 'si', 'x': True}}\x1b[0m"
    )
    parsed = o1.parse_log_line(line)
    assert parsed["logged_at"] == "2026-10-07 09:12:01.123"
    assert parsed["method"] == "get_data"
    assert parsed["hourly"] == [[1791331200, 0.25], [1791334800, 0]]
