# Regen-Wächter am Datum des Laufs — Implementation Plan (PR 2 von 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Revision 2026-09-15.** Vor der Ausführung zweimal geprüft.
> 1. **Prüfung gegen den Code nach PR 0 (#144) und PR 1 (#145):** 22 Agenten, schwere Befunde gegengeprüft. Drei Stellen hätten den Plan scheitern lassen: ein alter Test in `test_init.py`, die Testzeitzone US/Pacific statt UTC und eine Mutationsprobe ohne Wirkung. Dazu kamen Rechenfehler im Helfer: Lücken, ein gescheiterter Abruf und ein doppelt gezählter OWM-Tag.
> 2. **Probelauf dieses Plans in Wegwerf-Worktrees:** Tasks 1–7 und 9 wurden ausgeführt, jede Rot/Grün- und Mutationsaussage wurde nachgemessen. Gefunden wurden ruff B905 (`zip` ohne `strict=`), eine prettier-Zeile, die `npm run build` bricht, und die OWM-Doppelzählung an der Gleichheitsgrenze. Alles hier eingearbeitet.
>
> **User-Entscheidungen 2026-09-15:** Abendläufe wie entschieden bauen und offenlegen; Hilfetext je Modus getrennt; Met-Office-Dokumentwahl als eigener Commit in diesem PR. Zeitzone HA-Prod per MCP geprüft: `Europe/Berlin`. Nachtrag im Spec.

**Goal:** Der Niederschlags-Übersprung wertet den Regen am **Datum des Laufs** (HA-Ortszeit) plus die N-1 folgenden Tage aus, statt ab dem Tag nach dem Lauf — so wird der Regentag selbst geprüft (#137).

**Architecture:** Ein neues HA-freies Modul `forecast_window.py` integriert die stündliche Regenreihe des Clients über die Kalendertage des Laufs. Datierte Tageseinträge, die erst nach dem Ende der Reihe beginnen, füllen anteilig auf. Das Modul enthält auch den einzigen Leser der Tagesspanne (`day_span`), den das Panel mitbenutzt. `_eval_precipitation` nutzt das Modul mit einem optionalen Laufbeginn, den Vorschau und Ausblick immer mitgeben; nur der Dispatch lässt ihn weg. Met Office liest künftig das aktuellere seiner zwei Dokumente. `get_forecast_data`, Frost-Wächter und Gewichtung bleiben unverändert; der Hilfetext wird je Modus getrennt.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component, pytest + freezegun, `zoneinfo`; Frontend Lit + vitest + eslint/prettier, Rollup-Build.

**Spec:** `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md` (Branch `archive/design-history`), inkl. Nachtrag 2026-09-15.
**Basis:** Branch `fix/rain-guard-run-date`, angelegt auf `fix/dated-daily-forecast` @ `f14ebbdd` (PR 1, gestapelt auf PR 0).

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`. Gearbeitet wird im Hauptbaum auf `fix/rain-guard-run-date`.
- Test-Kommando: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint: `uvx black custom_components/irrigation_plus/` und `uvx ruff check custom_components/irrigation_plus/`. Die ruff-Konfiguration (`pyproject.toml`) wählt u. a. `B` und `I`, also gelten `B905` (`zip` ohne `strict=`) und die Import-Reihenfolge.
- Frontend (im Ordner `custom_components/irrigation_plus/frontend`): `npx vitest run <pfad>`, `npm run lint`, Build `npm ci && npm run build`. **Der Build läuft `lint` vor `rollup`** — eine prettier-Beanstandung verhindert das Bündeln, und die CI (`frontend.yml`) baut genauso.
- Die lokale Suite hat Vorbestandsfehler (7 failed / 320 errors) — **immer gegen die Basis vergleichen**, nie gegen null. Teardown-Errors „Lingering timer" sind lokal bekannt.
- **🔴 Zeitzone in Tests:** `tests/conftest.py` zieht per autouse `enable_custom_integrations` → `hass`, und das setzt `US/Pacific`. **Jeder** Test läuft damit in US/Pacific, auch ohne `hass`-Parameter. Wer eine Zone braucht, fordert ein Fixture **per Namen** an (läuft nach `hass`), setzt sie mit `dt_util.set_default_time_zone` und stellt sie im `finally` zurück. Nie `monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", …)`.
- **Zeitzonen-Arithmetik:** Die Differenz zweier Zeitpunkte mit **derselben** `ZoneInfo` rechnet Python in Wanduhrzeit (25-h-Tag = 24 h). Vor jeder Subtraktion nach UTC umrechnen. `==` auf aware datetimes vergleicht nur den Zeitpunkt; einen Offset eigens mit `utcoffset()` festnageln.
- **NaN:** `max(0.0, nan)` ergibt `0.0` (Vergleiche mit NaN sind falsch). Deshalb wird `math.isfinite` VOR jedem `max` geprüft.
- **Mutationsprobe Pflicht.** Vorgehen je Probe, mit ausgeschriebenen Pfaden (keine Shell-Variablen in Befehlen mit git/pytest):
  1. `cp <datei> /d/Entwicklung/HASI/pr2-work/mut/<name>.bak` und `sha256sum <datei> > …/mut/<name>.sha`
  2. Mutation mit dem Edit-Tool setzen, genannten Test laufen lassen (muss FAIL)
  3. `cp …/mut/<name>.bak <datei> && sha256sum -c …/mut/<name>.sha`

  **Nicht** `git checkout --` / `git stash` (revertiert Committetes nicht). Python-Hilfsskripte nie im Ordner `irrigation_plus` starten (dessen `datetime.py` verdeckt das Standardmodul).
- Kommentare für nicht-triviale Stellen im Format des Skills `code-doku`: `Wurzel:` / `Fix-Logik:` / `NOT-TO-DO:` / `siehe` (so auch upstream, z. B. `distributor.py`).
- Commits englisch, Ende `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, mehrzeilig per `git commit -F - <<'EOF' … EOF`. Gezielt stagen.
- Keine SHAs des eigenen Arbeitsbranches in Code-Kommentaren.
- `push`, PR, Kommentare nach außen und HA-Neustarts **nur nach Freigabe im Chat** (Tasks 11, 12).

## Dateien

| Datei | Änderung | Task |
|---|---|---|
| `custom_components/irrigation_plus/forecast_window.py` | **neu**: Tagesintervalle, Integration, Lücken, Auffüllen, `day_span` | 1–3 |
| `custom_components/irrigation_plus/websockets.py` | Panel liest die Spanne über `day_span`, Docstring | 4 |
| `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py` | beide Stunden-Accessoren lesen das aktuellere Dokument | 5 |
| `custom_components/irrigation_plus/skip_conditions.py` | `_eval_precipitation` am Laufdatum; `run_start`; Ausblick; gemeinsame Auswahl des nächsten Laufs | 6, 7 |
| `custom_components/irrigation_plus/const.py` | Kommentar zu `CONF_PRECIPITATION_FORECAST_DAYS` | 6 |
| `custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py` | Kommentar-Verweis (Z. ~212) | 6 |
| `custom_components/irrigation_plus/scheduler.py` | `_projected_skip` nennt immer einen Zeitpunkt, Docstring | 7 |
| `custom_components/irrigation_plus/frontend/src/views/general/view-general.ts` | Hilfetext nach Modus | 9 |
| `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) | `lookahead_help` → `{skip, water_less}` | 9 |
| `custom_components/irrigation_plus/frontend/dist/*` | neu gebaut, `git add -f` | 9 |
| `docs/configuration-when-to-water.md` (Z. 42), `docs/configuration-weather-location.md` (Z. 26) | je Modus; Chip ≠ Summe der Panel-Zeilen | 9 |
| `tests/test_forecast_window.py` | **neu** (25 Items) | 1–3 |
| `tests/test_websocket_get_weather_forecast.py` | +2 Items | 4 |
| `tests/test_met_office_forecast_document.py` | **neu** (4 Items) | 5 |
| `tests/test_precipitation_guard.py` | **neu** (13 Items) | 6 |
| `tests/test_init.py` | `TestPrecipitationLookAhead` auf Laufdatum umgeschrieben (±0) | 6 |
| `tests/test_skip_run_start_threading.py` | **neu** (5 Items) | 7 |
| `frontend/src/views/general/view-general.test.ts` | +2 vitest-Tests | 9 |

Erwartung am Ende: pytest **+49 passed**, identische FAILED-Namen, Errors unverändert; vitest **+2** (Basis Probelauf: 22 Dateien, 614 passed). Am Endstand nachmessen, nicht wörtlich nehmen.

---

### Task 0: Branch und Basis

- [x] **Step 1: Branch auf PR 1 angelegt** — `fix/rain-guard-run-date` @ `f14ebbdd` (2026-09-14).
- [x] **Step 2: Basis gemessen** — `D:\Entwicklung\HASI\baseline-pr2.txt`: `7 failed, 2906 passed, 9 skipped, 320 errors`. FAILED: `test_init.py::…test_async_setup_entry_success`, `…_with_weather_service`, `test_next_irrigation_sensor.py::…test_setup_entry_announces_after_loading_schedules`, `test_opensprinkler_teardown.py` ×3, `test_panel.py::…static_path_config`.
- [ ] **Step 3: vitest-Basis messen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
npm ci
npx vitest run 2>&1 | tail -5 > /d/Entwicklung/HASI/baseline-pr2-vitest.txt
cat /d/Entwicklung/HASI/baseline-pr2-vitest.txt
```
Expected: „22 passed“ Dateien / „614 passed“ Tests (Probelauf 2026-09-15); abweichende Zahl notieren.

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
rate in mm/h covering the interval that ENDS at its stamp. Time zones are passed
explicitly; nothing here reads Home Assistant's.
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
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: Collection-Fehler `ModuleNotFoundError: No module named 'custom_components.irrigation_plus.forecast_window'`.

- [ ] **Step 3: Modul schreiben**

Datei `custom_components/irrigation_plus/forecast_window.py`:

```python
"""Expected precipitation over a run's calendar days.

Pure arithmetic -- no Home Assistant import -- so the window can be checked
against hand-computed numbers. The precipitation skip guard hands it the
configured client's hourly precipitation series and its dated daily entries,
and Home Assistant's own time zone decides which calendar days a run covers.

The window starts at the run's own local DATE and spans ``days`` calendar days
from there. The guard used to sum whole days out of ``get_forecast_data``,
which by contract starts tomorrow; evaluated at dispatch on the morning of a
run, that put the first day of the window one day AFTER the run, so the day it
rained was never examined (#137). Hours before the evaluation are cut off, so a
run that starts in the evening with a one-day window sees only the rest of its
own day.

Known imprecisions, each bounded:

* Pirate Weather's hourly points are read as ending at their stamp, which its
  client marks as assumed; if they begin there, the run date's total is off by
  one hour of rain at each end.
* Open-Meteo converts its local stamps with the document's single
  ``utc_offset_seconds``, so hours after a daylight-saving change inside the
  document sit an hour off.
* ``day_projection.forecast_rain_mm`` integrates the same series for the
  next-run projection but declines when the series starts after the span. Here
  the first sample reaches back one step, which is what lets a three-hourly
  series cover the hours just after a fetch. The two can disagree on whether a
  span is covered; the difference is deliberate, do not fix one side only.
"""

from __future__ import annotations

import datetime
from typing import NamedTuple

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
    gives it 23 or 25 hours. The part before ``evaluated_at`` is cut off, because
    a forecast says nothing about hours that have already passed; a day that is
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
        segments.append((stamp - span, stamp, rate))
    return segments


def expected_rain(*, run_start, evaluated_at, days, tz, hourly, daily) -> ExpectedRain:
    """Forecast precipitation on the run's local date and the ``days - 1`` after it.

    The hourly series is integrated wherever it reaches. Coverage is reported per
    day so the caller can refuse to decide on a run date nothing forecast.
    ``daily`` is not read yet.
    """
    intervals = window_intervals(run_start, days, tz, evaluated_at)
    pieces = [
        (start, end, rate / _SECONDS_PER_HOUR)
        for start, end, rate in _hourly_segments(hourly)
    ]
    total = 0.0
    run_date_covered = True
    complete = True
    for index, start, end in intervals:
        covered = 0.0
        for piece_start, piece_end, per_second in pieces:
            seconds = _overlap_seconds(start, end, piece_start, piece_end)
            total += per_second * seconds
            covered += seconds
        if covered < (end - start).total_seconds() - _COVERAGE_TOLERANCE_SECONDS:
            complete = False
            if index == 0:
                run_date_covered = False
    return ExpectedRain(total, run_date_covered, complete)
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 6 passed.

- [ ] **Step 5: Mutationsproben** (Rezept im Rahmen)

1. `window_intervals`: `start = max(_local_midnight_utc(day, tz), evaluated)` → `start = _local_midnight_utc(day, tz)` → `test_the_rest_of_the_run_day_counts_from_the_evaluation` FAIL (24 statt 18).
2. `run_date = run_start.astimezone(tz).date()` → `run_date = run_start.astimezone(_UTC).date()` → `test_a_three_hourly_slot_across_midnight_is_split` FAIL (0 statt 3); die drei Umstellungs-Tests fallen mit.
3. `_local_midnight_utc`: `.astimezone(_UTC)` entfernen → `test_24_hours_of_forecast_do_not_cover_a_25_hour_day` FAIL (`run_date_covered` True). *(Der 25-mm-Test allein fängt diese Mutation NICHT — im Probelauf bestätigt.)*
4. `_hourly_segments`: `span = stamp - points[i - 1][0]` → `span = datetime.timedelta(hours=1)` → `test_a_three_hourly_slot_across_midnight_is_split` FAIL.
5. `window_intervals`: `evaluated = evaluated_at.astimezone(_UTC)` → `evaluated = run_start.astimezone(_UTC)` → `test_the_evening_before_looks_at_the_run_date` FAIL (18 statt 24).

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

### Task 2: `forecast_window` — Lücken, doppelte Zeitstempel, ungültige Werte

**Files:**
- Modify: `custom_components/irrigation_plus/forecast_window.py` (`_hourly_segments`, Import `math`)
- Test: `tests/test_forecast_window.py`

- [ ] **Step 1: Tests anhängen** (dazu `import math` in den Test-Importen zwischen `import datetime` und `import zoneinfo` ergänzen)

```python
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


def test_a_negative_rate_counts_as_dry_and_a_non_number_as_no_forecast():
    at = _utc(2026, 9, 13, 0, 0)
    series = _hourly(at, 24, 1.0)
    series[2] = (series[2][0], -5.0)  # 02:00-03:00 dry
    series[10] = (series[10][0], math.nan)  # 10:00-11:00 unknown
    rain = expected_rain(
        run_start=at, evaluated_at=at, days=1, tz=UTC, hourly=series, daily=[]
    )
    assert rain.mm == pytest.approx(22.0)
    assert rain.run_date_covered is False


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
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 4 failed, 8 passed — FAIL `test_a_gap_…` (14.0 statt 2.0), beide `test_a_duplicated_stamp_…` (0.0 statt 4.0), `test_a_negative_rate_…` (nan). Die zwei `test_a_series_starting_just_after_the_evaluation` sind grün (Pins; Beweis per Mutation 4 und 5).

- [ ] **Step 3: Implementieren**

In `forecast_window.py` den Import-Block ergänzen:

```python
import datetime
import math
from typing import NamedTuple
```

`_hourly_segments` vollständig ersetzen durch:

```python
def _hourly_segments(series):
    """``[(start, end, mm_per_hour)]`` in UTC from a client's ``[(stamp, rate)]``.

    Wurzel: a sample's length used to be the gap to the previous stamp. Open-Meteo
      and Pirate Weather drop a row without a value, so a missing hour stretched
      the next rate back across the gap: its water multiplied and the gap counted
      as forecast.
    Fix-Logik: each rate covers the interval ENDING at its stamp, the convention
      every client hands back, but never more than one step of the series, its
      smallest spacing. The first sample reaches back one step. A longer spacing
      is a hole the caller sees as uncovered. A duplicated stamp keeps its highest
      rate; a rate that is not a finite number is dropped, a negative one is dry.
    NOT-TO-DO: do not cap at a fixed length such as three hours: an hourly series
      with a two-hour hole would still stretch. Met Office already spreads its
      amounts over its own gaps, so capping under-counts there -- the direction
      that waters rather than skips. And check ``math.isfinite`` before any
      ``max``: ``max(0.0, nan)`` is ``0.0`` and would turn a hole into a dry hour.
    siehe tests/test_forecast_window.py
    """
    rates = {}
    for stamp, rate in series or []:
        if stamp is None or rate is None:
            continue
        try:
            value = float(rate)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        key = stamp.astimezone(_UTC)
        rates[key] = max(rates.get(key, 0.0), value, 0.0)
    stamps = sorted(rates)
    if not stamps:
        return []
    spacings = [
        later - earlier for earlier, later in zip(stamps, stamps[1:], strict=False)
    ]
    step = min(spacings) if spacings else datetime.timedelta(hours=1)
    return [(stamp - step, stamp, rates[stamp]) for stamp in stamps]
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 12 passed.

- [ ] **Step 5: Mutationsproben**

1. `step = min(spacings) if spacings else …` → `step = max(spacings) if spacings else …` → `test_a_gap_…` FAIL (14.0).
2. `rates[key] = max(rates.get(key, 0.0), value, 0.0)` → `rates[key] = max(value, 0.0)` → nur `test_a_duplicated_stamp_…[high-first]` FAIL; → `rates.setdefault(key, max(value, 0.0))` → nur `[low-first]` FAIL.
3. `if not math.isfinite(value): continue` entfernen → `test_a_negative_rate_…` FAIL an `run_date_covered` (True: `max` macht NaN zu einer abgedeckten trockenen Stunde). `max(rates.get(key, 0.0), value, 0.0)` → `max(rates.get(key, value), value)` → derselbe Test FAIL (17 statt 22).
4. `_COVERAGE_TOLERANCE_SECONDS = 1.0` → `3600.0` → `test_a_series_starting_just_after_the_evaluation[2.0-False]` FAIL.
5. `_COVERAGE_TOLERANCE_SECONDS = 1.0` → `0.0` → `test_a_series_starting_just_after_the_evaluation[0.5-True]` FAIL.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_forecast_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/forecast_window.py tests/test_forecast_window.py
git commit -F - <<'EOF'
fix(forecast): a gap in the hourly series is a hole, not a stretch

Two clients drop an hour without a value. Reading a sample's length as the gap
to the previous stamp stretched the next rate across the missing hours, which
multiplied its water and counted the gap as forecast. A sample now covers at
most one step of the series, so a gap is reported as uncovered.

A duplicated stamp keeps its highest rate whatever the order, a rate that is
not a finite number is dropped, and a negative one counts as dry.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Expected: ruff „All checks passed!“ (ohne `strict=False` meldet ruff B905).

---

### Task 3: `forecast_window` — Auffüllen hinter der Reihe, `day_span`, vergangenes Laufdatum

**Files:**
- Modify: `custom_components/irrigation_plus/forecast_window.py`
- Test: `tests/test_forecast_window.py`

- [ ] **Step 1: Tests anhängen** (Import auf `from custom_components.irrigation_plus.forecast_window import day_span, expected_rain` erweitern)

```python
def test_daily_entries_fill_in_only_behind_the_hourly_series():
    # OWM builds its days from the same three-hourly list as its series, and its
    # last day holds only the slots up to the series' end while claiming the whole
    # day. An entry that overlaps the series is therefore left out whole; the rest
    # of that day is reported uncovered rather than guessed.
    at = _utc(2026, 9, 13, 0, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=3,
        tz=UTC,
        # 36 hours of 1 mm/h: the whole 13th and the first half of the 14th
        hourly=_hourly(at, 36, 1.0),
        daily=[_day(_utc(2026, 9, 14), 12.0), _day(_utc(2026, 9, 15), 10.0)],
    )
    # 24 (13th) + 12 (14th, hourly only) + 10 (15th)
    assert rain.mm == pytest.approx(46.0)
    assert rain.run_date_covered is True
    assert rain.complete is False


def test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again():
    # OWM files each three-hourly slot under the UTC date of its stamp and gives
    # the bucket the whole day. Fetched between 00Z and 03Z, the list's last slot
    # is stamped 00Z: its rain fell in the three hours BEFORE, which the series
    # already counts, yet its bucket's span starts exactly at the series' end.
    first = _utc(2026, 9, 13, 3, 0)
    stamps = [first + datetime.timedelta(hours=3 * k) for k in range(40)]
    assert stamps[-1] == _utc(2026, 9, 18, 0, 0)
    hourly = [(s, 1.0 if s == stamps[-1] else 0.0) for s in stamps]
    at = _utc(2026, 9, 17, 0, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=2,
        tz=UTC,
        hourly=hourly,
        # The bucket for the 18th holds that one slot: 3 mm.
        daily=[_day(_utc(2026, 9, 18), 3.0)],
    )
    assert rain.mm == pytest.approx(3.0)
    assert rain.run_date_covered is True
    assert rain.complete is False


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
    # 13th overlaps it for 22 of its 24 hours. Counting the whole entry for the
    # local date holding its middle -- the panel's label rule -- would say 24.
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
    # be mistaken for today by its position.
    at = _utc(2026, 9, 13, 6, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=1,
        tz=UTC,
        hourly=[],
        daily=[_day(_utc(2026, 9, 12), 50.0)],
    )
    assert rain.mm == pytest.approx(0.0)
    assert rain.run_date_covered is False


def test_a_run_date_already_past_is_not_covered():
    # A projection may name a run that started before midnight. Nothing forecasts
    # its date any more, whatever the days after it hold.
    rain = expected_rain(
        run_start=_utc(2026, 9, 12, 21, 50),
        evaluated_at=_utc(2026, 9, 13, 6, 0),
        days=2,
        tz=UTC,
        hourly=_hourly(_utc(2026, 9, 13, 0, 0), 48, 1.0),
        daily=[],
    )
    assert rain.run_date_covered is False
    assert rain.complete is False


def test_a_daily_total_that_is_not_a_number_or_negative_adds_nothing():
    at = _utc(2026, 9, 13, 0, 0)
    rain = expected_rain(
        run_start=at,
        evaluated_at=at,
        days=3,
        tz=UTC,
        hourly=[],
        daily=[
            _day(_utc(2026, 9, 13), -10.0),
            _day(_utc(2026, 9, 14), math.nan),
            _day(_utc(2026, 9, 15), 4.0),
        ],
    )
    assert rain.mm == pytest.approx(4.0)
    assert rain.run_date_covered is True
    assert rain.complete is False


def test_day_span_reads_an_aware_span_in_utc():
    start = datetime.datetime(2026, 9, 13, tzinfo=BERLIN)
    entry = {
        FORECAST_DAY_START: start,
        FORECAST_DAY_END: start + datetime.timedelta(days=1),
    }
    span = day_span(entry)
    assert span == (_utc(2026, 9, 12, 22, 0), _utc(2026, 9, 13, 22, 0))
    assert span[0].utcoffset() == datetime.timedelta(0)
    assert span[1].utcoffset() == datetime.timedelta(0)


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param({FORECAST_DAY_END: _utc(2026, 9, 14)}, id="no-start"),
        pytest.param({FORECAST_DAY_START: _utc(2026, 9, 13)}, id="no-end"),
        pytest.param(
            {
                FORECAST_DAY_START: datetime.datetime(2026, 9, 13),
                FORECAST_DAY_END: _utc(2026, 9, 14),
            },
            id="naive",
        ),
        pytest.param(
            {
                FORECAST_DAY_START: _utc(2026, 9, 14),
                FORECAST_DAY_END: _utc(2026, 9, 13),
            },
            id="reversed",
        ),
        pytest.param(
            {
                FORECAST_DAY_START: _utc(2026, 9, 13),
                FORECAST_DAY_END: _utc(2026, 9, 13),
            },
            id="empty",
        ),
    ],
)
def test_day_span_refuses_a_span_it_cannot_place(entry):
    assert day_span(entry) is None
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: Collection-Fehler `ImportError: cannot import name 'day_span'`. Kontrollblick (Import temporär auf `expected_rain` zurück, danach wieder erweitern): FAIL `fill_in_only_behind` (36), `without_an_hourly_series` (0.0), `utc_day_entry` (0.0), `run_date_already_past` (True), `not_a_number_or_negative` (0.0), dazu die 6 `day_span`-Items (`NameError`). Grün (Pins, Beweis per Mutation): `owm_s_last_day_…` (3.0 schon ohne Tageseinträge), `entry_for_a_day_already_past`.

- [ ] **Step 3: Implementieren**

In `forecast_window.py` den Import-Block so ergänzen (eigene isort-Sektion, durch eine Leerzeile getrennt; so im Nachtest ruff-sauber):

```python
from __future__ import annotations

import datetime
import math
from typing import NamedTuple

from .const import FORECAST_DAY_END, FORECAST_DAY_START, MAPPING_PRECIPITATION
```

Direkt nach `class ExpectedRain` einfügen:

```python
def day_span(entry):
    """``(start, end)`` in UTC of the day a daily forecast entry covers, or None.

    The one reader of ``FORECAST_DAY_START``/``FORECAST_DAY_END``: the panel
    labels a day from it and the skip guard weighs a day with it, so the two
    cannot disagree about which entries carry a usable span. The rules they apply
    to a span differ on purpose -- the panel names the local date holding its
    middle, the guard counts it by overlap. None unless both ends are present,
    carry a time zone, and the end lies after the start.
    """
    start = entry.get(FORECAST_DAY_START)
    end = entry.get(FORECAST_DAY_END)
    if not isinstance(start, datetime.datetime) or not isinstance(
        end, datetime.datetime
    ):
        return None
    if start.utcoffset() is None or end.utcoffset() is None:
        return None
    start, end = start.astimezone(_UTC), end.astimezone(_UTC)
    if end <= start:
        return None
    return start, end
```

Direkt vor `def expected_rain` einfügen:

```python
def _entries_behind(daily, series_end):
    """``[(start, end, mm)]`` for dated daily entries lying behind the hourly series.

    Wurzel: OWM builds its days from the same three-hourly list its hourly series
      comes from. Its last day holds only the slots up to the series' end while
      its span claims the whole day, and a slot stamped 00Z is filed under the new
      day although its rain fell in the three hours before. Filling from such an
      entry counted rain the series had already counted, and reported the day as
      complete.
    Fix-Logik: an entry fills in only where the series has nothing to say -- its
      span has to start AFTER the series' last stamp. An entry that overlaps the
      series, or starts exactly at its end, is left out whole, so the rest of its
      day is uncovered. That under-counts, which errs towards watering.
    NOT-TO-DO: do not shorten the span in the client. The panel labels a day by
      the middle of that span, so the client's span has to stay the whole day.
    siehe tests/test_forecast_window.py::test_daily_entries_fill_in_only_behind_the_hourly_series
      und ::test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again
    """
    out = []
    for entry in daily or []:
        if not isinstance(entry, dict):
            continue
        span = day_span(entry)
        if span is None:
            continue
        try:
            mm = float(entry.get(MAPPING_PRECIPITATION))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(mm):
            continue
        start, end = span
        if series_end is not None and start <= series_end:
            continue
        out.append((start, end, max(0.0, mm)))
    return out
```

`expected_rain` vollständig ersetzen durch:

```python
def expected_rain(*, run_start, evaluated_at, days, tz, hourly, daily) -> ExpectedRain:
    """Forecast precipitation on the run's local date and the ``days - 1`` after it.

    The hourly series is integrated wherever it reaches. Dated daily entries that
    start after it fill in, each counted by the share of its own span that falls
    inside the window -- a UTC-day entry thus contributes to a local date in
    proportion to their overlap. Coverage is reported per day so the caller can
    refuse to decide on a run date nothing forecast; a run date already past at
    the evaluation counts as uncovered.
    """
    intervals = window_intervals(run_start, days, tz, evaluated_at)
    segments = _hourly_segments(hourly)
    series_end = segments[-1][1] if segments else None
    pieces = [(start, end, rate / _SECONDS_PER_HOUR) for start, end, rate in segments]
    pieces += [
        (start, end, mm / (end - start).total_seconds())
        for start, end, mm in _entries_behind(daily, series_end)
    ]
    total = 0.0
    run_date_covered = bool(intervals) and intervals[0][0] == 0
    complete = run_date_covered
    for index, start, end in intervals:
        covered = 0.0
        for piece_start, piece_end, per_second in pieces:
            seconds = _overlap_seconds(start, end, piece_start, piece_end)
            total += per_second * seconds
            covered += seconds
        if covered < (end - start).total_seconds() - _COVERAGE_TOLERANCE_SECONDS:
            complete = False
            if index == 0:
                run_date_covered = False
    return ExpectedRain(total, run_date_covered, complete)
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 25 passed.

- [ ] **Step 5: Mutationsproben**

1. `_entries_behind`: `if series_end is not None and start <= series_end: continue` entfernen → `test_daily_entries_fill_in_only_behind_the_hourly_series` FAIL (58 statt 46: der 14. bekommt 12 aus der Reihe plus die ganzen 12 des Eintrags); `test_owm_s_last_day_…` fällt mit.
2. `start <= series_end` → `start < series_end` → `test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again` FAIL (6.0 statt 3.0).
3. `run_date_covered = bool(intervals) and intervals[0][0] == 0` → `run_date_covered = True` → `test_a_run_date_already_past_is_not_covered` FAIL.
4. `if index == 0:` → `if index == 1:` → `test_without_an_hourly_series_the_run_date_is_reported_uncovered` FAIL.
5. Mitte-Regel statt Überlappung: die Zeilen `pieces += [ … _entries_behind(daily, series_end) ]` ersetzen durch

   ```python
   for start, end, mm in _entries_behind(daily, series_end):
       day = (start + (end - start) / 2).astimezone(tz).date()
       s = _local_midnight_utc(day, tz)
       e = _local_midnight_utc(day + datetime.timedelta(days=1), tz)
       pieces.append((s, e, mm / (e - s).total_seconds()))
   ```
   → `test_a_utc_day_entry_counts_against_a_local_date_by_overlap` FAIL (24 statt 22).
6. `_overlap_seconds`: `max(0.0, …)` entfernen, also `return (min(a_end, b_end) - max(a_start, b_start)).total_seconds()` → `test_an_entry_for_a_day_already_past_contributes_nothing` FAIL (negativ).
7. `_entries_behind`: `if not math.isfinite(mm): continue` entfernen → `test_a_daily_total_…` FAIL an `complete` (True: `max(0.0, nan)` = 0.0 macht den NaN-Tag zu einem abgedeckten trockenen Tag); `max(0.0, mm)` → `mm` → derselbe Test FAIL (−6).
8. `day_span`:
   - `if start.utcoffset() is None or end.utcoffset() is None: return None` entfernen → `[naive]` FAIL
   - `end <= start` → `end < start` → `[empty]` FAIL
   - `if end <= start: return None` entfernen → `[reversed]` und `[empty]` FAIL
   - die `isinstance`-Prüfung entfernen → `[no-start]` und `[no-end]` FAIL (`AttributeError`)
   - `start, end = start.astimezone(_UTC), end.astimezone(_UTC)` entfernen → `test_day_span_reads_an_aware_span_in_utc` FAIL (`utcoffset` 2 h)

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_forecast_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/forecast_window.py tests/test_forecast_window.py
git commit -F - <<'EOF'
feat(forecast): fill the window from dated days behind the hourly series

Beyond the hourly series the dated daily entries fill in by the share of their
span inside the window, which is also how a UTC-day entry is weighed against a
local date. Only entries starting after the series' last stamp count: OWM's
days come from the same three-hourly list, its last day holds only the slots up
to the series' end, and a 00Z slot is filed under the new day although its rain
fell before. Filling from those counted rain twice.

A run date nothing forecasts is reported as uncovered, and so is a run date
already past at the evaluation. day_span is added as the shared reader of an
entry's span; the panel moves to it next.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Panel liest die Spanne über `day_span`

**Files:**
- Modify: `custom_components/irrigation_plus/websockets.py` (Import, `websocket_get_weather_forecast` Z. ~1065-1114)
- Test: `tests/test_websocket_get_weather_forecast.py`

- [ ] **Step 1: Test anhängen**

```python
@pytest.mark.parametrize("broken", ["reversed", "naive"])
async def test_an_entry_whose_span_cannot_be_placed_keeps_the_positional_label(
    broken,
):
    # The panel and the skip guard read the span through the same helper, so an
    # entry the guard refuses is refused here too. A naive start used to reach
    # the subtraction below and raise, taking the whole forecast card down.
    today = dt_util.now().date()
    entry = _utc_day_entry(today + datetime.timedelta(days=3))
    if broken == "reversed":
        entry[const.FORECAST_DAY_START], entry[const.FORECAST_DAY_END] = (
            entry[const.FORECAST_DAY_END],
            entry[const.FORECAST_DAY_START],
        )
    else:
        entry[const.FORECAST_DAY_START] = entry[const.FORECAST_DAY_START].replace(
            tzinfo=None
        )

    assert await _labels([entry]) == [(today + datetime.timedelta(days=1)).isoformat()]
```

- [ ] **Step 2: Test läuft rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_websocket_get_weather_forecast.py -p _local_socket_unblock -q`
Expected: `[reversed]` FAIL (Label today+3 statt today+1); `[naive]` FAIL mit `TypeError: can't subtract offset-naive and offset-aware datetimes`.

- [ ] **Step 3: Implementieren**

In `websockets.py` zwischen `from .const import SmartIrrigationError` und `from .helpers import CannotConnect, InvalidAuth, validate_api_key` ergänzen:

```python
from .forecast_window import day_span
```

Den Docstring von `websocket_get_weather_forecast` ersetzen:

```python
    """Return the weather service's daily forecast (one entry per upcoming day).

    Reuses the coordinator's weather client (the same forecast already used for
    the precip look-ahead skip). Each entry carries the span of the day it
    covers (FORECAST_DAY_START/END), and the local date of its middle is the
    label.
    Values are metric (the frontend labels units; value conversion is the
    separate H7-units follow-up).
    """
```

durch:

```python
    """Return the weather service's daily forecast (one entry per upcoming day).

    Reuses the coordinator's weather client, whose daily entries the precip
    look-ahead skip also reads. Each entry carries the span of the day it covers
    (FORECAST_DAY_START/END), read through ``forecast_window.day_span``, and the
    local date of its middle is the label.
    Values are metric (the frontend labels units; value conversion is the
    separate H7-units follow-up).
    """
```

Im Schleifenkörper ersetzen:

```python
        start = day.get(const.FORECAST_DAY_START)
        end = day.get(const.FORECAST_DAY_END)
        if start is not None and end is not None:
```

durch:

```python
        span = day_span(day)
        if span is not None:
            start, end = span
```

und im `else`-Zweig ersetzen:

```python
            # No span, or only half of one: assume the list starts at tomorrow.
```

durch:

```python
            # No usable span -- none, half of one, naive, or not after its start
            # (day_span, shared with the skip guard): assume the list starts at
            # tomorrow.
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_websocket_get_weather_forecast.py tests/test_forecast_window.py -p _local_socket_unblock -q`
Expected: 35 passed (10 Panel-Items + 25 Fenster).

- [ ] **Step 5: Mutationsprobe**

`span = day_span(day)` / `if span is not None:` / `start, end = span` zurück auf `start = day.get(const.FORECAST_DAY_START)`, `end = day.get(const.FORECAST_DAY_END)`, `if start is not None and end is not None:` → beide neuen Items FAIL.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_websocket_get_weather_forecast.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/websockets.py tests/test_websocket_get_weather_forecast.py
git commit -F - <<'EOF'
refactor(panel): read the forecast day's span through the shared reader

The panel and the precipitation skip guard now read FORECAST_DAY_START/END
through one helper, so they agree on which entries carry a usable span. They
still apply different rules to it: the panel names the local date holding the
span's middle, the guard counts a span by overlap.

An entry with a naive or reversed span now gets the positional label; a naive
start used to raise and take the forecast card down.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Met Office liest das aktuellere seiner zwei Dokumente

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py` (neue Methode `_forecast_document`, Z. 202 und 231, zwei Docstrings)
- Test: `tests/test_met_office_forecast_document.py` (neu)

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Datei `tests/test_met_office_forecast_document.py`:

```python
"""Met Office's hourly accessors read the more current of its two documents.

The client holds the hourly product, refreshed only by ``get_data``, and the
three-hourly one, refreshed by ``get_forecast_data``. The accessors preferred the
hourly document whenever one existed, however old. The precipitation skip guard
runs before any ``get_data`` of a dispatch, so on an install whose sensors take
nothing from Met Office it decided on the hourly forecast of an earlier run while
a fresh three-hourly one sat beside it.
"""

import datetime

from custom_components.irrigation_plus.weathermodules.MetOfficeClient import (
    MetOfficeClient,
)

UTC = datetime.timezone.utc
# The client stamps its fetches with naive local time.
FETCHED = datetime.datetime(2026, 9, 13, 6, 20)


def _doc(time, amount, temperature):
    return {
        "features": [
            {
                "properties": {
                    "timeSeries": [
                        {
                            "time": time,
                            "totalPrecipAmount": amount,
                            "screenTemperature": temperature,
                        }
                    ]
                }
            }
        ]
    }


def _client(hourly_age):
    c = MetOfficeClient(api_key="k", latitude=51.5, longitude=-0.1, elevation=10)
    # An hourly auto-update: the cache lives one hour less a second.
    c.cache_seconds = 3599
    c._cached_hourly = _doc("2026-09-12T06:00Z", 0.0, 11.0)
    c._cached_hourly_at = FETCHED - hourly_age
    c._cached_three_hourly = _doc("2026-09-13T06:00Z", 3.0, 17.0)
    c._cached_three_hourly_at = FETCHED
    return c


def test_a_day_old_hourly_document_gives_way_to_a_fresh_three_hourly_one():
    series = _client(datetime.timedelta(days=1)).get_hourly_precipitation_forecast()
    assert series == [(datetime.datetime(2026, 9, 13, 7, tzinfo=UTC), 3.0)]


def test_an_hourly_document_within_one_cache_lifetime_is_still_preferred():
    # Fetched half an hour before the three-hourly one: as current as the cache
    # allows, and the finer product. The calculation's forecast fetch follows an
    # update cycle by minutes; it must not swap the hourly series out.
    series = _client(datetime.timedelta(minutes=30)).get_hourly_precipitation_forecast()
    assert series == [(datetime.datetime(2026, 9, 12, 7, tzinfo=UTC), 0.0)]


def test_the_temperature_accessor_follows_the_same_rule():
    series = _client(datetime.timedelta(days=1)).get_hourly_temperature_forecast()
    assert series == [(datetime.datetime(2026, 9, 13, 6, tzinfo=UTC), 17.0)]


def test_documents_without_a_fetch_time_keep_the_hourly_preference():
    c = _client(datetime.timedelta(days=1))
    c._cached_hourly_at = None
    assert c.get_hourly_precipitation_forecast() == [
        (datetime.datetime(2026, 9, 12, 7, tzinfo=UTC), 0.0)
    ]
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_met_office_forecast_document.py -p _local_socket_unblock -q`
Expected: FAIL `test_a_day_old_hourly_document_…` und `test_the_temperature_accessor_…` (Werte aus dem Stundendokument). Die anderen zwei grün (Pins; Beweis per Mutation).

- [ ] **Step 3: Implementieren**

In `MetOfficeClient.py` direkt vor `def get_hourly_temperature_forecast` einfügen:

```python
    def _forecast_document(self):
        """The fetched document the hourly accessors read, or None.

        Wurzel: both accessors took the hourly document whenever one existed. Only
          ``get_data`` refreshes it, and the precipitation skip guard runs before
          any ``get_data`` of a dispatch, so an install whose sensors take nothing
          from Met Office read the hourly forecast of an earlier run beside a
          three-hourly document ``get_forecast_data`` had just fetched.
        Fix-Logik: prefer the hourly product, the finer of the two, unless the
          three-hourly one was fetched more than one cache lifetime after it. A
          document younger than that is as current as the cache allows, so an
          ordinary update cycle keeps the hourly series.
        NOT-TO-DO: do not fetch here; the accessors read already-fetched documents
          only. And do not simply take the later fetch: the calculation's forecast
          fetch follows the update cycle by minutes and would swap the finer
          product out of the intra-day estimate after every calculation.
        siehe tests/test_met_office_forecast_document.py
        """
        hourly, three_hourly = self._cached_hourly, self._cached_three_hourly
        if not hourly or not three_hourly:
            return hourly or three_hourly
        if self._cached_hourly_at is None or self._cached_three_hourly_at is None:
            return hourly
        lifetime = datetime.timedelta(
            seconds=max(self.cache_seconds, _MIN_CACHE_SECONDS)
        )
        if self._cached_three_hourly_at - self._cached_hourly_at > lifetime:
            return three_hourly
        return hourly
```

In **beiden** Accessoren (`get_hourly_temperature_forecast`, `get_hourly_precipitation_forecast`) ersetzen:

```python
        doc = self._cached_hourly or self._cached_three_hourly
```

durch:

```python
        doc = self._forecast_document()
```

Im Docstring von `get_hourly_temperature_forecast` ersetzen:

```python
        The hourly endpoint runs T to T+48, which covers a calculation window's
        remaining hours with room to spare. Falls back to the three-hourly
        product where only that has been fetched -- coarser, but it still
        places the window's extremes far better than reading them off the
        observation.
```

durch:

```python
        The hourly endpoint runs T to T+48, which covers a calculation window's
        remaining hours with room to spare. Falls back to the three-hourly
        product where only that has been fetched, or where the hourly document
        is more than one cache lifetime older (``_forecast_document``) --
        coarser, but it still places the window's extremes far better than
        reading them off the observation.
```

Im Docstring von `get_hourly_precipitation_forecast` ersetzen:

```python
        one the consumer integrates. The step length is taken from the series
        itself, so the three-hourly product stands in where only it was fetched
        and its samples are divided back to a rate rather than counted as an
        hour's worth.
```

durch:

```python
        one the consumer integrates. The step length is taken from the series
        itself, so the three-hourly product stands in where only it was fetched
        or the hourly document has gone stale (``_forecast_document``), and its
        samples are divided back to a rate rather than counted as an hour's
        worth.
```

- [ ] **Step 4: Tests grün, Nachbarn grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_met_office_forecast_document.py tests/test_hourly_precipitation_forecast.py tests/test_hourly_temperature_forecast.py tests/test_weather_modules.py tests/test_pressure_shared_across_clients.py -p _local_socket_unblock -q`
Expected: alle PASS (Probelauf: 77 passed = 73 Basis + 4; Teardown-Errors mit Basis vergleichen).

- [ ] **Step 5: Mutationsproben**

1. `_forecast_document`: die letzten zwei `if`-Blöcke entfernen (immer `hourly`) → `test_a_day_old_…` und `test_the_temperature_accessor_…` FAIL.
2. `> lifetime` → `> datetime.timedelta(0)` → `test_an_hourly_document_within_one_cache_lifetime_…` FAIL.
3. Nur im Temperatur-Accessor `doc = self._cached_hourly or self._cached_three_hourly` zurück → `test_the_temperature_accessor_…` FAIL.
4. `if self._cached_hourly_at is None or …: return hourly` entfernen → `test_documents_without_a_fetch_time_…` FAIL (`TypeError`).

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_met_office_forecast_document.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weathermodules/MetOfficeClient.py tests/test_met_office_forecast_document.py
git commit -F - <<'EOF'
fix(met-office): hourly accessors read the more current document

Both hourly accessors preferred the hourly document whenever one existed. Only
get_data refreshes it, and the precipitation skip guard runs before any get_data
of a dispatch, so an install whose sensors take nothing from Met Office read the
hourly forecast of an earlier run beside a three-hourly document that had just
been fetched. The intra-day estimate reads the same accessors.

The hourly product still wins unless the three-hourly one was fetched more than
one cache lifetime after it, so an ordinary update cycle keeps the finer series.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: `_eval_precipitation` am Datum des Laufs

**Files:**
- Modify: `custom_components/irrigation_plus/skip_conditions.py` (Import, `_eval_precipitation`)
- Modify: `custom_components/irrigation_plus/const.py` (Kommentar Z. 41-42)
- Modify: `custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py` (Kommentar Z. ~212-213)
- Modify: `tests/test_init.py` (`_FakeForecastClient`, `TestPrecipitationLookAhead`, Importe)
- Test: `tests/test_precipitation_guard.py` (neu)

- [ ] **Step 1: Fehlschlagende Tests schreiben — der echte Fall vom 12./13. September**

Datei `tests/test_precipitation_guard.py`:

```python
"""The precipitation skip guard examines the run's own date.

Rebuilt from the live case behind #137, in the time zone of that install
(Europe/Berlin, checked on the install). Forecast: 2.15 mm on the 13th, window
1 day, threshold 2 mm. The guard used to read the day AFTER the run: it skipped
the dry 12th for the 13th's rain and let the 13th water, because by then it was
looking at the 14th.

The zone is set by the ``berlin`` fixture, which each test requests by name. The
repo's autouse fixtures hand every test a ``hass`` that sets US/Pacific, and a
fixture running before it would be overwritten.
"""

import datetime
import logging
import zoneinfo
from types import SimpleNamespace
from unittest.mock import Mock, patch

import homeassistant.util.dt as dt_util
import pytest
import requests
from freezegun import freeze_time

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.skip_conditions import SKIP_PRECIPITATION
from custom_components.irrigation_plus.weathermodules import OWMClient as owm_module

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


@pytest.fixture
def berlin():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(BERLIN)
    try:
        yield
    finally:
        dt_util.set_default_time_zone(original)


def _local(*args):
    return datetime.datetime(*args, tzinfo=BERLIN).astimezone(UTC)


# The live forecast's rain on the 13th, in the hour ending 14:00 local.
AFTERNOON = _local(2026, 9, 13, 14, 0)
# Rain in the first hour of the 13th: 00:00-01:00 local is 22:00-23:00 UTC on the
# 12th, so only Home Assistant's zone puts it on the run's date.
FIRST_LOCAL_HOUR = _local(2026, 9, 13, 1, 0)


def _forecast_days(rain_on):
    """UTC-day entries after today's UTC date, as OWM (HA-Prod's service) builds them."""
    today = dt_util.utcnow().date()
    out = []
    for d in (12, 13, 14, 15):
        start = datetime.datetime(2026, 9, d, tzinfo=UTC)
        if start.date() <= today:
            continue
        out.append(
            {
                const.FORECAST_DAY_START: start,
                const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
                const.MAPPING_PRECIPITATION: 2.15 if start.date() == rain_on else 0.0,
            }
        )
    return out


def _hourly(rain_ending_at):
    """Hourly stamps from the local 12th to the local 15th, with one rainy hour."""
    first = _local(2026, 9, 12, 0, 0)
    out = []
    for h in range(1, 73):
        stamp = first + datetime.timedelta(hours=h)
        out.append((stamp, 2.15 if stamp == rain_ending_at else 0.0))
    return out


def _client(rain_ending_at=AFTERNOON):
    rain_on = (rain_ending_at - datetime.timedelta(hours=1)).date()
    return SimpleNamespace(
        get_forecast_data=lambda: _forecast_days(rain_on),
        get_hourly_precipitation_forecast=lambda: _hourly(rain_ending_at),
    )


def _daily_only_client():
    return SimpleNamespace(get_forecast_data=lambda: _forecast_days(AFTERNOON.date()))


def _coordinator(client):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()

    async def run_executor(func, *args):
        return func(*args)

    hass.async_add_executor_job = run_executor
    coord.hass = hass
    coord._WeatherServiceClient = client
    return coord


def _config(enabled=True, days=1):
    return {
        const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION: enabled,
        const.CONF_PRECIPITATION_THRESHOLD_MM: 2,
        const.CONF_PRECIPITATION_FORECAST_DAYS: days,
        const.CONF_USE_WEATHER_SERVICE: True,
    }


async def test_the_dry_day_before_the_rain_is_not_skipped(berlin):
    with freeze_time(_local(2026, 9, 12, 6, 19)):
        result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["id"] == SKIP_PRECIPITATION
    assert result["available"] is True
    assert result["observed"] == 0.0
    assert result["would_skip"] is False


async def test_the_rain_day_itself_is_skipped(berlin):
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


async def test_the_evening_outlook_for_tomorrow_looks_at_tomorrow(berlin):
    with freeze_time(_local(2026, 9, 12, 20, 0)):
        result = await _coordinator(_client())._eval_precipitation(
            _config(), _local(2026, 9, 13, 6, 20)
        )
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


async def test_rain_in_the_first_local_hour_is_not_on_the_day_before(berlin):
    with freeze_time(_local(2026, 9, 12, 6, 19)):
        result = await _coordinator(_client(FIRST_LOCAL_HOUR))._eval_precipitation(
            _config()
        )
    assert (result["observed"], result["would_skip"]) == (0.0, False)


async def test_rain_in_the_first_local_hour_counts_for_the_run_date(berlin):
    with freeze_time(_local(2026, 9, 12, 20, 0)):
        result = await _coordinator(_client(FIRST_LOCAL_HOUR))._eval_precipitation(
            _config(), _local(2026, 9, 13, 6, 20)
        )
    assert (result["observed"], result["would_skip"]) == (2.15, True)


@pytest.mark.parametrize(
    ("days", "observed", "would_skip"), [(1, 0.0, False), (2, 2.15, True)]
)
async def test_an_evening_run_with_a_one_day_window_sees_only_the_rest_of_its_day(
    berlin, days, observed, would_skip
):
    # Chosen on #137: the window is the run's own date. A run starting at 21:00
    # sees three hours with one day and the next morning's rain only with two.
    # Pinned so that a change to it is deliberate.
    with freeze_time(_local(2026, 9, 13, 21, 0)):
        result = await _coordinator(
            _client(_local(2026, 9, 14, 6, 0))
        )._eval_precipitation(_config(days=days))
    assert (result["observed"], result["would_skip"]) == (observed, would_skip)


async def test_a_client_without_an_hourly_series_cannot_decide_the_run_date(berlin):
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(_daily_only_client())._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_a_failed_refresh_does_not_decide_on_the_last_documents_series(berlin):
    # Every client returns no daily forecast when its refresh fails but keeps the
    # document of its last success, and the hourly accessor reads that one.
    # Deciding on it would skip on a forecast of any age.
    client = SimpleNamespace(
        get_forecast_data=lambda: None,
        get_hourly_precipitation_forecast=lambda: _hourly(AFTERNOON),
    )
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_a_real_client_whose_refresh_fails_leaves_the_guard_undecided(berlin):
    # The premise of the test above, with OWM itself: the failed request yields no
    # daily forecast, while the hourly accessor still reads the old document,
    # which forecasts 30 mm over the run's late morning.
    client = owm_module.OWMClient(api_key="k", latitude=50.0, longitude=7.0)
    first = datetime.datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    client._cached_forecast_doc = {
        "cod": "200",
        "list": [
            {"dt": int((first + datetime.timedelta(hours=3 * k)).timestamp())}
            | ({"rain": {"3h": 30.0}} if k == 12 else {})
            for k in range(17)
        ],
    }
    offline = requests.ConnectionError("offline")
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        with patch.object(owm_module._SESSION, "get", side_effect=offline):
            assert client.get_forecast_data() is None
            assert client.get_hourly_precipitation_forecast()
            result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_at_dispatch_an_uncovered_run_date_is_logged_at_info(berlin, caplog):
    # The guard then sits the run out, and nothing in the dashboard shows it.
    caplog.set_level(
        logging.DEBUG, logger="custom_components.irrigation_plus.skip_conditions"
    )
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        await _coordinator(_daily_only_client())._eval_precipitation(_config())
    levels = [
        r.levelno
        for r in caplog.records
        if "does not cover the run's date" in r.getMessage()
    ]
    assert levels == [logging.INFO]


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
Expected FAIL (alter Code summiert `get_forecast_data[:days]`, nimmt kein `run_start`):
- `dry_day_before_the_rain` (2.15 statt 0.0), `rain_day_itself` (0.0 statt 2.15)
- `evening_outlook_for_tomorrow`, `first_local_hour_counts_for_the_run_date` (`TypeError`: zu viele Argumente)
- `evening_run…[1-0.0-False]` (2.15 statt 0.0)
- `client_without_an_hourly_series` (`available` True), `uncovered_run_date_is_logged_at_info` (kein Eintrag)

Grün schon vorher (Pins, Beweis per Mutation): `first_local_hour_is_not_on_the_day_before`, `evening_run…[2-2.15-True]`, `failed_refresh…`, `real_client_whose_refresh_fails…`, `disabled`, `no_weather_client`.

- [ ] **Step 3: `tests/test_init.py` auf das Laufdatum umschreiben**

Importe ergänzen: `import datetime` als erste Import-Zeile (vor `from unittest.mock …`); `import homeassistant.util.dt as dt_util` und `from freezegun import freeze_time` in den Drittanbieter-Block (bei `import pytest`).

`_FakeForecastClient` und `TestPrecipitationLookAhead` (Z. 572-633) vollständig ersetzen durch:

```python
class _FakeForecastClient:
    """Minimal weather client exposing a fixed forecast for skip tests."""

    def __init__(self, days, hourly=None):
        self._days = days
        self._hourly = hourly

    def get_forecast_data(self):
        return self._days

    def get_hourly_precipitation_forecast(self):
        return self._hourly


class TestPrecipitationLookAhead:
    """The precipitation skip respects the configurable look-ahead window."""

    async def test_lookahead_window_controls_skip(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_session: AsyncMock,
    ) -> None:
        """1-day window sees only the run's own date; 2-day window adds the next day."""
        cfg = {
            const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION: True,
            const.CONF_PRECIPITATION_THRESHOLD_MM: 2.0,
            const.CONF_USE_WEATHER_SERVICE: True,
            const.CONF_PRECIPITATION_FORECAST_DAYS: 1,
        }
        mock_store = AsyncMock()
        mock_store.async_get_config.return_value = cfg
        # Constructor reads the SYNC get_config(); keep weather off there so it
        # doesn't try to build a real client (we inject a fake below).
        mock_store.get_config = Mock(
            return_value={
                const.CONF_AUTO_UPDATE_ENABLED: False,
                const.CONF_AUTO_CALC_ENABLED: False,
                const.CONF_USE_WEATHER_SERVICE: False,
            }
        )
        hass.data[const.DOMAIN] = {
            const.CONF_USE_WEATHER_SERVICE: False,
            const.CONF_WEATHER_SERVICE: None,
        }
        coordinator = SmartIrrigationCoordinator(
            hass, mock_session, mock_config_entry, mock_store
        )
        hour = datetime.timedelta(hours=1)
        frozen = datetime.datetime(2026, 9, 13, 18, 0, tzinfo=datetime.timezone.utc)
        with freeze_time(frozen):
            # Built in Home Assistant's zone, whatever the fixtures set: the run's
            # date is dry, and 5 mm fall in the hour ending 10:00 the next day.
            today = dt_util.now().date()
            midnight = dt_util.as_utc(dt_util.start_of_local_day(today))
            rain_at = (
                dt_util.as_utc(
                    dt_util.start_of_local_day(today + datetime.timedelta(days=1))
                )
                + 10 * hour
            )
            hourly = [
                (midnight + h * hour, 5.0 if midnight + h * hour == rain_at else 0.0)
                for h in range(1, 49)
            ]
            day_after = dt_util.as_utc(
                dt_util.start_of_local_day(today + datetime.timedelta(days=2))
            )
            coordinator._WeatherServiceClient = _FakeForecastClient(
                [
                    {
                        const.FORECAST_DAY_START: day_after,
                        const.FORECAST_DAY_END: day_after + 24 * hour,
                        const.MAPPING_PRECIPITATION: 0.0,
                    }
                ],
                hourly,
            )

            # 1-day window: only the run's dry date counts -> no skip
            res = await coordinator._eval_precipitation(cfg)
            assert res["observed"] == 0.0
            assert res["would_skip"] is False

            # 2-day window: 0 + 5 mm >= 2 mm threshold -> skip
            cfg[const.CONF_PRECIPITATION_FORECAST_DAYS] = 2
            res = await coordinator._eval_precipitation(cfg)
            assert res["observed"] == 5.0
            assert res["would_skip"] is True
```

- [ ] **Step 4: Implementieren**

Import in `skip_conditions.py` zwischen `from . import const` und `from .helpers import normalize_zone_selection` ergänzen:

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
        Fix-Logik: the window starts at ``run_start``'s local date in Home
          Assistant's zone and spans ``precipitation_forecast_days`` calendar days;
          without ``run_start`` it starts now, which is dispatch -- every preview
          names a start. The hourly precipitation series every client serves
          forecasts the run's date; dated daily entries starting after it fill in
          the days it does not reach. Hours before the evaluation are not forecast
          and do not count, so an evening run with a one-day window sees only the
          rest of its day. Without a daily forecast nothing is decided: a refresh
          that failed returns none, while the hourly accessor still serves the
          document of the last success, however old.
        NOT-TO-DO: do not make ``get_forecast_data`` include today to get at the
          run's date. The ET averages and the freeze guard's "coming night" both
          depend on it excluding today. Do not derive the date from a client's own
          clock (OWM uses ``utcnow().date()``): Home Assistant's zone decides. And
          do not decide on the hourly series when the daily forecast is missing.
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
            # Daily first, and nothing without it: a failed refresh returns no
            # daily list, while the hourly accessor would still serve the last
            # good document.
            daily = await self.hass.async_add_executor_job(client.get_forecast_data)
            if not daily:
                return result
            hourly = None
            if hasattr(client, "get_hourly_precipitation_forecast"):
                hourly = await self.hass.async_add_executor_job(
                    client.get_hourly_precipitation_forecast
                )
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
                # At dispatch this sits the run out of the guard, and nothing in
                # the dashboard says so. Only dispatch names no start; previews
                # name one and repeat on every refresh, so they log at debug.
                log = _LOGGER.info if run_start is None else _LOGGER.debug
                log(
                    "Precipitation skip: the forecast does not cover the run's "
                    "date, so rain is not deciding this run"
                )
                return result
            if not rain.complete:
                _LOGGER.debug(
                    "Precipitation skip: the forecast covers only part of the "
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

In `const.py` ersetzen:

```python
# How many forecast days to sum when checking precipitation. The weather clients
# return future days only (today is excluded), so 1 = the next forecast day.
```

durch:

```python
# How many forecast days to sum for forecast rain. The skip guard counts from the
# run's own local date (1 = the day of the run); forecast weighting sums
# get_forecast_data, which starts at the day after the calculation (1 = that day).
```

In `OpenMeteoClient.py` (Kommentar in `get_forecast_data`) ersetzen:

```python
            # today as the first forecast day, although the forecast list starts
            # at tomorrow for every client (see CONF_PRECIPITATION_FORECAST_DAYS).
```

durch:

```python
            # today as the first forecast day, although get_forecast_data starts
            # at tomorrow for every client.
```

- [ ] **Step 5: Tests grün, Nachbarn grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py tests/test_forecast_window.py tests/test_init.py tests/test_coordinator_mixins.py tests/test_weather_modules.py -p _local_socket_unblock -q -rf`
Expected: neue Tests PASS; `test_init.py::TestPrecipitationLookAhead` PASS; FAILED nur die zwei Basis-Namen aus `test_init.py` (`test_async_setup_entry_success`, `…_with_weather_service`).

- [ ] **Step 6: Mutationsproben**

1. Altes Verhalten: `start = dt_util.as_utc(run_start) if run_start is not None else now` → `start = (dt_util.as_utc(run_start) if run_start is not None else now) + datetime.timedelta(days=1)` (dafür temporär `import datetime`) → `dry_day_before_the_rain` UND `rain_day_itself` FAIL.
2. `tz=dt_util.DEFAULT_TIME_ZONE` → `tz=datetime.timezone.utc` (temporär `import datetime`) → `first_local_hour_is_not_on_the_day_before` UND `first_local_hour_counts_for_the_run_date` FAIL.
3. `if not daily: return result` entfernen und nach dem Holen von `hourly` `if not daily and not hourly: return result` einsetzen → `failed_refresh…` UND `real_client_whose_refresh_fails…` FAIL.
4. `if not rain.run_date_covered:` → `if False:` → `client_without_an_hourly_series` FAIL.
5. `log = _LOGGER.info if run_start is None else _LOGGER.debug` → `log = _LOGGER.debug` → `uncovered_run_date_is_logged_at_info` FAIL.
6. `window_intervals` (forecast_window.py): `for index in range(max(1, int(days)))` → `for index in range(max(2, int(days)))` → `evening_run…[1-0.0-False]` FAIL (der nächste Morgen zählt mit).

- [ ] **Step 7: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_precipitation_guard.py tests/test_init.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/const.py custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py tests/test_precipitation_guard.py tests/test_init.py
git commit -F - <<'EOF'
fix(skip): examine rain on the run's own date, not the day after it

The precipitation guard summed whole days out of get_forecast_data, which by
contract starts tomorrow, while it runs at dispatch on the morning of the run.
Its window therefore began one day AFTER the run. On a live install that meant
skipping a dry day for the next day's forecast rain, then watering on the rain
day itself because by then the guard was looking at the day after.

The window now starts at the run's local date in Home Assistant's zone and
spans the configured number of calendar days. The run's date comes from the
client's hourly precipitation series, which all four clients serve; the days
beyond it fill in from the dated daily entries. Hours already past are not
forecast and do not count, so an evening run with a one-day window sees only
the rest of its day.

Without an hourly series nothing forecasts the run's date, and without a daily
forecast (a failed refresh) the hourly series may be of any age. In both cases
the guard declines to decide rather than skip. When the run's date is not
covered at dispatch, it says so in the log.

get_forecast_data still excludes today: the ET averages and the freeze guard's
"coming night" depend on it. Forecast weighting is unchanged here. The test that
pinned the old "1 = tomorrow" window is rewritten to the run's date.

Refs #137.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Laufbeginn durchreichen — Auswertung, Vorschau, Ausblick

**Files:**
- Modify: `custom_components/irrigation_plus/skip_conditions.py` (`async_evaluate_skip_conditions`, `async_get_irrigation_outlook`, `_project_days_between_to_next_run`, neue statische Methode `_next_irrigate_run_utc`)
- Modify: `custom_components/irrigation_plus/scheduler.py` (`_projected_skip`; `dt_util` ist dort bereits importiert, Z. 10)
- Test: `tests/test_skip_run_start_threading.py` (neu)

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Datei `tests/test_skip_run_start_threading.py`:

```python
"""The run's start reaches the precipitation guard from every place that asks.

The guard's window starts at the run's local date, so each caller has to say
which run it is asking about: dispatch (now, by naming none), the schedule
projection (its planned start) and the dashboard outlook (the next scheduled
irrigate run). A preview always names a moment, because the guard reads a
missing start as dispatch and logs at INFO there.
"""

import datetime
from unittest.mock import AsyncMock, Mock

import homeassistant.util.dt as dt_util

from custom_components.irrigation_plus import SmartIrrigationCoordinator
from custom_components.irrigation_plus.scheduler import RecurringScheduleManager

UTC = datetime.timezone.utc
START = datetime.datetime(2026, 9, 13, 4, 20, tzinfo=UTC)
CALCULATE = {"action": "calculate", "next_run_utc": "2026-09-12T21:00:00+00:00"}


def _off(check_id):
    return {"id": check_id, "enabled": False, "would_skip": False}


def _outlook_coordinator(upcoming):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.store = Mock()
    coord.store.async_get_config = AsyncMock(return_value={})
    coord.recurring_schedule_manager = Mock()
    coord.recurring_schedule_manager.async_get_upcoming_runs = AsyncMock(
        return_value=upcoming
    )
    coord.async_evaluate_skip_conditions = AsyncMock(
        return_value={"would_skip": False, "checks": []}
    )
    coord.async_get_cached_zone_estimates = AsyncMock(return_value={})
    coord.get_zone_faults = Mock(return_value={})
    coord.get_zone_skips = Mock(return_value={})
    coord.get_active_runs = Mock(return_value={})
    return coord


def _projection_manager():
    manager = RecurringScheduleManager.__new__(RecurringScheduleManager)
    manager.coordinator = Mock()
    manager.coordinator.async_evaluate_skip_conditions = AsyncMock(
        return_value={"would_skip": False, "checks": []}
    )
    manager.coordinator._project_days_between_to_next_run = Mock()
    manager.coordinator._rain_delay_until_dt = Mock(return_value=None)
    return manager


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
    manager = _projection_manager()

    await manager._projected_skip(START)

    assert manager.coordinator.async_evaluate_skip_conditions.await_args.kwargs == {
        "run_start": START
    }


async def test_a_projection_without_a_start_still_names_a_moment():
    manager = _projection_manager()

    await manager._projected_skip(None)

    kwargs = manager.coordinator.async_evaluate_skip_conditions.await_args.kwargs
    assert kwargs["run_start"] is not None


async def test_the_outlook_asks_about_the_next_irrigate_run():
    coord = _outlook_coordinator(
        [CALCULATE, {"action": "irrigate", "next_run_utc": START.isoformat()}]
    )

    await coord.async_get_irrigation_outlook()

    assert coord.async_evaluate_skip_conditions.await_args.kwargs == {
        "run_start": dt_util.parse_datetime(START.isoformat())
    }


async def test_with_no_irrigate_run_the_outlook_still_names_a_moment():
    coord = _outlook_coordinator([CALCULATE])

    await coord.async_get_irrigation_outlook()

    kwargs = coord.async_evaluate_skip_conditions.await_args.kwargs
    assert kwargs["run_start"] is not None
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_skip_run_start_threading.py -p _local_socket_unblock -q`
Expected: 5 FAIL (`TypeError: unexpected keyword argument 'run_start'` bzw. `kwargs == {}` / `KeyError: 'run_start'`).

- [ ] **Step 3: `async_evaluate_skip_conditions` erweitern**

In `skip_conditions.py` ersetzen:

```python
    async def async_evaluate_skip_conditions(self) -> dict:
        """Evaluate every skip guard and return structured results.

        Unlike the boolean ``_check_*`` helpers this does not log skip decisions;
        it is safe to call for a live preview. Each check is a dict with keys
        ``id``, ``enabled``, ``would_skip``, ``available`` (could it be
        evaluated), ``observed`` and ``threshold``. Precipitation/temperature/
        wind reuse the in-memory weather-client cache, so this is normally cheap.
        """
```

durch:

```python
    async def async_evaluate_skip_conditions(self, run_start=None) -> dict:
        """Evaluate every skip guard and return structured results.

        Unlike the boolean ``_check_*`` helpers this does not log skip decisions;
        it is safe to call for a live preview. Each check is a dict with keys
        ``id``, ``enabled``, ``would_skip``, ``available`` (could it be
        evaluated), ``observed`` and ``threshold``. Precipitation/temperature/
        wind reuse the in-memory weather-client cache, so this is normally cheap.

        ``run_start`` is the run being asked about. The precipitation guard's
        window starts at its local date. Only dispatch leaves it out, meaning now;
        every preview names a moment, because the guard logs an uncovered run
        date at INFO when none is named.
        """
```

In der Liste `checks = [` ersetzen:

```python
            await self._eval_precipitation(config),
```

durch:

```python
            await self._eval_precipitation(config, run_start),
```

- [ ] **Step 4: Gemeinsame Auswahl des nächsten Laufs**

In `skip_conditions.py` direkt vor `    @staticmethod` / `    def _project_days_between_to_next_run(` einfügen:

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
        ``skip_preview`` is evaluated live (as of now — forecasts may change
        before the run). ``last_skip_evaluation`` is the persisted result of the
        most recent real scheduled-irrigate decision (None until one has run, or
        after a restart).
        """
        config = await self.store.async_get_config()
        skip_preview = await self.async_evaluate_skip_conditions()
        upcoming = await self.recurring_schedule_manager.async_get_upcoming_runs()
```

durch:

```python
        ``skip_preview`` is evaluated live against the current forecast, for the
        next scheduled irrigate run (forecasts may still change before it).
        ``last_skip_evaluation`` is the persisted result of the most recent real
        scheduled-irrigate decision (None until one has run, or after a restart).
        """
        config = await self.store.async_get_config()
        upcoming = await self.recurring_schedule_manager.async_get_upcoming_runs()
        # The precipitation guard's window starts at the run's date, so ask about
        # the next run rather than about now: opened in the evening, "now" would
        # examine today for a run that waters tomorrow. With no run scheduled it
        # still names a moment, because only dispatch names none.
        skip_preview = await self.async_evaluate_skip_conditions(
            run_start=self._next_irrigate_run_utc(upcoming) or dt_util.utcnow()
        )
```

- [ ] **Step 6: Vorschau reicht ihren Start durch**

In `scheduler.py`, `_projected_skip`, ersetzen:

```python
        Evaluated through ``async_evaluate_skip_conditions`` - the same call
        ``_check_skip_conditions`` makes before every scheduled dispatch, minus
        its logging and its persistence - so a guard that early-returns for the
        runner early-returns identically here. The days-between counter is
        advanced to the run's own date first, exactly as the dashboard preview
        does, because it is a day counter and reading it as of now would report
        a skip the run will not perform.
        """
        evaluation = await self.coordinator.async_evaluate_skip_conditions()
```

durch:

```python
        Evaluated through ``async_evaluate_skip_conditions`` - the same call
        ``_check_skip_conditions`` makes before every scheduled dispatch, minus
        its logging and its persistence - so a guard that early-returns for the
        runner early-returns identically here. It names this run's start, because
        the precipitation guard's window starts at the run's date; without a
        start it names now, since only dispatch names none. The days-between
        counter is advanced to the run's own date first, exactly as the dashboard
        preview does, because it is a day counter and reading it as of now would
        report a skip the run will not perform.
        """
        evaluation = await self.coordinator.async_evaluate_skip_conditions(
            run_start=start if start is not None else dt_util.utcnow()
        )
```

- [ ] **Step 7: Tests grün, benachbarte Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_skip_run_start_threading.py tests/test_days_between_preview.py tests/test_precipitation_guard.py tests/test_next_irrigation_sensor.py tests/test_init.py tests/test_soil_moisture_veto.py -p _local_socket_unblock -q -rf`
Expected: neue Tests PASS; FAILED nur die Basis-Namen aus `test_init.py` und `test_next_irrigation_sensor.py`.

- [ ] **Step 8: Mutationsproben**

1. `await self._eval_precipitation(config, run_start),` → `await self._eval_precipitation(config),` → `test_evaluation_hands_the_run_start…` FAIL.
2. In `_projected_skip` `run_start=start if start is not None else dt_util.utcnow()` → `run_start=start` → `test_a_projection_without_a_start_still_names_a_moment` FAIL; das ganze Argument entfernen → zusätzlich `test_the_schedule_projection_asks…` FAIL.
3. Im Ausblick `run_start=self._next_irrigate_run_utc(upcoming) or dt_util.utcnow()` → `run_start=self._next_irrigate_run_utc(upcoming)` → `test_with_no_irrigate_run_the_outlook_still_names_a_moment` FAIL; das ganze Argument entfernen → zusätzlich `test_the_outlook_asks…` FAIL.

- [ ] **Step 9: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_skip_run_start_threading.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/scheduler.py tests/test_skip_run_start_threading.py
git commit -F - <<'EOF'
fix(skip): previews ask the precipitation guard about the run they preview

The guard's window now starts at the run's date, so every caller has to name
the run. Dispatch still means now by naming none. The schedule projection
passes its planned start, and the dashboard outlook passes the next scheduled
irrigate run -- opened in the evening, "now" would have examined today for a run
that waters tomorrow. A preview without a run to name passes the current moment,
so the guard's INFO log for an uncovered run date stays with dispatch.

The outlook and the days-between projection now share one selection of the
next irrigate run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8: (entfällt — der Abendlauf-Pin steckt in Task 6, `test_an_evening_run_with_a_one_day_window…`)

---

### Task 9: Hilfetext je Modus, Doku, dist

**Files:**
- Modify: `custom_components/irrigation_plus/frontend/src/views/general/view-general.ts:708`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json` (`weather_skip.lookahead_help`)
- Modify: `docs/configuration-when-to-water.md:42`, `docs/configuration-weather-location.md:26`
- Modify: `custom_components/irrigation_plus/frontend/dist/*` (Build)
- Test: `custom_components/irrigation_plus/frontend/src/views/general/view-general.test.ts`

- [ ] **Step 1: Fehlschlagende vitest-Tests anhängen** (ans Dateiende)

```typescript
describe("view-general: the look-ahead help follows the rain mode", () => {
  // The same setting serves two modes that count from different days: the skip
  // guard from the run's own date, forecast weighting from the day after the
  // calculation. One help text was wrong for one of them.
  function weatherView(config: any) {
    const el: any = new View();
    el.hass = { language: "en" };
    el.config = { precipitation_forecast_days: 1, ...config };
    el.data = {};
    el.requestUpdate = () => {};
    return el;
  }

  it("counts from the run's own date when the run is skipped on rain", () => {
    const text = flatten(
      weatherView({
        skip_irrigation_on_precipitation: true,
      })._renderWeatherSkipCard(),
    );
    expect(text).toContain("starting with the day the run takes place");
    expect(text).not.toContain("starting with the day after the calculation");
  });

  it("counts from the day after the calculation when rain only shortens the run", () => {
    const text = flatten(
      weatherView({
        skip_irrigation_on_precipitation: false,
        forecast_weighting_enabled: true,
      })._renderWeatherSkipCard(),
    );
    expect(text).toContain("starting with the day after the calculation");
    expect(text).not.toContain("starting with the day the run takes place");
  });
});
```

- [ ] **Step 2: Tests laufen rot, Lint sauber**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
npx vitest run src/views/general/view-general.test.ts
npm run lint
```
Expected: die zwei neuen Tests FAIL an `toContain` (alter Text „How many upcoming forecast days …“). **Muss eine Assertion sein, keine Render-Exception.** `npm run lint` ohne Beanstandung (prettier bricht sonst später den Build).

- [ ] **Step 3: Kataloge umbauen (Skript, schreibt über temporäre Datei, erhält Zeilenende)**

Skriptdatei mit dem Write-Tool anlegen: `D:\Entwicklung\HASI\pr2-work\lookahead_i18n.py`

```python
import json, os, pathlib, sys
base = pathlib.Path(sys.argv[1])
new = {
    "en": (
        "How many days of forecast to add up when checking for rain, starting with the day the run takes place: 1 = the day of the run, 2 = that day and the next, and so on. Hours that have already passed are not forecast and do not count, so a run that starts in the evening needs 2 to see the next morning.",
        "How many forecast days to add up when shortening the run, starting with the day after the calculation: 1 = that day, 2 = that day and the next, and so on.",
    ),
    "de": (
        "Wie viele Vorhersagetage beim Regen-Check zusammengezählt werden, beginnend mit dem Tag, an dem der Lauf stattfindet: 1 = der Tag des Laufs, 2 = dieser Tag und der nächste usw. Bereits vergangene Stunden werden nicht vorhergesagt und zählen nicht mit; ein Lauf am Abend braucht deshalb 2, um den nächsten Morgen zu sehen.",
        "Wie viele Vorhersagetage beim Kürzen des Laufs zusammengezählt werden, beginnend mit dem Tag nach der Berechnung: 1 = dieser Tag, 2 = dieser Tag und der nächste usw.",
    ),
    "es": (
        "Cuántos días de previsión se suman al comprobar la lluvia, empezando por el día en que se realiza el riego: 1 = el día del riego, 2 = ese día y el siguiente, etc. Las horas ya pasadas no se prevén y no cuentan, así que un riego que empieza por la noche necesita 2 para ver la mañana siguiente.",
        "Cuántos días de previsión se suman al acortar el riego, empezando por el día siguiente al cálculo: 1 = ese día, 2 = ese día y el siguiente, etc.",
    ),
    "fr": (
        "Nombre de jours de prévision additionnés lors de la vérification de la pluie, en commençant par le jour de l'arrosage : 1 = le jour de l'arrosage, 2 = ce jour et le suivant, etc. Les heures déjà écoulées ne sont pas prévues et ne comptent pas ; un arrosage qui démarre le soir a donc besoin de 2 pour voir le lendemain matin.",
        "Nombre de jours de prévision additionnés pour raccourcir l'arrosage, en commençant par le jour qui suit le calcul : 1 = ce jour, 2 = ce jour et le suivant, etc.",
    ),
    "it": (
        "Quanti giorni di previsione sommare nel controllo della pioggia, a partire dal giorno dell'irrigazione: 1 = il giorno dell'irrigazione, 2 = quel giorno e il successivo, e così via. Le ore già trascorse non sono previste e non vengono contate, quindi un'irrigazione che parte la sera ha bisogno di 2 per vedere la mattina seguente.",
        "Quanti giorni di previsione sommare per accorciare l'irrigazione, a partire dal giorno successivo al calcolo: 1 = quel giorno, 2 = quel giorno e il successivo, e così via.",
    ),
    "nl": (
        "Hoeveel verwachtingsdagen worden opgeteld bij de regencontrole, te beginnen met de dag waarop wordt beregend: 1 = de dag van de beregening, 2 = die dag en de volgende, enzovoort. Voor uren die al voorbij zijn, is er geen verwachting en ze tellen niet mee; een beregening die 's avonds start, heeft daarom 2 nodig om de volgende ochtend te zien.",
        "Hoeveel verwachtingsdagen worden opgeteld om de beregening in te korten, te beginnen met de dag na de berekening: 1 = die dag, 2 = die dag en de volgende, enzovoort.",
    ),
    "no": (
        "Hvor mange varseldøgn som summeres ved regnsjekken, fra og med dagen vanningen skjer: 1 = vanningsdagen, 2 = den dagen og neste, og så videre. Timer som allerede er passert, varsles ikke og telles ikke med, så en vanning som starter om kvelden trenger 2 for å se neste morgen.",
        "Hvor mange varseldøgn som summeres når vanningen forkortes, fra og med dagen etter beregningen: 1 = den dagen, 2 = den dagen og neste, og så videre.",
    ),
    "sk": (
        "Koľko dní predpovede sa spočíta pri kontrole dažďa, počnúc dňom zavlažovania: 1 = deň zavlažovania, 2 = tento deň a nasledujúci atď. Hodiny, ktoré už uplynuli, sa nepredpovedajú a nezapočítavajú sa, preto zavlažovanie, ktoré začína večer, potrebuje 2, aby videlo nasledujúce ráno.",
        "Koľko dní predpovede sa spočíta pri skracovaní zavlažovania, počnúc dňom po výpočte: 1 = tento deň, 2 = tento deň a nasledujúci atď.",
    ),
}
for lang, (skip, water_less) in new.items():
    p = base / f"{lang}.json"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if l.lstrip().startswith('"lookahead_help"')]
    assert len(hits) == 1, (lang, hits)
    i = hits[0]
    old = lines[i]
    indent = old[: len(old) - len(old.lstrip())]
    ending = "," if old.rstrip().endswith(",") else ""
    nl = "\r\n" if old.endswith("\r\n") else "\n"
    child = indent + "  "
    lines[i : i + 1] = [
        f'{indent}"lookahead_help": {{{nl}',
        f'{child}"skip": {json.dumps(skip, ensure_ascii=False)},{nl}',
        f'{child}"water_less": {json.dumps(water_less, ensure_ascii=False)}{nl}',
        f"{indent}}}{ending}{nl}",
    ]
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(lines), encoding="utf-8", newline="")
    os.replace(tmp, p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert set(data["weather_skip"]["lookahead_help"]) == {"skip", "water_less"}, lang
    print(lang, "ok")
```

Ausführen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
./.venv/Scripts/python.exe /d/Entwicklung/HASI/pr2-work/lookahead_i18n.py custom_components/irrigation_plus/frontend/localize/languages
```
Expected: acht Zeilen `<lang> ok`.

- [ ] **Step 4: TS umstellen**

In `view-general.ts` ersetzen:

```typescript
                  ${localize("weather_skip.lookahead_help", lang)}
```

durch:

```typescript
                  ${localize(`weather_skip.lookahead_help.${rainMode}`, lang)}
```

- [ ] **Step 5: Doku**

In `docs/configuration-when-to-water.md` die Zeile

```markdown
For *Water less* and *Skip watering* you also set the **Forecast look-ahead (days)** — how many upcoming forecast days are added together. The forecast starts at *tomorrow* (today is excluded), so `1` (the default) means just the next day, `2` the next two days, and so on.
```

ersetzen durch:

```markdown
For *Water less* and *Skip watering* you also set the **Forecast look-ahead (days)** — how many forecast days are added together. The two modes count from different days. *Skip watering* starts with the day the run takes place: `1` (the default) means the day of the run, `2` that day and the next, and so on. Hours already past do not count, so a run that starts in the evening needs `2` to see the next morning. *Water less* is applied when the duration is calculated and starts with the day after the calculation.
```

In `docs/configuration-weather-location.md` die Zeile

```markdown
A card with the coming days from your weather service: minimum/maximum temperature, expected precipitation and wind speed. This is the same forecast data the precipitation skip condition evaluates.
```

ersetzen durch:

```markdown
A card with the coming days from your weather service: minimum/maximum temperature, expected precipitation and wind speed. The precipitation skip condition reads the same service, but its hourly forecast first and these days only beyond it, counted by local day from the time of the check — so its figure is not the sum of these rows.
```

- [ ] **Step 6: Alte Aussage ist überall weg**

```bash
grep -rn -E "today is excluded|heute ausgeschlossen|hoy se excluye|aujourd'hui est exclu|oggi è escluso|vandaag wordt uitgesloten|i dag utelates|dnešok je vylúčený" custom_components/irrigation_plus/frontend/localize/languages/ custom_components/irrigation_plus/const.py docs/ || echo "keine alte Formulierung mehr"
```
Expected: `keine alte Formulierung mehr` (setzt Task 6 voraus, dort wird `const.py` geändert).

- [ ] **Step 7: Tests grün, Lint grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend && npx vitest run src/views/general/view-general.test.ts && npm run lint
cd /d/Entwicklung/HASI/HAsmartirrigation && ./.venv/Scripts/python.exe -m pytest tests/test_i18n_completeness.py -p _local_socket_unblock -q
```
Expected: vitest alle PASS; lint ohne Beanstandung; i18n alle PASS (Probelauf: 65 passed — Schlüsselparität, keine englischen Kopien, Platzhalter).

- [ ] **Step 8: Mutationsprobe**

`view-general.ts` zurück auf `localize("weather_skip.lookahead_help", lang)` → beide neuen vitest-Tests FAIL.

- [ ] **Step 9: dist bauen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend && npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation && git status --short custom_components/irrigation_plus/frontend/dist/ && git diff --stat -- custom_components/irrigation_plus/frontend/dist/
```
Expected: Build erfolgreich (lint + rollup). Inhaltlich geändert: `irrigation-plus.js` und `irrigation-plus-card-impl.js` (Probelauf); die anderen zwei Bundles können nur als Zeilenende-Änderung erscheinen.

- [ ] **Step 10: Commit**

```bash
git add custom_components/irrigation_plus/frontend/localize/languages/*.json custom_components/irrigation_plus/frontend/src/views/general/view-general.ts custom_components/irrigation_plus/frontend/src/views/general/view-general.test.ts docs/configuration-when-to-water.md docs/configuration-weather-location.md
git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-legacy.js
git commit -F - <<'EOF'
i18n(skip): the look-ahead help names the day each rain mode counts from

The look-ahead setting serves two modes. Skipping on rain now counts from the
run's own date and ignores hours already past; forecast weighting still sums
the daily forecast from the day after the calculation. One help text said
"starts tomorrow" for both, which would now be wrong for the skip.

The help is split per mode in all eight catalogues, the panel picks the one for
the selected mode, and the user docs say the same. The skip text also says that
a run starting in the evening needs two days to see the next morning, and the
forecast card's docs no longer call the skip's figure the same data.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Volle Suite, Lint, Geschwister-Prüfung

- [ ] **Step 1: Lint**

```bash
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

- [ ] **Step 2: Suite gegen Basis**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/after-pr2.txt
grep "^FAILED" /d/Entwicklung/HASI/baseline-pr2.txt | sort > /d/Entwicklung/HASI/pr2-work/b2.txt
grep "^FAILED" /d/Entwicklung/HASI/after-pr2.txt | sort > /d/Entwicklung/HASI/pr2-work/a2.txt
diff /d/Entwicklung/HASI/pr2-work/b2.txt /d/Entwicklung/HASI/pr2-work/a2.txt && echo "IDENTISCHE Vorbestands-Fehler"
tail -1 /d/Entwicklung/HASI/baseline-pr2.txt; tail -1 /d/Entwicklung/HASI/after-pr2.txt
```
Expected: identische FAILED-Namen; `passed` +49 (25 Fenster, 2 Panel, 4 Met Office, 13 Wächter, 5 Durchreichen); Errors 320. Abweichung am Endstand erklären, nicht wegreden.

- [ ] **Step 3: vitest gesamt gegen Basis**

```bash
cd custom_components/irrigation_plus/frontend && npx vitest run 2>&1 | tail -5
```
Expected: gegenüber `baseline-pr2-vitest.txt` +2 passed, keine neuen Fehler.

- [ ] **Step 4: Frontend-Build reproduzierbar**

```bash
cd custom_components/irrigation_plus/frontend && npm run build && cd /d/Entwicklung/HASI/HAsmartirrigation && git diff --quiet -- custom_components/irrigation_plus/frontend/dist/ && echo "dist in sync"
```

- [ ] **Step 5: Geschwister-Checks**

```bash
grep -rn "forecast_data\[:days\]\|fd\[:days\]" custom_components/irrigation_plus/*.py
grep -rn "_cached_hourly or self._cached_three_hourly" custom_components/irrigation_plus/ || echo "Met Office: kein direkter Dokument-Vorzug mehr"
grep -rn "FORECAST_DAY_START\|FORECAST_DAY_END" custom_components/irrigation_plus/*.py
grep -rn "async_evaluate_skip_conditions(" custom_components/irrigation_plus/*.py
```
Expected:
- `fd[:days]` nur in `calculation.py` (Gewichtung, **bewusst unverändert**).
- Kein direkter Met-Office-Vorzug mehr.
- `FORECAST_DAY_*` (die Clients liegen in `weathermodules/` und werden von diesem Glob nicht erfasst) nur in `const.py`, `forecast_window.py` und als Docstring-Erwähnung in `websockets.py`.
- `async_evaluate_skip_conditions(`: nur `_check_skip_conditions` ruft ohne Argument, alle anderen Aufrufer mit `run_start=`.

- [ ] **Step 6: Keine Branch-SHAs in Kommentaren**

```bash
git diff fix/dated-daily-forecast --unified=0 -- 'custom_components/irrigation_plus/*.py' 'custom_components/irrigation_plus/weathermodules/*.py' tests/ | grep -E "^\+.*\b[0-9a-f]{8}\b" || echo "keine SHAs"
```

---

### Task 11: Texte nach außen, Basis, Archiv (Freigabe nötig)

- [ ] **Step 1: Basis klären (User):** auf #145 gestapelt öffnen oder Merge von #144/#145 abwarten und dann master hineinmergen (kein Rebase gepushter Branches).
- [ ] **Step 2: PR-Text entwerfen** (englisch). Inhalt:
  - Wurzel, Live-Fall als Tabelle, JustChrs Form („keyed on the run's date").
  - Wie gerechnet wird:
    - Stundenreihe zuerst.
    - Tageseinträge nur, wenn sie nach dem Ende der Reihe beginnen, mit OWM-Begründung inkl. 00Z-Slot.
    - Lücken zählen als Löcher.
    - Ein gescheiterter Abruf entscheidet nicht.
  - Met-Office-Dokumentwahl als eigener Commit; heilt `live_estimate` mit.
  - **Jede nicht abschaltbare Verhaltensänderung mit Reichweite:**
    - Abendläufe mit Fenster 1 sehen nur den Rest ihres Tages.
    - Ist das Laufdatum nicht abgedeckt, entscheidet der Wächter nicht (INFO-Log beim Dispatch).
    - Die Chip-Zahl ist nicht die Summe der Panel-Zeilen.
    - Das Panel beschriftet kaputte Spannen nach Position.
    - Der Hilfetext ist je Modus getrennt.
  - „Forecast weighting unchanged (same blind spot under `before_run`)".
  - Tests mit Mutationstabelle; Suite- und vitest-Zahlen am Endstand gemessen.
  - `Closes #137`. Ende `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3: Kommentar für #137 entwerfen**: Abendlauf-Konsequenz der Form; Satz zur Gewichtung unter `before_run`; Verweis auf #144/#145/PR 2.
- [ ] **Step 4: Beide Texte im Chat zeigen, Freigabe abwarten.**
- [ ] **Step 5: Nach Freigabe:** `git push -u origin fix/rain-guard-run-date`; `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/rain-guard-run-date --title "Examine rain on the run's own date, not the day after it" --body-file <datei>`.
- [ ] **Step 6: Regel P1:** Spec (mit Nachtrag) und diesen Plan auf `archive/design-history` pushen (Rezept Projekt-`CLAUDE.md`).

---

### Task 12: Live-Test (Freigabe nötig, nach Task 10)

Kriterien sind vor dem Test festgelegt, das Vorgehen stimmt der User ab (Einspielen auf HA-Test, Neustart nur mit Freigabe).

- [ ] **Step 1: Weg klären (User):** HA-Test (Open-Meteo) mit dem Branch-Stand bespielen, oder bis zum nächsten Produktiv-Release warten.
- [ ] **Step 2: HA-Test, beobachtbare Kriterien**
  - **Hilfetext:** In den Einstellungen „Wann bewässern“ zeigt „Überspringen“ den neuen deutschen Text, „Weniger bewässern“ den anderen. Vorher den Refresh-Drill machen (Strg+F5), denn Nicht-Englisch wird nur über `VERSION` neu geladen.
  - **Chip:** Der Niederschlags-Chip im Ausblick entspricht der Summe der Open-Meteo-Stundenwerte für das Ortsdatum des nächsten Laufs, ab dem Abfragezeitpunkt. Die Gegenrechnung kommt aus der Open-Meteo-API mit den Koordinaten von HA-Test (Stundenreihe `precipitation`, `timezone=auto`); Toleranz ±0,05 mm.
  - **Log:** keine Exception aus `skip_conditions` / `forecast_window`.
- [ ] **Step 3: HA-Prod (eigene Freigabe):** Nach dem Release prüft der erste Sunrise-Lauf mit Regen im Fenster, dass der Verlauf `precipitation` am Regentag selbst zeigt und nicht am Vortag.
