"""Tests for scout.py, the stand-in site search of the Eifel-Joe#61 live verification (spec §10.2)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

import scout

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def rows(rate_at, first=-2, last=72):
    """Hourly rows [unix, mm] for stamps NOW + k h; each value covers the hour ending at its stamp."""
    return [[int((NOW + k * H).timestamp()), rate_at(k)] for k in range(first, last + 1)]


def series(rate_at):
    return scout.o1.hourly_series(rows(rate_at))


def test_a_dry_site_fails():
    assert scout.assess(series(lambda k: 0.0), NOW)["ok"] is False


def test_rain_today_and_a_dry_tomorrow_passes():
    # 1 mm/h over (NOW, NOW+12h]: the weakest start is NOW+8h with 4 mm left -> reserve 4 - 2 = 2
    result = scout.assess(series(lambda k: 1.0 if 1 <= k <= 12 else 0.0), NOW)
    assert result["ok"] is True
    assert result["reserve"] == pytest.approx(2.0)


def test_more_rain_tomorrow_counts_as_a_contrast_too():
    # 0.25 mm/h today, 1 mm/h tomorrow: day 1 holds 6..12 mm, day 2 holds 24 mm -> reserve 6 - 2 = 4
    result = scout.assess(series(lambda k: 0.25 if 1 <= k <= 24 else (1.0 if 25 <= k <= 56 else 0.0)), NOW)
    assert result["ok"] is True
    assert result["reserve"] == pytest.approx(4.0)


def test_steady_rain_fails_on_the_plus_one_day_gap():
    result = scout.assess(series(lambda k: 1.0), NOW)
    assert result["ok"] is False
    assert result["reserve"] == pytest.approx(-0.5)


def test_without_a_t1_contrast_the_site_fails():
    # 4 mm in (NOW+20h, NOW+24h]: every start up to +8 h carries, but each T1 in [+1 h, +20 h] sees the same 4 mm
    result = scout.assess(series(lambda k: 1.0 if 21 <= k <= 24 else 0.0), NOW)
    assert result["ok"] is False
    assert result["reserve"] == pytest.approx(-0.5)


def test_check_reads_a_series_file(tmp_path, capsys):
    path = tmp_path / "doc.series.json"
    path.write_text(json.dumps({"logged_at": "x", "method": "get_data",
                                "hourly": rows(lambda k: 1.0 if 1 <= k <= 12 else 0.0)}), encoding="utf-8")
    assert scout.main(["scout.py", "check", str(path), NOW.isoformat()]) == 0
    out = capsys.readouterr().out
    assert "ok=True" in out
    assert "reserve=2.00" in out
