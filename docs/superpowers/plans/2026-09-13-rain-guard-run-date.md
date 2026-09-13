# Regen-Wächter am Datum des Laufs — Implementation Plan (PR 2 von 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Niederschlags-Übersprung wertet den Regen am **Datum des Laufs** (HA-Ortszeit) plus die N-1 folgenden Tage aus, statt ab dem Tag nach dem Lauf — so wird der Regentag selbst geprüft (#137).

**Architecture:** Ein neues HA-freies Modul `forecast_window.py` integriert die stündliche Regenreihe des Clients über die Kalendertage des Laufs und füllt dahinter mit den datierten Tageseinträgen aus PR 1 anteilig auf. `_eval_precipitation` nutzt es mit einem optionalen Laufbeginn, den `async_evaluate_skip_conditions`, die Lauf-Vorschau und der Dashboard-Ausblick durchreichen. `get_forecast_data`, Frost-Wächter und Gewichtung bleiben unverändert.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component, pytest + freezegun, `zoneinfo`.

**Spec:** `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md` (Branch `archive/design-history`).
**Voraussetzung:** Plan `2026-09-13-dated-daily-forecast.md` (PR 1) ist umgesetzt; `FORECAST_DAY_START`/`FORECAST_DAY_END` existieren.

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`.
- Test-Kommando: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint: `uvx black custom_components/irrigation_plus/` und `uvx ruff check custom_components/irrigation_plus/`
- Vorbestands-Fehler der lokalen Suite: **immer gegen die Basis vergleichen.**
- **Mutationsprobe Pflicht**; Wiederherstellen per Byte-Backup + `sha256sum -c`, nicht `git checkout --`.
- Commits englisch mit `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Keine SHAs des eigenen Arbeitsbranches in Kommentaren.
- **Zeitzonen-Falle:** Die Differenz zweier Zeitpunkte mit **derselben** `ZoneInfo` rechnet Python in Wanduhrzeit (`datetime(2026,10,26,tz) - datetime(2026,10,25,tz)` ergibt 24 h, real sind es 25 h). Vor jeder Subtraktion nach UTC umrechnen.
- In Tests ohne `hass`-Fixture ist `dt_util.DEFAULT_TIME_ZONE` UTC. `zoneinfo.ZoneInfo("Europe/Berlin")` ist lokal verfügbar (tzdata installiert).
- `push` und PR nur nach Freigabe. PR 2 erst öffnen, wenn PR 1 gemergt ist; dann auf `upstream/master` neu aufsetzen.

## Dateien

| Datei | Änderung |
|---|---|
| `custom_components/irrigation_plus/forecast_window.py` | **neu**: Fenster, Integration, Auffüllen |
| `custom_components/irrigation_plus/skip_conditions.py` | `_eval_precipitation` am Laufdatum; `run_start` durchreichen; Ausblick; gemeinsame Auswahl des nächsten Laufs |
| `custom_components/irrigation_plus/scheduler.py` | `_projected_skip` reicht `start` durch |
| `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) | `lookahead_help` |
| `tests/test_forecast_window.py` | **neu** |
| `tests/test_precipitation_guard.py` | **neu** |
| `tests/test_skip_run_start_threading.py` | **neu** |

---

### Task 0: Branch und Basis

- [ ] **Step 1: Branch auf PR 1 anlegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --branch
git checkout -b fix/rain-guard-run-date fix/dated-daily-forecast
git log --oneline -3
```
Expected: sauber, HEAD = letzter Commit von PR 1.

- [ ] **Step 2: Basis messen**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/baseline-pr2.txt
tail -1 /d/Entwicklung/HASI/baseline-pr2.txt
```

---

### Task 1: `forecast_window` — Tagesintervalle und Integration der Stundenreihe

**Files:**
- Create: `custom_components/irrigation_plus/forecast_window.py`
- Test: `tests/test_forecast_window.py`

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Datei `tests/test_forecast_window.py`:

```python
"""Expected precipitation over a run's calendar days.

Every number below is hand-computed. Series follow the clients' convention: a
rate in mm/h covering the interval that ENDS at its stamp.
"""

import datetime
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
    stamps = [_utc(2026, 9, 13, 0, 0) + datetime.timedelta(hours=3 * k) for k in range(9)]
    hourly = [(s, 0.0) for s in stamps[:-1]] + [(stamps[-1], 3.0)]
    at = _utc(2026, 9, 12, 22, 0)
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=PLUS2, hourly=hourly, daily=[]
    )
    assert rain.mm == pytest.approx(3.0)
    assert rain.complete is True


def test_a_day_with_the_clocks_going_back_has_25_hours():
    berlin = zoneinfo.ZoneInfo("Europe/Berlin")
    # Local midnight of 2026-10-25 is 24th 22:00Z; the next local midnight is
    # 25th 23:00Z, because the clocks go back an hour that night.
    at = _utc(2026, 10, 24, 22, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=berlin,
        hourly=_hourly(at, 30, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(25.0)
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'custom_components.irrigation_plus.forecast_window'`.

- [ ] **Step 3: Modul schreiben**

Datei `custom_components/irrigation_plus/forecast_window.py`:

```python
"""Expected precipitation over a run's calendar days.

Pure arithmetic -- no Home Assistant import -- so the window can be checked
against hand-computed numbers. The precipitation skip guard hands it the
configured client's hourly precipitation series and its dated daily entries, and
Home Assistant's own time zone decides which calendar days a run covers.

The window starts at the run's own local DATE and spans ``days`` calendar days
from there. The guard used to sum whole days out of ``get_forecast_data``, which
by contract starts tomorrow; evaluated at dispatch on the morning of a run, that
put the first day of the window one day AFTER the run, so the day it rained was
never examined (#137).
"""

from __future__ import annotations

import datetime
from typing import NamedTuple

from .const import FORECAST_DAY_END, FORECAST_DAY_START, MAPPING_PRECIPITATION

_UTC = datetime.timezone.utc
_SECONDS_PER_HOUR = 3600.0
# A covered span within this many seconds of the requested one counts as whole.
_COVERAGE_TOLERANCE_SECONDS = 1.0


class ExpectedRain(NamedTuple):
    """Forecast rain over a run's window, and how much of the window was covered."""

    mm: float
    # The run's own date was fully covered by the hourly series or daily entries.
    run_date_covered: bool
    # Every day of the window was fully covered.
    complete: bool


def _local_midnight_utc(day: datetime.date, tz) -> datetime.datetime:
    # Built in the zone, then converted: subtracting two datetimes that share one
    # ZoneInfo is wall-clock arithmetic and would give a 25-hour day 24 hours.
    return datetime.datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(_UTC)


def window_intervals(run_start, days, tz, evaluated_at):
    """``[(index, start, end)]`` in UTC for the run's local date and the days after it.

    Each day runs from local midnight to the next, so a daylight-saving change
    gives it 23 or 25 hours. The part before ``evaluated_at`` is cut off, because a
    forecast says nothing about hours that have already passed; a day that is
    entirely past is left out. ``index`` 0 is the run's own date.
    """
    run_date = run_start.astimezone(tz).date()
    evaluated = evaluated_at.astimezone(_UTC)
    out = []
    for index in range(max(1, int(days))):
        day = run_date + datetime.timedelta(days=index)
        start = max(_local_midnight_utc(day, tz), evaluated)
        end = _local_midnight_utc(day + datetime.timedelta(days=1), tz)
        if start < end:
            out.append((index, start, end))
    return out


def _overlap_seconds(a_start, a_end, b_start, b_end) -> float:
    return max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())


def _hourly_segments(series):
    """``[(start, end, mm_per_hour)]`` in UTC from a client's ``[(stamp, rate)]``.

    Each rate covers the interval ENDING at its stamp, the convention every client
    hands back. Its length is the gap to the previous stamp; the first sample takes
    the gap to the next one, or one hour when it stands alone. A duplicated stamp
    has no length and is dropped.
    """
    points = sorted(
        (stamp.astimezone(_UTC), float(rate))
        for stamp, rate in (series or [])
        if stamp is not None and rate is not None
    )
    segments = []
    for i, (stamp, rate) in enumerate(points):
        if i > 0:
            span = stamp - points[i - 1][0]
        elif len(points) > 1:
            span = points[1][0] - stamp
        else:
            span = datetime.timedelta(hours=1)
        if span.total_seconds() <= 0:
            continue
        segments.append((stamp - span, stamp, max(0.0, rate)))
    return segments


def _dated_entries(daily):
    """``[(start, end, mm)]`` in UTC for daily entries that carry their span."""
    out = []
    for entry in daily or []:
        start = entry.get(FORECAST_DAY_START)
        end = entry.get(FORECAST_DAY_END)
        mm = entry.get(MAPPING_PRECIPITATION)
        if start is None or end is None or mm is None:
            continue
        start, end = start.astimezone(_UTC), end.astimezone(_UTC)
        if end <= start:
            continue
        out.append((start, end, float(mm)))
    return out


def expected_rain(*, run_start, evaluated_at, days, tz, hourly, daily) -> ExpectedRain:
    """Forecast precipitation on the run's local date and the ``days - 1`` after it.

    The hourly series is integrated wherever it reaches. Beyond its last stamp the
    dated daily entries fill in, each counted by the share of its own span that
    falls inside the window -- a UTC-day entry thus contributes to a local date in
    proportion to their overlap. Coverage is reported per day so the caller can
    refuse to decide on a run date nothing forecast.
    """
    intervals = window_intervals(run_start, days, tz, evaluated_at)
    segments = _hourly_segments(hourly)
    entries = _dated_entries(daily)
    series_start = segments[0][0] if segments else None
    series_end = segments[-1][1] if segments else None

    total = 0.0
    run_date_covered = True
    complete = True
    for index, start, end in intervals:
        requested = (end - start).total_seconds()
        covered = 0.0
        for seg_start, seg_end, rate in segments:
            total += rate * _overlap_seconds(start, end, seg_start, seg_end) / (
                _SECONDS_PER_HOUR
            )
        if segments:
            covered += _overlap_seconds(start, end, series_start, series_end)
        tail_start = max(start, series_end) if series_end is not None else start
        if tail_start < end:
            for entry_start, entry_end, mm in entries:
                seconds = _overlap_seconds(tail_start, end, entry_start, entry_end)
                if seconds <= 0:
                    continue
                total += mm * seconds / (entry_end - entry_start).total_seconds()
                covered += seconds
        if covered < requested - _COVERAGE_TOLERANCE_SECONDS:
            complete = False
            if index == 0:
                run_date_covered = False
    return ExpectedRain(total, run_date_covered, complete)
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 4 PASS.

- [ ] **Step 5: Mutationsproben**

1. In `window_intervals` `start = max(_local_midnight_utc(day, tz), evaluated)` → `start = _local_midnight_utc(day, tz)` → `test_the_rest_of_the_run_day_counts_from_the_evaluation` FAIL (24 statt 18).
2. `run_date = run_start.astimezone(tz).date()` → `run_date = run_start.astimezone(_UTC).date()` → `test_a_three_hourly_slot_across_midnight_is_split` FAIL (das Laufdatum wird zum UTC-12. statt zum Orts-13.).
3. In `_local_midnight_utc` `.astimezone(_UTC)` entfernen (Rückgabe bleibt in `tz`) → `test_a_day_with_the_clocks_going_back_has_25_hours` FAIL, weil Subtraktion und Vergleich dann in Wanduhrzeit laufen.
4. In `_hourly_segments` `span = stamp - points[i - 1][0]` → `span = datetime.timedelta(hours=1)` → `test_a_three_hourly_slot_across_midnight_is_split` FAIL (0 statt 3).
Jeweils wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_forecast_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/forecast_window.py tests/test_forecast_window.py
git commit -F - <<'EOF'
feat(forecast): integrate expected rain over a run's calendar days

A pure helper that takes a client's hourly precipitation series and returns the
rain expected on the run's local date and the days after it. Each day runs from
local midnight to the next, converted to UTC before any arithmetic so a
daylight-saving day keeps its 23 or 25 hours; hours already past are cut off,
since a forecast says nothing about them.

Nothing calls it yet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: `forecast_window` — Auffüllen mit Tageseinträgen und Abdeckung

**Files:**
- Modify: nichts in Produktion (Code steht seit Task 1)
- Test: `tests/test_forecast_window.py`

- [ ] **Step 1: Tests anhängen**

```python
def test_daily_totals_fill_beyond_the_end_of_the_hourly_series():
    at = _utc(2026, 9, 13, 0, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=3,
        tz=UTC,
        # 36 hours of 1 mm/h: the whole 13th and the first half of the 14th
        hourly=_hourly(at, 36, 1.0),
        daily=[_day(_utc(2026, 9, 14), 48.0), _day(_utc(2026, 9, 15), 10.0)],
    )
    # 24 (13th) + 12 (14th, hourly) + 24 (half of the 14th's 48) + 10 (15th)
    assert rain.mm == pytest.approx(70.0)
    assert rain.complete is True


def test_without_an_hourly_series_the_run_date_is_reported_uncovered():
    # At dispatch get_forecast_data holds no entry for today, so without an hourly
    # series nothing forecasts the run's own date.
    at = _utc(2026, 9, 13, 6, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=2,
        tz=UTC,
        hourly=[],
        daily=[_day(_utc(2026, 9, 14), 5.0)],
    )
    assert rain.mm == pytest.approx(5.0)
    assert rain.run_date_covered is False
    assert rain.complete is False


def test_a_utc_day_entry_counts_against_a_local_date_by_overlap():
    # Local 13th (+02) is 12th 22:00Z .. 13th 22:00Z; the UTC-day entry for the
    # 13th overlaps it for 22 of its 24 hours.
    at = _utc(2026, 9, 12, 22, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=PLUS2,
        hourly=[],
        daily=[_day(_utc(2026, 9, 13), 24.0)],
    )
    assert rain.mm == pytest.approx(22.0)
    assert rain.run_date_covered is False


def test_an_entry_for_a_day_already_past_contributes_nothing():
    # A daily list parsed before midnight and served from cache afterwards still
    # holds yesterday's entry. Its span no longer meets the window, so it cannot
    # be mistaken for today by position.
    at = _utc(2026, 9, 13, 6, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=UTC,
        hourly=_hourly(_utc(2026, 9, 13, 0, 0), 24, 0.0),
        daily=[_day(_utc(2026, 9, 12), 50.0)],
    )
    assert rain.mm == pytest.approx(0.0)
    assert rain.complete is True
```

- [ ] **Step 2: Tests laufen (Code steht bereits) — Erwartung grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 8 PASS. Da der Code schon existiert, **ist die Mutationsprobe hier der Beweis, dass die Tests beißen**:

- [ ] **Step 3: Mutationsproben**

1. `tail_start = max(start, series_end) if series_end is not None else start` → `tail_start = start` → `test_daily_totals_fill_beyond_the_end_of_the_hourly_series` FAIL (Doppelzählung).
2. `if index == 0:` → `if index == 1:` → `test_without_an_hourly_series_the_run_date_is_reported_uncovered` FAIL.
3. `total += mm * seconds / (entry_end - entry_start).total_seconds()` → `total += mm` → `test_a_utc_day_entry_counts_against_a_local_date_by_overlap` FAIL (24 statt 22).
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 4: Commit**

```bash
uvx black tests/test_forecast_window.py
git add tests/test_forecast_window.py
git commit -F - <<'EOF'
test(forecast): pin the daily fill-in and the coverage report

Beyond the hourly series the dated daily entries fill in by the share of their
span inside the window, which is also how a UTC-day entry is weighed against a
local date. A run date nothing forecasts is reported as uncovered.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: `_eval_precipitation` am Datum des Laufs

**Files:**
- Modify: `custom_components/irrigation_plus/skip_conditions.py` (`_eval_precipitation`, Import)
- Test: `tests/test_precipitation_guard.py` (neu)

- [ ] **Step 1: Fehlschlagende Tests schreiben — der echte Fall vom 12./13. September**

Datei `tests/test_precipitation_guard.py`:

```python
"""The precipitation skip guard examines the run's own date.

Rebuilt from the live case behind #137. Forecast: 2.15 mm on the 13th, window 1
day, threshold 2 mm. The guard used to read the day AFTER the run: it skipped
the dry 12th for the 13th's rain and let the 13th water, because by then it was
looking at the 14th. Times are UTC; in these tests Home Assistant's zone is UTC.
"""

import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from freezegun import freeze_time

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.skip_conditions import SKIP_PRECIPITATION

UTC = datetime.timezone.utc
RAIN_AT = datetime.datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def _daily():
    def day(d, mm):
        start = datetime.datetime(2026, 9, d, tzinfo=UTC)
        return {
            const.FORECAST_DAY_START: start,
            const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
            const.MAPPING_PRECIPITATION: mm,
        }

    return [day(13, 2.15), day(14, 0.0)]


def _hourly():
    first = datetime.datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    out = []
    for h in range(1, 73):
        stamp = first + datetime.timedelta(hours=h)
        out.append((stamp, 2.15 if stamp == RAIN_AT else 0.0))
    return out


def _coordinator(client):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()

    async def run_executor(func, *args):
        return func(*args)

    hass.async_add_executor_job = run_executor
    coord.hass = hass
    coord._WeatherServiceClient = client
    return coord


def _client():
    return SimpleNamespace(
        get_forecast_data=lambda: _daily(),
        get_hourly_precipitation_forecast=lambda: _hourly(),
    )


def _config(enabled=True):
    return {
        const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION: enabled,
        const.CONF_PRECIPITATION_THRESHOLD_MM: 2,
        const.CONF_PRECIPITATION_FORECAST_DAYS: 1,
        const.CONF_USE_WEATHER_SERVICE: True,
    }


@freeze_time("2026-09-12 06:19:00")
async def test_the_dry_day_before_the_rain_is_not_skipped():
    result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["id"] == SKIP_PRECIPITATION
    assert result["available"] is True
    assert result["observed"] == 0.0
    assert result["would_skip"] is False


@freeze_time("2026-09-13 06:20:00")
async def test_the_rain_day_itself_is_skipped():
    result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


@freeze_time("2026-09-12 20:00:00")
async def test_the_evening_outlook_for_tomorrow_looks_at_tomorrow():
    run_start = datetime.datetime(2026, 9, 13, 6, 20, tzinfo=UTC)
    result = await _coordinator(_client())._eval_precipitation(_config(), run_start)
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


@freeze_time("2026-09-13 06:20:00")
async def test_a_client_without_an_hourly_series_cannot_decide_the_run_date():
    client = SimpleNamespace(get_forecast_data=lambda: _daily()[1:])
    result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_disabled_is_a_noop():
    result = await _coordinator(_client())._eval_precipitation(_config(enabled=False))
    assert result["enabled"] is False
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_no_weather_client_is_unavailable():
    result = await _coordinator(None)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py -p _local_socket_unblock -q`
Expected: FAIL — `test_the_dry_day_before_the_rain_is_not_skipped` (heute `observed 2.15`, `would_skip True`), `test_the_rain_day_itself_is_skipped` (heute `0.0`), `test_the_evening_outlook_…` (`TypeError`: zu viele Argumente), `test_a_client_without_an_hourly_series…` (heute `available True`).

- [ ] **Step 3: Implementieren**

Import in `skip_conditions.py` ergänzen (nach `from . import const`):

```python
from .forecast_window import expected_rain
```

`_eval_precipitation` vollständig ersetzen durch:

```python
    async def _eval_precipitation(self, config, run_start=None) -> dict:
        """Structured precipitation-forecast guard over the run's own calendar days.

        Wurzel: this summed whole days out of ``get_forecast_data``, which by
          contract starts TOMORROW, while the guard runs at dispatch on the morning
          of the run. The window therefore began the day after the run: a dry day
          was skipped for the next day's rain, and the rain day itself watered
          (#137).
        Fix-Logik: the window starts at ``run_start``'s local DATE and spans
          ``precipitation_forecast_days`` calendar days. The run's date comes from
          the client's hourly precipitation series, which every client serves; the
          days beyond it fill in from the dated daily entries. Hours before the
          evaluation are not forecast and do not count.
        NOT-TO-DO: do not make ``get_forecast_data`` include today to get at the
          run's date. The ET averages and the freeze guard's "coming night" both
          depend on it excluding today. And do not derive the date from a client's
          own clock (OWM uses ``utcnow().date()``): Home Assistant's zone decides.
        siehe tests/test_precipitation_guard.py, tests/test_forecast_window.py
        """
        threshold = config.get(
            const.CONF_PRECIPITATION_THRESHOLD_MM,
            const.CONF_DEFAULT_PRECIPITATION_THRESHOLD_MM,
        )
        result = {
            "id": SKIP_PRECIPITATION,
            "enabled": bool(
                config.get(
                    const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION,
                    const.CONF_DEFAULT_SKIP_IRRIGATION_ON_PRECIPITATION,
                )
            ),
            "would_skip": False,
            "available": False,
            "observed": None,
            "threshold": threshold,
        }
        if not result["enabled"]:
            return result
        use_weather_service = config.get(
            const.CONF_USE_WEATHER_SERVICE, const.CONF_DEFAULT_USE_WEATHER_SERVICE
        )
        client = self._WeatherServiceClient
        if not use_weather_service or client is None:
            return result
        try:
            # Daily first: the hourly accessor reads the document it fetches.
            daily = await self.hass.async_add_executor_job(client.get_forecast_data)
            hourly = None
            if hasattr(client, "get_hourly_precipitation_forecast"):
                hourly = await self.hass.async_add_executor_job(
                    client.get_hourly_precipitation_forecast
                )
            if not daily and not hourly:
                return result
            days = max(
                1,
                config.get(
                    const.CONF_PRECIPITATION_FORECAST_DAYS,
                    const.CONF_DEFAULT_PRECIPITATION_FORECAST_DAYS,
                ),
            )
            now = dt_util.utcnow()
            start = dt_util.as_utc(run_start) if run_start is not None else now
            rain = expected_rain(
                run_start=start,
                evaluated_at=now,
                days=days,
                tz=dt_util.DEFAULT_TIME_ZONE,
                hourly=hourly,
                daily=daily,
            )
            if not rain.run_date_covered:
                _LOGGER.debug(
                    "Skip preview: precipitation forecast does not cover the run's "
                    "date; not deciding on it"
                )
                return result
            if not rain.complete:
                _LOGGER.debug(
                    "Skip preview: precipitation forecast covers only part of the "
                    "%s-day window",
                    days,
                )
            result["available"] = True
            result["observed"] = round(rain.mm, 2)
            result["would_skip"] = rain.mm >= threshold
        except Exception as e:  # noqa: BLE001 — preview must never raise
            _LOGGER.debug("Skip preview: precipitation eval failed: %s", e)
        return result
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py tests/test_forecast_window.py tests/test_coordinator_mixins.py -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 5: Mutationsproben — der Regressions-Pin**

1. Das alte Verhalten nachbauen: `start = dt_util.as_utc(run_start) if run_start is not None else now` → `start = (dt_util.as_utc(run_start) if run_start is not None else now) + datetime.timedelta(days=1)` (dafür `import datetime` temporär ergänzen) → `test_the_dry_day_before_the_rain_is_not_skipped` UND `test_the_rain_day_itself_is_skipped` FAIL.
2. `if not rain.run_date_covered:` → `if False:` → `test_a_client_without_an_hourly_series_cannot_decide_the_run_date` FAIL.
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_precipitation_guard.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/skip_conditions.py tests/test_precipitation_guard.py
git commit -F - <<'EOF'
fix(skip): examine rain on the run's own date, not the day after it

The precipitation guard summed whole days out of get_forecast_data, which by
contract starts tomorrow, while it runs at dispatch on the morning of the run.
Its window therefore began one day AFTER the run. On a live install that meant
skipping a dry day for the next day's forecast rain, then watering on the rain
day itself because by then the guard was looking at the day after.

The window now starts at the run's local date and spans the configured number
of calendar days. The run's date comes from the client's hourly precipitation
series, which all four clients serve; the days beyond it fill in from the dated
daily entries. Hours already past are not forecast and do not count. Without an
hourly series nothing forecasts the run's date, so the guard declines to decide
rather than skip on nothing.

get_forecast_data still excludes today: the ET averages and the freeze guard's
"coming night" depend on it. Forecast weighting is unchanged here.

Refs #137.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Laufbeginn durchreichen — Auswertung, Vorschau, Ausblick

**Files:**
- Modify: `custom_components/irrigation_plus/skip_conditions.py` (`async_evaluate_skip_conditions`, `async_get_irrigation_outlook`, `_project_days_between_to_next_run`, neue statische Methode `_next_irrigate_run_utc`)
- Modify: `custom_components/irrigation_plus/scheduler.py` (`_projected_skip`)
- Test: `tests/test_skip_run_start_threading.py` (neu)

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Datei `tests/test_skip_run_start_threading.py`:

```python
"""The run's start reaches the precipitation guard from every place that asks.

The guard's window starts at the run's local date, so each caller has to say
which run it is asking about: dispatch (now), the schedule projection (its
planned start) and the dashboard outlook (the next scheduled irrigate run).
"""

import datetime
from unittest.mock import AsyncMock, Mock

import homeassistant.util.dt as dt_util

from custom_components.irrigation_plus import SmartIrrigationCoordinator
from custom_components.irrigation_plus.scheduler import RecurringScheduleManager

UTC = datetime.timezone.utc
START = datetime.datetime(2026, 9, 13, 4, 20, tzinfo=UTC)


def _off(check_id):
    return {"id": check_id, "enabled": False, "would_skip": False}


async def test_evaluation_hands_the_run_start_to_the_precipitation_guard():
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.store = Mock()
    coord.store.async_get_config = AsyncMock(return_value={})
    coord._eval_precipitation = AsyncMock(return_value=_off("precipitation"))
    coord._eval_days_between = AsyncMock(return_value=_off("days_between"))
    coord._eval_temp = AsyncMock(return_value=_off("temperature"))
    coord._eval_wind = AsyncMock(return_value=_off("wind"))
    coord._eval_freeze = AsyncMock(return_value=_off("freeze"))
    coord._eval_rain_sensor = AsyncMock(return_value=_off("rain_sensor"))

    await coord.async_evaluate_skip_conditions(run_start=START)

    assert coord._eval_precipitation.await_args.args == ({}, START)


async def test_the_schedule_projection_asks_about_its_planned_start():
    manager = RecurringScheduleManager.__new__(RecurringScheduleManager)
    manager.coordinator = Mock()
    manager.coordinator.async_evaluate_skip_conditions = AsyncMock(
        return_value={"would_skip": False, "checks": []}
    )
    manager.coordinator._project_days_between_to_next_run = Mock()
    manager.coordinator._rain_delay_until_dt = Mock(return_value=None)

    await manager._projected_skip(START)

    assert manager.coordinator.async_evaluate_skip_conditions.await_args.kwargs == {
        "run_start": START
    }


async def test_the_outlook_asks_about_the_next_irrigate_run():
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.store = Mock()
    coord.store.async_get_config = AsyncMock(return_value={})
    coord.recurring_schedule_manager = Mock()
    coord.recurring_schedule_manager.async_get_upcoming_runs = AsyncMock(
        return_value=[
            {"action": "calculate", "next_run_utc": "2026-09-12T21:00:00+00:00"},
            {"action": "irrigate", "next_run_utc": START.isoformat()},
        ]
    )
    coord.async_evaluate_skip_conditions = AsyncMock(
        return_value={"would_skip": False, "checks": []}
    )
    coord.async_get_cached_zone_estimates = AsyncMock(return_value={})
    coord.get_zone_faults = Mock(return_value={})
    coord.get_zone_skips = Mock(return_value={})
    coord.get_active_runs = Mock(return_value={})

    await coord.async_get_irrigation_outlook()

    assert coord.async_evaluate_skip_conditions.await_args.kwargs == {
        "run_start": dt_util.parse_datetime(START.isoformat())
    }
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_skip_run_start_threading.py -p _local_socket_unblock -q`
Expected: 3 FAIL (`TypeError: unexpected keyword argument 'run_start'` bzw. `kwargs == {}`).

- [ ] **Step 3: `async_evaluate_skip_conditions` erweitern**

In `skip_conditions.py` ersetzen:

```python
    async def async_evaluate_skip_conditions(self) -> dict:
```

durch:

```python
    async def async_evaluate_skip_conditions(self, run_start=None) -> dict:
```

im Docstring vor der schließenden `"""` ergänzen:

```python
        ``run_start`` is the run being asked about. The precipitation guard's
        window starts at its local date; without it the guard assumes now,
        which is right at dispatch and wrong for any preview of a later run.
```

und in der Liste `checks = [` ersetzen:

```python
            await self._eval_precipitation(config),
```

durch:

```python
            await self._eval_precipitation(config, run_start),
```

- [ ] **Step 4: Gemeinsame Auswahl des nächsten Laufs**

In `skip_conditions.py` direkt vor `    @staticmethod\n    def _project_days_between_to_next_run(` einfügen:

```python
    @staticmethod
    def _next_irrigate_run_utc(upcoming: list):
        """The start of the next scheduled irrigate run, or None.

        ``upcoming`` is sorted by ``next_run_utc``; the first irrigate entry with a
        start is the next one. Shared by every preview that projects a run-time
        decision, so they cannot pick different runs.
        """
        next_run = next(
            (
                r["next_run_utc"]
                for r in upcoming
                if r.get("action") == "irrigate" and r.get("next_run_utc")
            ),
            None,
        )
        return dt_util.parse_datetime(next_run) if next_run else None

```

In `_project_days_between_to_next_run` ersetzen:

```python
        next_run = next(
            (
                r["next_run_utc"]
                for r in upcoming
                if r.get("action") == "irrigate" and r.get("next_run_utc")
            ),
            None,
        )
        if not next_run:
            return
        run_dt = dt_util.parse_datetime(next_run)
        if run_dt is None:
            return
```

durch:

```python
        run_dt = SkipConditionsMixin._next_irrigate_run_utc(upcoming)
        if run_dt is None:
            return
```

- [ ] **Step 5: Ausblick fragt nach dem nächsten Lauf**

In `async_get_irrigation_outlook` ersetzen:

```python
        config = await self.store.async_get_config()
        skip_preview = await self.async_evaluate_skip_conditions()
        upcoming = await self.recurring_schedule_manager.async_get_upcoming_runs()
```

durch:

```python
        config = await self.store.async_get_config()
        upcoming = await self.recurring_schedule_manager.async_get_upcoming_runs()
        # The precipitation guard's window starts at the run's date, so ask about
        # the next run rather than about now: opened in the evening, "now" would
        # examine today for a run that waters tomorrow.
        skip_preview = await self.async_evaluate_skip_conditions(
            run_start=self._next_irrigate_run_utc(upcoming)
        )
```

- [ ] **Step 6: Vorschau reicht ihren Start durch**

In `scheduler.py`, `_projected_skip`, ersetzen:

```python
        evaluation = await self.coordinator.async_evaluate_skip_conditions()
```

durch:

```python
        # The precipitation guard's window starts at the run's date, so this
        # projection asks about ITS start, not about now.
        evaluation = await self.coordinator.async_evaluate_skip_conditions(
            run_start=start
        )
```

- [ ] **Step 7: Tests grün, benachbarte Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_skip_run_start_threading.py tests/test_days_between_preview.py tests/test_precipitation_guard.py tests/test_next_irrigation_sensor.py -p _local_socket_unblock -q`
Expected: alle PASS (Teardown-Errors der lokalen Env zählen nicht; mit Basis vergleichen).

- [ ] **Step 8: Mutationsproben**

1. `await self._eval_precipitation(config, run_start),` → `await self._eval_precipitation(config),` → erster Test FAIL.
2. In `_projected_skip` `run_start=start` entfernen → zweiter Test FAIL.
3. Im Ausblick `run_start=self._next_irrigate_run_utc(upcoming)` entfernen → dritter Test FAIL.
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 9: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_skip_run_start_threading.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/scheduler.py tests/test_skip_run_start_threading.py
git commit -F - <<'EOF'
fix(skip): previews ask the precipitation guard about the run they preview

The guard's window now starts at the run's date, so every caller has to name
the run. Dispatch still means now. The schedule projection passes its planned
start, and the dashboard outlook passes the next scheduled irrigate run -- opened
in the evening, "now" would have examined today for a run that waters tomorrow.

The outlook and the days-between projection now share one selection of the
next irrigate run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Hilfetext in allen acht Sprachen

**Files:**
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json` (Schlüssel `lookahead_help`)

- [ ] **Step 1: Texte ersetzen (Skript, schreibt über temporäre Datei)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
./.venv/Scripts/python.exe - <<'PY'
import json, os, pathlib
base = pathlib.Path("custom_components/irrigation_plus/frontend/localize/languages")
new = {
    "en": "How many days of forecast to add up when checking for rain, starting with the day the run takes place. 1 = the day of the run, 2 = that day and the next, and so on. Hours that have already passed are not forecast and do not count.",
    "de": "Wie viele Vorhersagetage beim Regen-Check zusammengezählt werden, beginnend mit dem Tag des Laufs. 1 = der Tag des Laufs, 2 = dieser Tag und der nächste usw. Bereits vergangene Stunden werden nicht vorhergesagt und zählen nicht mit.",
    "es": "Cuántos días de previsión se suman al comprobar la lluvia, empezando por el día en que se realiza el riego. 1 = el día del riego, 2 = ese día y el siguiente, etc. Las horas ya pasadas no se prevén y no cuentan.",
    "fr": "Nombre de jours de prévision additionnés lors de la vérification de la pluie, en commençant par le jour de l'arrosage. 1 = le jour de l'arrosage, 2 = ce jour et le suivant, etc. Les heures déjà écoulées ne sont pas prévues et ne comptent pas.",
    "it": "Quanti giorni di previsione sommare nel controllo della pioggia, a partire dal giorno dell'irrigazione. 1 = il giorno dell'irrigazione, 2 = quel giorno e il successivo, e così via. Le ore già trascorse non sono previste e non vengono contate.",
    "nl": "Hoeveel verwachtingsdagen worden opgeteld bij de regencontrole, te beginnen met de dag waarop wordt beregend. 1 = de dag van de beregening, 2 = die dag en de volgende, enzovoort. Uren die al voorbij zijn, worden niet verwacht en tellen niet mee.",
    "no": "Hvor mange varseldøgn som summeres ved regnsjekken, fra og med dagen vanningen skjer. 1 = vanningsdagen, 2 = den dagen og neste, og så videre. Timer som allerede er passert, varsles ikke og telles ikke med.",
    "sk": "Koľko dní predpovede sa spočíta pri kontrole dažďa, počnúc dňom zavlažovania. 1 = deň zavlažovania, 2 = tento deň a nasledujúci atď. Hodiny, ktoré už uplynuli, sa nepredpovedajú a nezapočítavajú sa.",
}
for lang, text in new.items():
    p = base / f"{lang}.json"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if l.lstrip().startswith('"lookahead_help"')]
    assert len(hits) == 1, (lang, hits)
    i = hits[0]
    indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
    ending = "," if lines[i].rstrip().endswith(",") else ""
    newline = "\r\n" if lines[i].endswith("\r\n") else "\n"
    lines[i] = f'{indent}"lookahead_help": {json.dumps(text, ensure_ascii=False)}{ending}{newline}'
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(lines), encoding="utf-8", newline="")
    os.replace(tmp, p)
    json.loads(p.read_text(encoding="utf-8"))
    print(lang, "ok")
PY
```
Expected: acht Zeilen `<lang> ok`.

- [ ] **Step 2: Alte Aussage ist überall weg**

```bash
grep -n "\"lookahead_help\"" custom_components/irrigation_plus/frontend/localize/languages/*.json | grep -iE "tomorrow|morgen \(|mañana|demain|domani|morgen \(vandaag|i morgen|zajtraj" || echo "keine alte Formulierung mehr"
```
Expected: `keine alte Formulierung mehr`.

- [ ] **Step 3: i18n-Vollständigkeit**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_i18n_completeness.py -p _local_socket_unblock -q`
Expected: PASS.

- [ ] **Step 4: Frontend-Build, falls Übersetzungen ins Bundle gehen**

```bash
cd custom_components/irrigation_plus/frontend && npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation && git status --short custom_components/irrigation_plus/frontend/dist/
```
Expected: geänderte Bundles; mit `git add -f` stagen (dist ist gitignored).

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/frontend/localize/languages/*.json
git add -f custom_components/irrigation_plus/frontend/dist/
git commit -F - <<'EOF'
i18n(skip): the look-ahead starts with the day of the run

The help text said the window starts tomorrow with today excluded. It now
starts with the run's own date, in all eight catalogues, and says that hours
already past do not count.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Volle Suite, Lint, Geschwister-Prüfung

- [ ] **Step 1: Lint**

```bash
uvx black --check custom_components/irrigation_plus/ tests/
uvx ruff check custom_components/irrigation_plus/
```

- [ ] **Step 2: Suite gegen Basis**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/after-pr2.txt
grep "^FAILED" /d/Entwicklung/HASI/baseline-pr2.txt | sort > /tmp/b2.txt
grep "^FAILED" /d/Entwicklung/HASI/after-pr2.txt | sort > /tmp/a2.txt
diff /tmp/b2.txt /tmp/a2.txt && echo "IDENTISCHE Vorbestands-Fehler"
tail -1 /d/Entwicklung/HASI/baseline-pr2.txt; tail -1 /d/Entwicklung/HASI/after-pr2.txt
```
Expected: identische Fehlernamen; `passed` um +17 höher (8 Fenster, 6 Wächter, 3 Durchreichen).

- [ ] **Step 3: Kein anderer Leser nutzt noch `forecast_data[:days]` für Regen am Laufdatum**

```bash
grep -rn "forecast_data\[:days\]\|fd\[:days\]" custom_components/irrigation_plus/*.py
```
Expected: nur `calculation.py` (Gewichtung) — **bewusst unverändert** laut Spec; im PR-Text und auf #137 benennen.

- [ ] **Step 4: Keine Branch-SHAs in Kommentaren**

```bash
git diff upstream/master --unified=0 -- custom_components/ | grep -E "^\+.*\b[0-9a-f]{8}\b" || echo "keine SHAs"
```

---

### Task 7: Texte nach außen (Freigabe nötig)

- [ ] **Step 1: PR-Text entwerfen** (englisch): Wurzel, der Live-Fall als Tabelle, JustChrs Form („keyed on the run's date"), was das Stundenfenster und das Auffüllen tun, die Annahme zu vergangenen Stunden, Tests mit Mutationstabelle, Suite-Zahlen, „Forecast weighting unchanged (same blind spot under `before_run`)". `Closes #137`. Ende mit `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2: Kommentar für #137 entwerfen**: die Open-Meteo-Verschiebung (`past_days=1`, PR 1), der Satz zur Gewichtung unter `before_run`, Verweis auf beide PRs.
- [ ] **Step 3: Beide Texte im Chat zeigen, Freigabe abwarten.**
- [ ] **Step 4: Erst nach Merge von PR 1:** auf `upstream/master` neu aufsetzen, Suite erneut, dann `git push -u origin fix/rain-guard-run-date` und `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/rain-guard-run-date --title "Examine rain on the run's own date, not the day after it" --body-file <datei>`.
