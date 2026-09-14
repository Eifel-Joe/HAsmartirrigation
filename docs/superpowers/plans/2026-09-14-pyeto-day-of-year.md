# PyETO-Tag aus den Wetterdaten — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PyETO rechnet Sonnenstand und Strahlung mit dem Tag, zu dem die Wetterdaten gehören, statt mit dem Tag der Uhr — in der täglichen Berechnung, der Live-Schätzung, den Vorhersagetagen und dem Bewässerungskalender.

**Architecture:** Eine Regel `weather_day(window_start, window_end)` in `weather_aggregate.py` bestimmt den Tag eines Wetterfensters (Datum von Beginn plus zwölf Stunden). `PyETO.calculate_et_for_day` und `PyETO.calculate` bekommen den Tag als optionalen keyword-only Parameter; ohne ihn bleibt das Verhalten unverändert. Die drei Produktionsaufrufer übergeben ihn; der Tag reist nur als Argument, nie als Zustand am geteilten Modulobjekt.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component, pytest, freezegun.

**Spec:** `docs/superpowers/specs/2026-09-14-pyeto-day-of-year-design.md` (Branch `archive/design-history`, `6232a0e8`).

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`. Branch `fix/pyeto-day-of-year` von `upstream/master` (`437042a7`). Eigener Upstream-PR, **nicht** PR #140.
- Test-Kommando: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint: `uvx black custom_components/irrigation_plus/ <testdateien>` und `uvx ruff check custom_components/irrigation_plus/`
- Lokale Env: viele Tests enden mit Teardown-`ERROR` „Lingering timer ... _reset_event_fired_today“ — vorbestehend, nur `FAILED`-Zeilen vergleichen. Vorbestands-Fehler **immer gegen die Basis vom selben Tag** vergleichen.
- `tests/test_live_estimate_replayed_balance.py::TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one` ist ohne Fix seit 2026-09-14 auf dem echten Datum rot. Das ist der Fehler, den dieser Plan behebt.
- **Mutationsprobe Pflicht**; Wiederherstellen per Byte-Backup + `sha256sum -c`, nicht `git checkout --`.
- Commits englisch, Ende: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Kommentare und Docstrings beschreiben, was der Code tut; keine Historie, keine SHAs des Arbeitsbranches.
- `push` und PR nur nach Freigabe im Chat.

## Dateien

| Datei | Änderung |
|---|---|
| `custom_components/irrigation_plus/weather_aggregate.py` | neue Funktion `weather_day` (Task 1) |
| `custom_components/irrigation_plus/calcmodules/pyeto/__init__.py` | `calculate_et_for_day(..., day=None)`, `calculate(..., day=None, forecast_first_day=None)` (Task 2) |
| `custom_components/irrigation_plus/calculation.py` | `calculate_module` übergibt `day` und `forecast_first_day` (Task 3) |
| `custom_components/irrigation_plus/live_estimate.py` | `_composed_day_et` rechnet PyETO und Hargreaves-Ersatz mit `weather_day(anchor, now)` (Task 3) |
| `custom_components/irrigation_plus/watering_calendar.py` | jeder Monat mit `date(2024, month, 15)` (Task 4) |
| `tests/test_weather_aggregate.py` | `TestWeatherDay`, 4 Tests (Task 1) |
| `tests/test_pyeto_day_of_year.py` | neu, 4 Tests (Task 2) |
| `tests/test_solrad_clamp_warning.py` | Clamp-Test mit festem Hochsommertag (Task 2) |
| `tests/test_live_estimate_replayed_balance.py` | Helper `_committed_daily_et` mit Tag, 2 neue Klassen mit je 2 Tests (Task 3) |
| `tests/test_watering_calendar.py` | 2 Tests (Task 4) |

---

### Task 0: Branch und Basis

- [ ] **Step 1: Branch von upstream**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --branch
git fetch upstream
git log --oneline -1 upstream/master
git checkout -b fix/pyeto-day-of-year upstream/master
mkdir -p /d/Entwicklung/HASI/mutation-backup
```
Expected: Arbeitsbaum sauber (untracked `docs/SESSION-STAND.md` ok); `upstream/master` = `437042a7`. Hat sich `upstream/master` bewegt, STOP und prüfen, ob upstream den Fehler selbst angefasst hat (`git log -S "datetime.datetime.now().timetuple().tm_yday" 437042a7..upstream/master`).

- [ ] **Step 2: Basis messen (am selben Tag wie Task 5)**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/baseline-pyeto.txt
date; tail -1 /d/Entwicklung/HASI/baseline-pyeto.txt
grep -c "^FAILED" /d/Entwicklung/HASI/baseline-pyeto.txt
```
Expected: die Zeile `FAILED tests/test_live_estimate_replayed_balance.py::TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one` ist in der Liste enthalten.

### Task 1: Regel für den Tag eines Wetterfensters

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (neue öffentliche Funktion `weather_day` direkt nach `_window_bounds`)
- Test: `tests/test_weather_aggregate.py` (neue Klasse `TestWeatherDay` am Dateiende)

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_weather_aggregate.py` den Import-Block ersetzen. Aus

```python
import datetime

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.weather_aggregate import (
    aggregate_window,
    select_window,
)
```

wird

```python
import datetime

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.weather_aggregate import (
    aggregate_window,
    select_window,
    weather_day,
)
```

Dann ans Dateiende, nach der letzten Zeile von `test_weather_service_precip_is_unaffected_by_the_guard` (`        assert out[const.MAPPING_PRECIPITATION] == 1.0  # 1 mm/h over 1 h`), anhängen:

```python


class TestWeatherDay:
    """The calendar day a window's readings are priced as."""

    @pytest.mark.parametrize(
        ("start", "end", "expected"),
        [
            pytest.param(
                datetime.datetime(2026, 5, 21, 23, 0),
                datetime.datetime(2026, 5, 22, 23, 0),
                datetime.date(2026, 5, 22),
                id="started-late-the-evening-before",
            ),
            pytest.param(
                datetime.datetime(2026, 5, 22, 6, 0),
                datetime.datetime(2026, 5, 23, 6, 0),
                datetime.date(2026, 5, 22),
                id="ends-the-next-morning",
            ),
            pytest.param(
                datetime.datetime(2026, 5, 22, 2, 0),
                datetime.datetime(2026, 5, 23, 2, 0),
                datetime.date(2026, 5, 22),
                id="ends-in-the-small-hours",
            ),
        ],
    )
    def test_a_window_belongs_to_the_day_twelve_hours_after_its_start(
        self, start, end, expected
    ):
        assert weather_day(start, end) == expected

    def test_a_window_without_a_start_belongs_to_the_day_it_ends(self):
        end = datetime.datetime(2026, 5, 23, 2, 0)
        assert weather_day(None, end) == datetime.date(2026, 5, 23)
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate.py::TestWeatherDay -p _local_socket_unblock -q`
Expected: FAIL beim Sammeln, `ImportError: cannot import name 'weather_day' from 'custom_components.irrigation_plus.weather_aggregate'`, Zusammenfassung `ERROR tests/test_weather_aggregate.py` / `1 error`.

- [ ] **Step 3: Funktion schreiben**

Das Modul importiert `import datetime` (kein nacktes `timedelta`) und schreibt überall `datetime.timedelta(...)`. Deshalb bleibt der Import-Block unverändert, und die Funktion nutzt `datetime.timedelta`.

In `custom_components/irrigation_plus/weather_aggregate.py` ersetzen. Aus

```python
    if start is None or end is None or end <= start:
        return None, None
    return start, end


def _time_weighted_mean(times, values, start, end):
```

wird

```python
    if start is None or end is None or end <= start:
        return None, None
    return start, end


def weather_day(window_start, window_end):
    """Calendar day a weather window's readings belong to.

    The day of the window start plus 12 h. The commit and the live estimate
    share that start, since both measure from the zone's watermark. So both
    price the same day while the window is still open, and the projected day
    closes on the committed one. The window end cannot serve as the rule
    because the live estimate's end is always ``now``. For a 24 h window the
    start plus 12 h is its midpoint, and that falls on the calendar day
    holding at least half of the window's hours.

    Without a known start the date of the window end is the only anchor left.
    The date is taken in whatever timezone the datetimes carry; buffer stamps
    are naive local times. Reads no clock: the caller's ``now`` arrives as
    ``window_end``.
    """
    if window_start is not None:
        return (window_start + datetime.timedelta(hours=12)).date()
    return window_end.date()


def _time_weighted_mean(times, values, start, end):
```

- [ ] **Step 4: Tests laufen grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate.py::TestWeatherDay -p _local_socket_unblock -q`
Expected: `4 passed`.

- [ ] **Step 5: Ganze Testdatei**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate.py -p _local_socket_unblock -q`
Expected: `23 passed` (19 bestehende + 4 neue).

- [ ] **Step 6: Mutationsproben**

Vorher eine Byte-Sicherung anlegen:

```bash
cp custom_components/irrigation_plus/weather_aggregate.py /d/Entwicklung/HASI/mutation-backup/weather_aggregate.py.bak
sha256sum custom_components/irrigation_plus/weather_aggregate.py > /d/Entwicklung/HASI/mutation-backup/weather_aggregate.py.sha
```

Jede Mutation einzeln einsetzen und dann laufen lassen:
`./.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate.py::TestWeatherDay -p _local_socket_unblock -q`
Nach jeder Mutation zurücksetzen:

```bash
cp /d/Entwicklung/HASI/mutation-backup/weather_aggregate.py.bak custom_components/irrigation_plus/weather_aggregate.py
sha256sum -c /d/Entwicklung/HASI/mutation-backup/weather_aggregate.py.sha
```

Expected nach jedem Zurücksetzen: `custom_components/irrigation_plus/weather_aggregate.py: OK`.

1. Immer das Datum des Fensterendes: den ganzen Rumpf
   ```python
       if window_start is not None:
           return (window_start + datetime.timedelta(hours=12)).date()
       return window_end.date()
   ```
   durch `    return window_end.date()` ersetzen.
   Expected: `2 failed, 2 passed`, und zwar
   `test_a_window_belongs_to_the_day_twelve_hours_after_its_start[ends-the-next-morning]` FAIL und
   `test_a_window_belongs_to_the_day_twelve_hours_after_its_start[ends-in-the-small-hours]` FAIL.
   (Der 23:00-Fall besteht hier, weil dessen Ende auf demselben Tag liegt.)
2. Die +12 h weglassen: `        return (window_start + datetime.timedelta(hours=12)).date()` durch `        return window_start.date()` ersetzen.
   Expected: `1 failed, 3 passed`, und zwar
   `test_a_window_belongs_to_the_day_twelve_hours_after_its_start[started-late-the-evening-before]` FAIL.
3. Ohne Beginn die Uhr lesen: `    return window_end.date()` durch `    return datetime.date.today()` ersetzen.
   Expected: `1 failed, 3 passed`, und zwar
   `test_a_window_without_a_start_belongs_to_the_day_it_ends` FAIL.

Zum Schluss `sha256sum -c /d/Entwicklung/HASI/mutation-backup/weather_aggregate.py.sha` → `OK`, dann Step 5 erneut → `23 passed`.

- [ ] **Step 7: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_weather_aggregate.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weather_aggregate.py tests/test_weather_aggregate.py
git commit -F - <<'EOF'
feat: add weather_day, the calendar day a weather window belongs to

PyETO takes the day of year from the wall clock, so a window committed
after midnight is priced as the next day. weather_day derives the day
from the window itself: the date of its start plus 12 h, or the date of
its end when no start is known. It reads no clock, so the commit and the
live estimate price the same day for the same window start.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Expected: black `All done! ✨ 🍰 ✨` / `68 files left unchanged.`, ruff `All checks passed!`.

---

### Task 2: PyETO rechnet mit dem übergebenen Tag

Der Tag wird nur als Argument durchgereicht und nie auf der geteilten Modul-Instanz gespeichert. Dieser Task braucht `weather_day` aus Task 1 nicht.

**Files:**
- Modify: `custom_components/irrigation_plus/calcmodules/pyeto/__init__.py` (`PyETO.calculate`, `PyETO.calculate_et_for_day`)
- Modify: `tests/test_solrad_clamp_warning.py` (`TestTheCalculationPath::test_a_plausible_reading_warns_about_nothing`)
- Create: `tests/test_pyeto_day_of_year.py`

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Neue Datei `tests/test_pyeto_day_of_year.py`, vollständiger Inhalt:

```python
"""PyETO prices each day's weather with the sun of that day.

Extraterrestrial and clear-sky radiation depend on the day of the year, and with
an estimated solar radiation so does the whole Penman-Monteith result. The day
comes from the caller, as the day the weather belongs to; only a call without a
day falls back to the clock.
"""

import datetime
from statistics import mean

import pytest
from freezegun import freeze_time

from custom_components.irrigation_plus.calcmodules.pyeto import (
    MAPPING_DEWPOINT,
    MAPPING_MAX_TEMP,
    MAPPING_MIN_TEMP,
    MAPPING_PRESSURE,
    MAPPING_WINDSPEED,
    PyETO,
    SOLRAD_behavior,
)
from custom_components.irrigation_plus.const import (
    CONF_PYETO_FORECAST_DAYS,
    CONF_PYETO_SOLRAD_BEHAVIOR,
)

SUMMER_SOLSTICE = datetime.date(2026, 6, 21)
WINTER_SOLSTICE = datetime.date(2026, 12, 21)
# Around an equinox the solar declination changes fastest, so neighbouring days
# price the same weather measurably differently.
SPRING_EQUINOX = datetime.date(2026, 3, 20)


def _module(hass, forecast_days=0):
    return PyETO(
        hass,
        description="",
        config={
            # Estimated radiation, so the day of the year reaches the result
            # through the extraterrestrial radiation.
            CONF_PYETO_SOLRAD_BEHAVIOR: SOLRAD_behavior.EstimateFromTemp.value,
            CONF_PYETO_FORECAST_DAYS: forecast_days,
        },
    )


def _weather():
    # Every reading calculate_et_for_day requires; the solar radiation is
    # estimated from the temperatures.
    return {
        MAPPING_DEWPOINT: 12.0,
        MAPPING_MIN_TEMP: 14.0,
        MAPPING_MAX_TEMP: 28.0,
        MAPPING_WINDSPEED: 1.5,
        MAPPING_PRESSURE: 977.0,
    }


def _forecast():
    return {
        MAPPING_DEWPOINT: 9.0,
        MAPPING_MIN_TEMP: 11.0,
        MAPPING_MAX_TEMP: 24.0,
        MAPPING_WINDSPEED: 3.0,
        MAPPING_PRESSURE: 1005.0,
    }


class TestTheDayOfTheWeather:
    def test_the_same_weather_evaporates_more_in_june_than_in_december(self, hass):
        modinst = _module(hass)

        june = modinst.calculate_et_for_day(_weather(), day=SUMMER_SOLSTICE)
        december = modinst.calculate_et_for_day(_weather(), day=WINTER_SOLSTICE)

        # The delta is the negative ET, so more evaporation is the lower value.
        assert june < december

    def test_a_given_day_prices_like_the_clock_on_that_day(self, hass):
        modinst = _module(hass)

        with freeze_time(WINTER_SOLSTICE):
            by_clock = modinst.calculate_et_for_day(_weather())
        by_day = modinst.calculate_et_for_day(_weather(), day=WINTER_SOLSTICE)

        assert by_day == by_clock


class TestTheForecastDays:
    def test_each_forecast_entry_is_priced_one_day_further_out(self, hass):
        modinst = _module(hass, forecast_days=2)
        day = SPRING_EQUINOX
        first = SPRING_EQUINOX + datetime.timedelta(days=3)

        combined = modinst.calculate(
            _weather(), [_forecast(), _forecast()], day=day, forecast_first_day=first
        )

        assert combined == pytest.approx(
            mean(
                [
                    modinst.calculate_et_for_day(_weather(), day=day),
                    modinst.calculate_et_for_day(_forecast(), day=first),
                    modinst.calculate_et_for_day(
                        _forecast(), day=first + datetime.timedelta(days=1)
                    ),
                ]
            )
        )

    def test_without_a_first_forecast_day_the_forecast_starts_the_day_after(self, hass):
        modinst = _module(hass, forecast_days=1)
        day = SPRING_EQUINOX

        combined = modinst.calculate(_weather(), [_forecast()], day=day)

        assert combined == pytest.approx(
            mean(
                [
                    modinst.calculate_et_for_day(_weather(), day=day),
                    modinst.calculate_et_for_day(
                        _forecast(), day=day + datetime.timedelta(days=1)
                    ),
                ]
            )
        )
```

- [ ] **Step 2: Clamp-Test auf einen festen Tag setzen**

`test_a_plausible_reading_warns_about_nothing` hängt heute am Kalender. Mit der Breite der `hass`-Fixture (32.87336) liegt das Klarhimmel-Maximum am 21. Dezember bei 13.4 MJ/day/m2. Die 20.0 MJ/day/m2 des Tests werden dann gekappt und der Test wird rot.

In `tests/test_solrad_clamp_warning.py` ersetze

```python
"""

import logging
```

durch

```python
"""

import datetime
import logging
```

und ersetze

```python
        with caplog.at_level(logging.WARNING):
            modinst.calculate(weather, None)
```

durch

```python
        with caplog.at_level(logging.WARNING):
            # A mid-summer day, so 20 MJ/day/m2 stays below the clear-sky maximum.
            modinst.calculate(weather, None, day=datetime.date(2026, 6, 21))
```

- [ ] **Step 3: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pyeto_day_of_year.py tests/test_solrad_clamp_warning.py -p _local_socket_unblock -q`
Expected: FAIL, `5 failed, 4 passed`. Alle fünf scheitern mit `TypeError: PyETO.calculate_et_for_day() got an unexpected keyword argument 'day'` oder `TypeError: PyETO.calculate() got an unexpected keyword argument 'day'`:
- `tests/test_pyeto_day_of_year.py::TestTheDayOfTheWeather::test_the_same_weather_evaporates_more_in_june_than_in_december`
- `tests/test_pyeto_day_of_year.py::TestTheDayOfTheWeather::test_a_given_day_prices_like_the_clock_on_that_day`
- `tests/test_pyeto_day_of_year.py::TestTheForecastDays::test_each_forecast_entry_is_priced_one_day_further_out`
- `tests/test_pyeto_day_of_year.py::TestTheForecastDays::test_without_a_first_forecast_day_the_forecast_starts_the_day_after`
- `tests/test_solrad_clamp_warning.py::TestTheCalculationPath::test_a_plausible_reading_warns_about_nothing`

- [ ] **Step 4: `calculate_et_for_day` nimmt den Tag**

In `custom_components/irrigation_plus/calcmodules/pyeto/__init__.py` ersetze

```python
    def calculate_et_for_day(self, weather_data, *, warn_on_clamp=True):
        """Calculate the evapotranspiration delta for a single day's weather data.

        Args:
            weather_data: Dictionary containing weather data for the day..
            warn_on_clamp: whether a solar-radiation clamp may warn the user.
```

durch

```python
    def calculate_et_for_day(self, weather_data, *, day=None, warn_on_clamp=True):
        """Calculate the evapotranspiration delta for a single day's weather data.

        Args:
            weather_data: Dictionary containing weather data for the day..
            day: calendar day the weather belongs to, as a ``datetime.date``.
                Its day of the year sets the solar declination and with it the
                extraterrestrial and clear-sky radiation. Without a day the
                current date is used.
            warn_on_clamp: whether a solar-radiation clamp may warn the user.
```

und ersetze

```python
                day_of_year = datetime.datetime.now().timetuple().tm_yday
```

durch

```python
                day_of_year = (
                    (day if day is not None else datetime.datetime.now())
                    .timetuple()
                    .tm_yday
                )
```

- [ ] **Step 5: `calculate` reicht den Tag weiter und datiert die Vorhersage**

In derselben Datei ersetze

```python
    def calculate(self, weather_data, forecast_data, *, warn_on_clamp=True) -> float:
        """Calculate the average evapotranspiration delta for the given weather and forecast data.

        Args:
            weather_data: Dictionary containing current weather data.
            forecast_data: List of dictionaries containing forecasted weather data for upcoming days.
            warn_on_clamp: whether a solar-radiation clamp may warn the user.
                See :meth:`calculate_et_for_day`.
```

durch

```python
    def calculate(
        self,
        weather_data,
        forecast_data,
        *,
        day=None,
        forecast_first_day=None,
        warn_on_clamp=True,
    ) -> float:
        """Calculate the average evapotranspiration delta for the given weather and forecast data.

        Args:
            weather_data: Dictionary containing current weather data.
            forecast_data: List of dictionaries containing forecasted weather data for upcoming days.
            day: calendar day ``weather_data`` belongs to, as a ``datetime.date``.
                See :meth:`calculate_et_for_day`.
            forecast_first_day: calendar day of ``forecast_data[0]``; entry ``x``
                is priced ``x`` days later. Defaults to the day after ``day``,
                or to tomorrow when no ``day`` is given.
            warn_on_clamp: whether a solar-radiation clamp may warn the user.
                See :meth:`calculate_et_for_day`.
```

und ersetze

```python
        if weather_data:
            deltas.append(
                self.calculate_et_for_day(weather_data, warn_on_clamp=warn_on_clamp)
            )
            # loop over the forecast days
```

durch

```python
        if weather_data:
            deltas.append(
                self.calculate_et_for_day(
                    weather_data, day=day, warn_on_clamp=warn_on_clamp
                )
            )
            if forecast_first_day is None:
                base_day = day if day is not None else datetime.datetime.now().date()
                forecast_first_day = base_day + datetime.timedelta(days=1)
            # loop over the forecast days
```

und ersetze

```python
                        self.calculate_et_for_day(
                            forecast_data[x], warn_on_clamp=warn_on_clamp
                        )
```

durch

```python
                        self.calculate_et_for_day(
                            forecast_data[x],
                            day=forecast_first_day + datetime.timedelta(days=x),
                            warn_on_clamp=warn_on_clamp,
                        )
```

- [ ] **Step 6: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pyeto_day_of_year.py tests/test_solrad_clamp_warning.py -p _local_socket_unblock -q`
Expected: `9 passed`.

- [ ] **Step 7: Nachbar-Tests unverändert**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_solar_unit_and_clamp.py tests/test_summed_hourly_eto.py tests/test_live_estimate_without_hourly_calculation.py tests/test_watering_calendar.py tests/test_live_estimate_replayed_balance.py tests/unit/test_zone_calculate.py tests/test_live_estimate_from_buffer.py -p _local_socket_unblock -q`
Expected: keine neue FAILED-Zeile gegenüber upstream/master. Teardown-ERRORs „Lingering timer … `_reset_event_fired_today`" sind lokale Env-Artefakte und werden ignoriert. Einzige erlaubte FAILED-Zeile: `tests/test_live_estimate_replayed_balance.py::TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one`. Sie hängt schon auf upstream/master am Kalendertag und war am 2026-09-14 vor und nach diesem Task rot (`1 failed, 194 passed`). Geschlossen wird sie in Task 3.

- [ ] **Step 8: Mutationsproben**

Byte-Sicherung vorab:

```bash
cp custom_components/irrigation_plus/calcmodules/pyeto/__init__.py "/d/Entwicklung/HASI/mutation-backup/pyeto_init.py.bak"
sha256sum custom_components/irrigation_plus/calcmodules/pyeto/__init__.py > "/d/Entwicklung/HASI/mutation-backup/pyeto_init.py.sha"
```

Jede Mutation einzeln anwenden. Danach jeweils laufen lassen mit
`./.venv/Scripts/python.exe -m pytest tests/test_pyeto_day_of_year.py tests/test_solrad_clamp_warning.py -p _local_socket_unblock -q`
und zurücksetzen mit

```bash
cp "/d/Entwicklung/HASI/mutation-backup/pyeto_init.py.bak" custom_components/irrigation_plus/calcmodules/pyeto/__init__.py
sha256sum -c "/d/Entwicklung/HASI/mutation-backup/pyeto_init.py.sha"
```

Das muss `custom_components/irrigation_plus/calcmodules/pyeto/__init__.py: OK` ausgeben.

1. Tag ignoriert (immer Uhr):
   `sed -i 's/(day if day is not None else datetime.datetime.now())/(datetime.datetime.now())/' custom_components/irrigation_plus/calcmodules/pyeto/__init__.py`
   Expected: `2 failed, 7 passed`. Rot werden:
   - `TestTheDayOfTheWeather::test_the_same_weather_evaporates_more_in_june_than_in_december` (an jedem Tag)
   - `TestTheDayOfTheWeather::test_a_given_day_prices_like_the_clock_on_that_day` (an jedem Ausführungstag außer dem 21. Dezember)

   Der Clamp-Test fängt diese Mutation nur im Winter. Unter eingefrorener Uhr 2026-12-21 werden `test_the_same_weather_evaporates_more_in_june_than_in_december` und `test_a_plausible_reading_warns_about_nothing` rot.
2. Vorhersage-Versatz entfernt (alle Einträge am ersten Tag):
   `sed -i 's/day=forecast_first_day + datetime.timedelta(days=x),/day=forecast_first_day,/' custom_components/irrigation_plus/calcmodules/pyeto/__init__.py`
   Expected: `1 failed, 8 passed`, rot wird `TestTheForecastDays::test_each_forecast_entry_is_priced_one_day_further_out` (`comparison failed`).
3. Standard-Starttag = `day` statt `day` + 1:
   `sed -i 's/forecast_first_day = base_day + datetime.timedelta(days=1)/forecast_first_day = base_day/' custom_components/irrigation_plus/calcmodules/pyeto/__init__.py`
   Expected: `1 failed, 8 passed`, rot wird `TestTheForecastDays::test_without_a_first_forecast_day_the_forecast_starts_the_day_after` (`comparison failed`).

- [ ] **Step 9: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/calcmodules/pyeto/__init__.py tests/test_pyeto_day_of_year.py tests/test_solrad_clamp_warning.py
uvx ruff check custom_components/irrigation_plus/
git status
git diff
git add custom_components/irrigation_plus/calcmodules/pyeto/__init__.py tests/test_solrad_clamp_warning.py tests/test_pyeto_day_of_year.py
git commit -F - <<'EOF'
fix(pyeto): price each day's weather with that day's sun

PyETO took the day of the year from the clock, so the extraterrestrial and
clear-sky radiation applied to a day's weather followed the date the
calculation ran instead of the date the readings belong to.
calculate_et_for_day and calculate now accept the day as a keyword argument.
Forecast entries are priced one day further out each, starting at
forecast_first_day or the day after the weather's day. Without a day the
weather is still priced with today.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Expected: black `3 files left unchanged.`, ruff `All checks passed!`.

---

### Task 3: Berechnung und Live-Schätzung rechnen mit dem Tag ihres Fensters

Ein Task, weil die Schätzungstests Commit und Live-Schätzung auf Gleichheit vergleichen. Bekommt nur eine Seite den Tag des Fensters, laufen `TestEstimatedRadiationZonesRunTheirOwnCommitsEquation` und die Gleichheitstests in `tests/test_live_estimate_without_hourly_calculation.py` rot. Beide Seiten ändern sich deshalb in einem Commit.

Voraussetzung: Tasks 1 und 2 sind committet (`weather_day`, `PyETO.calculate(..., day=..., forecast_first_day=...)`).

In jedem Lauf gilt: Teardown-`ERROR` mit „Lingering timer … `_reset_event_fired_today`“ ist ein bekanntes Artefakt der lokalen Env und zählt nicht. Verglichen werden nur `FAILED`-Zeilen.

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (Import-Block `from .weather_aggregate import (` und der PyETO-Zweig in `calculate_module`)
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Import von `weather_day`; `_composed_day_et`)
- Test: `tests/test_live_estimate_replayed_balance.py` (Imports, Helper `_committed_daily_et`, neue Klasse `TestTheCommitPricesTheDayItsWindowCovers` direkt vor `class TestTheGapNarrowsAsTheWindowCloses:`, neue Klasse `TestTheEstimatePricesTheDayOfItsWindow` direkt vor `class TestThePostMidnightTail:`)

- [ ] **Step 1: Imports im Test ergänzen**

In `tests/test_live_estimate_replayed_balance.py` ersetzen:

```python
from custom_components.irrigation_plus.et_estimate import live_balance
```

durch

```python
from custom_components.irrigation_plus.et_estimate import (
    SiteGeometry,
    estimate_daily_et0_hargreaves,
    live_balance,
)
from custom_components.irrigation_plus.helpers import as_datetime
```

und

```python
from custom_components.irrigation_plus.store import SmartIrrigationStorage
```

durch

```python
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from custom_components.irrigation_plus.weather_aggregate import weather_day
```

- [ ] **Step 2: Der Test-Helfer bepreist den Commit mit demselben Tag wie die Produktion**

`_committed_daily_et` ruft PyETO direkt auf, ohne `calculate_module`. Er liest das Watermark der Zone so ein wie die Produktion (`helpers.as_datetime`). Ersetzen:

```python
async def _committed_daily_et(c, zone, now=WINDOW_END):
    """The whole-window evapotranspiration the commit books, in mm."""
    weatherdata, _ = await c._aggregate_for_zone(zone, now=now)
    instance = await c.getModuleInstanceByID(zone[const.ZONE_MODULE])
    delta = instance.calculate(weather_data=weatherdata, forecast_data=None)
```

durch

```python
async def _committed_daily_et(c, zone, now=WINDOW_END):
    """The whole-window evapotranspiration the commit books, in mm.

    Priced for the day the commit prices it for: the calendar day of the zone's
    consume watermark, parsed the way ``calculate_module`` parses it.
    """
    weatherdata, _ = await c._aggregate_for_zone(zone, now=now)
    instance = await c.getModuleInstanceByID(zone[const.ZONE_MODULE])
    day = weather_day(as_datetime(zone.get(const.ZONE_LAST_CONSUMED)), now)
    delta = instance.calculate(weather_data=weatherdata, forecast_data=None, day=day)
```

(Die Zeile `return -delta * (...)` darunter bleibt.)

- [ ] **Step 3: Fehlschlagende Tests für die Berechnung**

Direkt vor `class TestTheGapNarrowsAsTheWindowCloses:` einfügen. `datetime`, `Mock`, `freeze_time` und `pytest` sind in der Datei schon importiert.

```python
class TestTheCommitPricesTheDayItsWindowCovers:
    """The daily equation's solar geometry is read off the window, not the clock.

    ``now`` is handed to the commit explicitly in every case here, so the window
    is identical from run to run and the wall clock is the only thing left that
    could move the booked number.
    """

    async def test_the_same_window_books_the_same_delta_whatever_the_clock_says(
        self, coordinator
    ):
        c, store = coordinator
        zone, _, _ = await _estimating_zone(c, store, 2.0)

        deltas = []
        for clock in ("2026-05-23 02:00:00", "2026-12-21 12:00:00"):
            with freeze_time(clock):
                data = await _committed(c, zone, now=WINDOW_END)
            deltas.append(data[const.ZONE_DELTA])

        # Not vacuous: the window loses real water, and at this latitude late May
        # and midwinter differ several-fold in extraterrestrial radiation.
        assert deltas[0] < -0.5
        assert deltas[1] == pytest.approx(deltas[0], abs=1e-9)

    async def test_the_module_is_handed_the_windows_day_and_the_forecasts_first_day(
        self, coordinator
    ):
        """An early-morning commit: the window opened the previous morning, so its
        daylight belongs to the date before the commit's own, while the forecast
        still starts on the day after the commit."""
        c, store = coordinator
        zone, _, instance = await _estimating_zone(c, store, 2.0)
        watermark = datetime.datetime(2026, 5, 21, 6, 0)
        now = datetime.datetime(2026, 5, 22, 6, 0)
        zone[const.ZONE_LAST_CONSUMED] = watermark
        zone[const.ZONE_LAST_CALCULATED] = watermark
        instance.calculate = Mock(wraps=instance.calculate)

        data = await _committed(c, zone, now=now)

        kwargs = instance.calculate.call_args.kwargs
        assert kwargs.get("day") == datetime.date(2026, 5, 21)
        assert kwargs.get("forecast_first_day") == datetime.date(2026, 5, 23)
        # The wrapped module still priced the window, so the booked delta is real.
        assert data[const.ZONE_DELTA] < -0.5


```

`_estimating_zone` baut eine echte `PyETO`-Instanz mit `EstimateFromTemp`. `_hourly_et_for_zone` lehnt diese Konfiguration ab, deshalb läuft der Commit garantiert über `modinst.calculate`. `Mock(wraps=...)` umhüllt die Instanz nur, der echte Wert kommt weiterhin im Delta an.

- [ ] **Step 4: Fehlschlagende Tests für die Live-Schätzung**

Direkt vor `class TestThePostMidnightTail:` einfügen. Der Block endet wie in Step 3 mit zwei Leerzeilen:

```python
class TestTheEstimatePricesTheDayOfItsWindow:
    """The daily equation's solar geometry depends on the day of the year, and
    the day an estimate prices is the one its window's readings belong to. The
    wall clock at refresh time plays no part, so one window gives one figure
    whenever it is computed."""

    async def test_the_same_window_gives_the_same_figure_in_any_season(
        self, coordinator
    ):
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        midday = ANCHOR + timedelta(hours=10)

        figures = []
        for wall_clock in ("2026-05-22 12:00:00", "2026-12-21 12:00:00"):
            with freeze_time(wall_clock):
                implied, _est = _implied_daily(
                    c, store, zone, module, instance, midday, _hourly_forecast()
                )
            figures.append(implied)

        assert figures[0] > 0.5
        assert figures[1] == figures[0]

    async def test_the_hargreaves_stand_in_prices_the_windows_day(self, coordinator):
        """A window anchored at 02:00 is still open at 01:00 the next morning.
        Its readings belong to the anchor's day, so the stand-in is priced for
        that day and not for the date ``now`` has already reached."""
        c, store = coordinator
        zone, _module, _instance = await _estimating_zone(c, store, 2.0)
        now = WINDOW_END - timedelta(hours=1)
        low, high = 12.0, 26.0
        geometry = SiteGeometry(LAT, 0.0, ELEV, 0.0, datetime.timezone.utc)

        day = c._composed_day_et(
            zone,
            {const.MAPPING_MIN_TEMP: low, const.MAPPING_MAX_TEMP: high},
            {"hourly_forecast": _hourly_forecast()},
            anchor=ANCHOR,
            now=now,
            geometry=geometry,
            modinst=None,
        )

        windows_day = estimate_daily_et0_hargreaves(
            low, high, LAT, datetime.date(2026, 5, 22).timetuple().tm_yday
        )
        nows_day = estimate_daily_et0_hargreaves(
            low, high, LAT, datetime.date(2026, 5, 23).timetuple().tm_yday
        )
        assert windows_day != nows_day
        assert day[0] == windows_day


```

- [ ] **Step 5: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_live_estimate_replayed_balance.py::TestTheCommitPricesTheDayItsWindowCovers tests/test_live_estimate_replayed_balance.py::TestTheEstimatePricesTheDayOfItsWindow -p _local_socket_unblock -q`

Expected: `4 failed`:
- `test_the_same_window_books_the_same_delta_whatever_the_clock_says` FAIL, `assert -1.6786438838511741 == -4.624615153661553 ± 1.0e-09` (Dezember und Mai buchen dasselbe Fenster verschieden)
- `test_the_module_is_handed_the_windows_day_and_the_forecasts_first_day` FAIL, `AssertionError: assert None == datetime.date(2026, 5, 21)`
- `test_the_same_window_gives_the_same_figure_in_any_season` FAIL, `assert 1.67856 == 4.61424` (Dezember-Wert gegen Mai-Wert, gerundet)
- `test_the_hargreaves_stand_in_prices_the_windows_day` FAIL, `assert 5.243981921293758 == 5.231788347780426` (bepreist den 23.05. statt den 22.05.)

In diesem Zwischenstand rechnet der Helper aus Step 2 schon mit dem 22.05., Commit und Schätzung aber noch mit der Uhr. Weitere Tests der Datei können deshalb jetzt rot sein; Step 9 prüft sie nach der Umsetzung.

- [ ] **Step 6: Die Berechnung übergibt Tag und ersten Vorhersagetag**

In `custom_components/irrigation_plus/calculation.py` ersetzen:

```python
from .weather_aggregate import (
    aggregate_window,
    build_substeps,
    merge_latest_per_field,
    select_window,
)
```

durch

```python
from .weather_aggregate import (
    aggregate_window,
    build_substeps,
    merge_latest_per_field,
    select_window,
    weather_day,
)
```

(`timedelta` und `_as_datetime` sind in diesem Modul schon importiert: `from datetime import datetime, timedelta` und `from .helpers import as_datetime as _as_datetime`.)

In `calculate_module` ersetzen:

```python
        if m[const.MODULE_NAME] == "PyETO":
            if hourly is None:
                # pyeto expects pressure in hpa, solar radiation in mj/m2/day and wind speed in m/s
                delta = modinst.calculate(
                    weather_data=weatherdata, forecast_data=forecastdata
                )
```

durch

```python
        if m[const.MODULE_NAME] == "PyETO":
            if hourly is None:
                # pyeto expects pressure in hpa, solar radiation in mj/m2/day and wind speed in m/s
                delta = modinst.calculate(
                    weather_data=weatherdata,
                    forecast_data=forecastdata,
                    # The solar geometry of the day the window's readings belong
                    # to, not of the day this runs on: a window that opened
                    # yesterday morning and closes at dawn is yesterday's weather.
                    day=weather_day(
                        _as_datetime(zone.get(const.ZONE_LAST_CONSUMED)), now
                    ),
                    # Forecast rows are the days after the commit, whichever day
                    # the window itself was.
                    forecast_first_day=now.date() + timedelta(days=1),
                )
```

`now` ist an dieser Stelle schon aufgelöst (`if now is None: now = datetime.now()` weiter oben in derselben Funktion).

- [ ] **Step 7: Die Live-Schätzung rechnet mit dem Tag ihres Fensters**

In `custom_components/irrigation_plus/live_estimate.py` ersetzen:

```python
from .weather_aggregate import aggregate_window, build_substeps
```

durch

```python
from .weather_aggregate import aggregate_window, build_substeps, weather_day
```

In `_composed_day_et` ersetzen:

```python
        if low is None:
            return None
        if modinst is None:
            return (
                estimate_daily_et0_hargreaves(
                    low, high, geometry.latitude, now.timetuple().tm_yday
                ),
                tier,
            )
```

durch

```python
        if low is None:
            return None
        # Both equations below read solar geometry off the day of the year. The
        # day priced is the one the window's readings belong to, the same day the
        # commit prices this window for, so the figure does not move with the
        # wall clock and an estimate refreshed after midnight still prices the
        # day it is estimating.
        day = weather_day(anchor, now)
        if modinst is None:
            return (
                estimate_daily_et0_hargreaves(
                    low, high, geometry.latitude, day.timetuple().tm_yday
                ),
                tier,
            )
```

und im selben Methodenkörper ersetzen:

```python
        delta = modinst.calculate(
            weather_data=projected, forecast_data=None, warn_on_clamp=False
        )
```

durch

```python
        delta = modinst.calculate(
            weather_data=projected, forecast_data=None, day=day, warn_on_clamp=False
        )
```

Der Tag wird nur als Argument weitergereicht, nichts landet auf der geteilten Modul-Instanz. Die Proxy-Stufe in `_intraday_for_zone` (`doy = local.timetuple().tm_yday`) bleibt unverändert.

- [ ] **Step 8: Tests laufen grün**

Run: derselbe Befehl wie in Step 5.
Expected: `4 passed`.

- [ ] **Step 9: Beide Live-Estimate-Dateien komplett**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_live_estimate_replayed_balance.py tests/test_live_estimate_without_hourly_calculation.py -p _local_socket_unblock -q`
Expected: keine `FAILED`-Zeile, `117 passed`. Auch der Konvergenztest ist jetzt grün.

- [ ] **Step 10: Regression über alle Module, die `calculate_module` oder PyETO ausführen**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_calculate_module.py tests/test_coordinator_mixins.py tests/test_experimental_features.py tests/test_live_duration.py tests/test_live_estimate_replayed_balance.py tests/test_live_estimate_without_hourly_calculation.py tests/test_lumped_credit_drainage.py tests/test_manual_bucket_assertion.py tests/test_mid_window_bucket_credit.py tests/test_per_zone_consumption.py tests/test_prune_delta_baseline.py tests/test_run_in_flight.py tests/test_solar_ratio_hold.py tests/test_summed_hourly_eto.py tests/test_water_balance_substeps.py tests/test_zone_depth_defaults.py tests/test_solrad_clamp_warning.py tests/test_solar_unit_and_clamp.py -p _local_socket_unblock -q`
Expected: keine `FAILED`-Zeile.

- [ ] **Step 11: Mutationsproben**

Byte-Sicherungen vorab:

```bash
B=/d/Entwicklung/HASI/mutation-backup
for f in custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/live_estimate.py tests/test_live_estimate_replayed_balance.py; do
  n=$(basename "$f"); cp "$f" "$B/$n.bak"; sha256sum "$f" > "$B/$n.sha"
done
```

Nach jeder Probe die betroffene Datei zurückspielen (`cp "$B/<name>.bak" <datei>`) und `sha256sum -c "$B/<name>.sha"` muss `OK` melden.

Commit-Seite, jeweils geprüft mit `./.venv/Scripts/python.exe -m pytest tests/test_live_estimate_replayed_balance.py::TestTheCommitPricesTheDayItsWindowCovers -p _local_socket_unblock -q`:

1. In `calculation.py` das Argument `day=weather_day(...)` samt seinem dreizeiligen Kommentar entfernen → `2 failed`: `test_the_same_window_books_the_same_delta_whatever_the_clock_says` (`assert -1.6786438838511741 == -4.624615153661553 ± 1.0e-09`) und `test_the_module_is_handed_the_windows_day_and_the_forecasts_first_day` (`AssertionError: assert None == datetime.date(2026, 5, 21)`).
2. In `calculation.py` die drei Zeilen
   ```python
                       day=weather_day(
                           _as_datetime(zone.get(const.ZONE_LAST_CONSUMED)), now
                       ),
   ```
   durch `                    day=now.date(),` ersetzen → `1 failed, 1 passed`: `test_the_module_is_handed_the_windows_day_and_the_forecasts_first_day` (`AssertionError: assert datetime.date(2026, 5, 22) == datetime.date(2026, 5, 21)`).
3. Das Argument `forecast_first_day=now.date() + timedelta(days=1)` samt Kommentar entfernen → `1 failed, 1 passed`: `test_the_module_is_handed_the_windows_day_and_the_forecasts_first_day` (`AssertionError: assert None == datetime.date(2026, 5, 23)`).

Schätzungs-Seite, jeweils geprüft mit dem Befehl aus Step 9:

4. In `live_estimate.py` `day = weather_day(anchor, now)` durch `day = weather_day(now, now)` ersetzen → mindestens rot: `TestTheEstimatePricesTheDayOfItsWindow::test_the_hargreaves_stand_in_prices_the_windows_day`, `TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one`, `TestTheGapNarrowsAsTheWindowCloses::test_it_is_exact_once_the_window_has_closed`, `TestEstimatedRadiationZonesRunTheirOwnCommitsEquation::test_its_evapotranspiration_is_the_one_the_commit_books`.
5. In `live_estimate.py` `forecast_data=None, day=day, warn_on_clamp=False` durch `forecast_data=None, warn_on_clamp=False` ersetzen → mindestens rot: `TestTheEstimatePricesTheDayOfItsWindow::test_the_same_window_gives_the_same_figure_in_any_season`, `TestEstimatedRadiationZonesRunTheirOwnCommitsEquation::test_the_live_bucket_lands_on_the_committed_bucket`, `TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one`, `test_live_estimate_without_hourly_calculation.py::TestTheMirrorAppliesWithTheSwitchOff::test_the_live_bucket_lands_on_the_committed_bucket`.
6. In `live_estimate.py` `low, high, geometry.latitude, day.timetuple().tm_yday` durch `low, high, geometry.latitude, now.timetuple().tm_yday` ersetzen → `1 failed`: `TestTheEstimatePricesTheDayOfItsWindow::test_the_hargreaves_stand_in_prices_the_windows_day`.
7. Im Test-Helfer `delta = instance.calculate(weather_data=weatherdata, forecast_data=None, day=day)` durch `delta = instance.calculate(weather_data=weatherdata, forecast_data=None)` ersetzen → auf der echten Uhr mindestens rot: `TestTheGapNarrowsAsTheWindowCloses::test_it_is_exact_once_the_window_has_closed` und `TestEstimatedRadiationZonesRunTheirOwnCommitsEquation::test_its_evapotranspiration_is_the_one_the_commit_books`. Diese Probe greift nur, wenn der Ausführungstag einen anderen Tag des Jahres hat als der 22.05.

Zum Schluss alle drei `sha256sum -c` → `OK`, dann Step 9 erneut → keine `FAILED`-Zeile.

- [ ] **Step 12: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_live_estimate_replayed_balance.py
uvx ruff check custom_components/irrigation_plus/
git status
git diff
git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/live_estimate.py tests/test_live_estimate_replayed_balance.py
git commit -F - <<'EOF'
fix(calculation,live-estimate): price the day a weather window covers

calculate_module let PyETO take the day of year from the wall clock, so the
same window booked a different evapotranspiration depending on when the
commit ran, and an early-morning commit priced yesterday's weather with
today's sun. The live estimate did the same for the zone's own daily equation
and for the Hargreaves stand-in, so its figure moved with the season of the
refresh time.

Both now take the day from weather_day: the commit from its consume watermark
and now, the estimate from its anchor and now. The commit also hands PyETO the
first forecast day, the day after the commit. The two sides change together
because the estimate tests compare them for equality; the test helper that
books the commit's daily ET passes the same day.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Expected: black `... files left unchanged.`, ruff `All checks passed!`.

---

### Task 4: Der Bewässerungskalender rechnet jeden Monat mit seinem 15.

Setzt die Signatur `PyETO.calculate_et_for_day(self, weather_data, *, day=None, warn_on_clamp=True)` aus Task 2 voraus.

**Files:**
- Modify: `custom_components/irrigation_plus/watering_calendar.py` (Import + Aufruf in `_calculate_monthly_et_pyeto`)
- Test: `tests/test_watering_calendar.py` (zwei neue Tests am Ende von `TestWateringCalendar`)

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_watering_calendar.py` den Import ergänzen. Ersetze:

```python
"""Tests for the Irrigation Plus 12-month watering calendar feature."""

from unittest.mock import AsyncMock, Mock, patch
```

durch:

```python
"""Tests for the Irrigation Plus 12-month watering calendar feature."""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch
```

Dann am Dateiende, direkt nach dem Schluss von `test_calculate_monthly_et_pyeto`, anfügen. Ersetze:

```python
        # Verify the module was called with weather data
        mock_pyeto_module.calculate_et_for_day.assert_called_once()
        # Check that function was called (argument structure may have changed)
        assert mock_pyeto_module.calculate_et_for_day.call_count == 1
```

durch:

```python
        # Verify the module was called with weather data
        mock_pyeto_module.calculate_et_for_day.assert_called_once()
        # Check that function was called (argument structure may have changed)
        assert mock_pyeto_module.calculate_et_for_day.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_watering_calendar_prices_each_month_at_its_15th(
        self, coordinator, mock_pyeto_module
    ):
        """Each month's equation runs for the 15th of that month, in order."""
        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=mock_pyeto_module),
        ):
            await coordinator.async_generate_watering_calendar(zone_id=1)

        priced_days = [
            call.kwargs.get("day")
            for call in mock_pyeto_module.calculate_et_for_day.call_args_list
        ]
        assert priced_days == [date(2024, month, 15) for month in range(1, 13)]

    @pytest.mark.asyncio
    async def test_identical_weather_prices_july_above_january(self, hass, coordinator):
        """With the same weather, July's longer days give more ET than January's.

        Both months have 31 days, so any difference comes from the day of year
        the equation is priced at. The hass fixture is in the northern hemisphere.
        """
        from custom_components.irrigation_plus.calcmodules.pyeto import PyETO

        modinst = PyETO(hass, description="", config={})
        month_data = {
            "avg_temp": 20.0,
            "min_temp": 15.0,
            "max_temp": 25.0,
            "precipitation": 50.0,
            "humidity": 65.0,
            "wind_speed": 3.0,
            "pressure": 1013.25,
            "dewpoint": 12.0,
        }

        january = coordinator._calculate_monthly_et_pyeto(month_data, modinst, 1)
        july = coordinator._calculate_monthly_et_pyeto(month_data, modinst, 7)

        assert july > january
```

Der erste Test nutzt die vorhandene Fixture `mock_pyeto_module` (`calculate_et_for_day = Mock(return_value=-2.5)`); `call_args_list` hält die kwargs jedes der zwölf Aufrufe fest. Der zweite rechnet mit einem echten `PyETO` (leere Konfiguration, keine Sensorwerte nötig) auf der Breite der hass-Fixture (32,87 N).

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest "tests/test_watering_calendar.py::TestWateringCalendar::test_generate_watering_calendar_prices_each_month_at_its_15th" "tests/test_watering_calendar.py::TestWateringCalendar::test_identical_weather_prices_july_above_january" -p _local_socket_unblock -q`
Expected: FAIL, `2 failed`:
- `test_generate_watering_calendar_prices_each_month_at_its_15th`: `assert [None, None, ...ne, None, ...] == [datetime.dat..., 6, 15), ...]` mit `At index 0 diff: None != datetime.date(2024, 1, 15)` (kein `day` übergeben).
- `test_identical_weather_prices_july_above_january`: `assert X > X` mit zwei identischen Werten (die Zahl hängt vom Ausführungsdatum ab) (beide Monate mit dem heutigen Tag gerechnet, also identisch).

(Lokal zusätzlich je ein Teardown-ERROR `Lingering timer ... _reset_event_fired_today`, vorbestehend, ignorieren.)

- [ ] **Step 3: Kalender übergibt den 15. des Monats**

In `custom_components/irrigation_plus/watering_calendar.py` den Import ersetzen:

```python
import logging
import math
from datetime import datetime
```

durch:

```python
import logging
import math
from datetime import date, datetime
```

In `_calculate_monthly_et_pyeto` ersetzen:

```python
        # Calculate daily ET and scale to monthly
        daily_et_delta = modinst.calculate_et_for_day(weather_data)
```

durch:

```python
        # Calculate daily ET and scale to monthly. The equation is priced at the
        # month's 15th, so its solar geometry (daylight, extraterrestrial
        # radiation) belongs to the month being estimated.
        daily_et_delta = modinst.calculate_et_for_day(
            weather_data, day=date(2024, month, 15)
        )
```

2024 ist dasselbe Referenzjahr, das die Funktion schon für `calendar.monthrange(2024, month)` und `datetime(2024, month, 1)` nutzt. Der Tag wird nur als Argument durchgereicht, nichts landet auf der geteilten Modul-Instanz.

- [ ] **Step 4: Tests laufen grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py -p _local_socket_unblock -q`
Expected: `11 passed` (lokal zusätzlich `11 errors`, alle `Lingering timer ... _reset_event_fired_today` im Teardown, vorbestehend; keine FAILED-Zeile).

- [ ] **Step 5: Schwester-Pfad-Check**

Run: `grep -n "calculate_et_for_day\|\.calculate(\|now()\|tm_yday" custom_components/irrigation_plus/watering_calendar.py`
Expected: genau vier Treffer: zweimal `"generated_at": datetime.now().isoformat(),` (Zeitstempel der Erzeugung, keine Rechnung), `et_estimate = modinst.calculate()` (Static-Modul, kein Tagesbezug) und `daily_et_delta = modinst.calculate_et_for_day(`. Kein weiterer Pfad rechnet mit dem heutigen Tag.

- [ ] **Step 6: Mutationsproben**

Jede Mutation einzeln einbauen, `./.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py -p _local_socket_unblock -q` laufen lassen, danach byte-genau zurücknehmen (vorher `cp` + `sha256sum` nach `/d/Entwicklung/HASI/mutation-backup/`, danach `cp` zurück + `sha256sum -c` muss `OK` melden).

1. `day=date(2024, month, 15)` entfernen (Aufruf wieder `modinst.calculate_et_for_day(weather_data)`) -> `2 failed, 9 passed`: `test_generate_watering_calendar_prices_each_month_at_its_15th` FAIL (`None != datetime.date(2024, 1, 15)`) und `test_identical_weather_prices_july_above_january` FAIL (`assert X > X` mit zwei identischen Werten (die Zahl hängt vom Ausführungsdatum ab)).
2. `day=date(2024, month, 15)` -> `day=date(2024, month, 1)` -> `1 failed, 10 passed`: `test_generate_watering_calendar_prices_each_month_at_its_15th` FAIL (`At index 0 diff: datetime.date(2024, 1, 1) != datetime.date(2024, 1, 15)`). Der Juli-über-Januar-Test bleibt hier erwartungsgemäß grün, denn auch der 1. Januar und der 1. Juli unterscheiden sich.

- [ ] **Step 7: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
```
Expected: `2 files left unchanged.` bzw. `All checks passed!`

```bash
git status
git diff custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix: price each watering-calendar month at its own 15th

The 12-month calendar ran the PyETO equation for every month with the
day of year of the moment the calendar was generated, so daylight hours
and extraterrestrial radiation were the same for January and July and
the seasonal shape came only from the synthetic temperatures. Each month
is now priced at the 15th of that month.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Determinismus, volle Suite, Lint, Prüfungen

- [ ] **Step 1: Uhr-Plugin für die Datumsprobe anlegen (außerhalb des Repos)**

```bash
mkdir -p /d/Entwicklung/HASI/freezeplug
cat > /d/Entwicklung/HASI/freezeplug/_freeze_at.py <<'EOF'
import os

import pytest
from freezegun import freeze_time


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    with freeze_time(os.environ["FREEZE_AT"], tick=True):
        yield
EOF
```

- [ ] **Step 2: Die drei datumsabhängigen Tests an vier Tagen**

```bash
T1="tests/test_live_estimate_replayed_balance.py::TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one"
T2="tests/test_live_estimate_replayed_balance.py::TestTheForecastTierIsPublished::test_the_self_contained_tier_beats_reading_the_extremes_off_the_morning"
T3="tests/test_solrad_clamp_warning.py::TestTheCalculationPath::test_a_plausible_reading_warns_about_nothing"
for at in 2026-03-01T12:00:00Z 2026-05-22T12:00:00Z 2026-09-14T12:00:00Z 2026-12-21T12:00:00Z; do
  echo "== $at"
  FREEZE_AT=$at PYTHONPATH=/d/Entwicklung/HASI/freezeplug ./.venv/Scripts/python.exe -m pytest "$T1" "$T2" "$T3" -p _local_socket_unblock -p _freeze_at -q 2>&1 | grep -E "^FAILED|passed|failed"
done
```
Expected: an allen vier Tagen `3 passed`, keine `FAILED`-Zeile.

- [ ] **Step 3: Lint**

```bash
uvx black --check custom_components/irrigation_plus/ tests/
uvx ruff check custom_components/irrigation_plus/
```
Expected: `would be left unchanged`, `All checks passed!`

- [ ] **Step 4: Volle Suite gegen die Basis vom selben Tag**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/after-pyeto.txt
grep "^FAILED" /d/Entwicklung/HASI/baseline-pyeto.txt | sort > /d/Entwicklung/HASI/bp.txt
grep "^FAILED" /d/Entwicklung/HASI/after-pyeto.txt | sort > /d/Entwicklung/HASI/ap.txt
diff /d/Entwicklung/HASI/bp.txt /d/Entwicklung/HASI/ap.txt
tail -1 /d/Entwicklung/HASI/baseline-pyeto.txt; tail -1 /d/Entwicklung/HASI/after-pyeto.txt
```
Expected: `diff` zeigt genau eine entfernte Zeile, den Konvergenztest, und keine hinzugefügte; `failed` um 1 niedriger; `passed` um 15 höher (14 neue Tests plus der Konvergenztest). Die lokalen Teardown-`errors` steigen um 6, je einer pro neuem asynchronen Coordinator-Test; das ist kein Rückschritt.

- [ ] **Step 5: Kein Produktionsaufrufer verlässt sich auf die Uhr**

```bash
grep -rn -A6 "calculate_et_for_day(\|modinst.calculate(\s*$\|modinst.calculate(weather_data" custom_components/irrigation_plus --include=*.py
grep -n "datetime.datetime.now()" custom_components/irrigation_plus/calcmodules/pyeto/__init__.py
```
Expected: jeder PyETO-Aufruf in `calculation.py` (`delta = modinst.calculate(`, `day=weather_day(` sechs Zeilen darunter), `live_estimate.py` und `watering_calendar.py` trägt `day=`. Der zweite Treffer in `calculation.py`, `delta = 0 - modinst.calculate(` mit `et_data=`, gehört zu Passthrough und ist nicht betroffen (Static `modinst.calculate()` trifft das Muster nicht). `datetime.datetime.now()` steht in der PyETO-Datei genau zweimal, beide Male nur als Rückfall ohne `day`: `base_day = day if day is not None else datetime.datetime.now().date()` in `calculate` und `(day if day is not None else datetime.datetime.now())` in `calculate_et_for_day`.

- [ ] **Step 6: Keine Branch-SHAs in hinzugefügten Zeilen**

```bash
git diff upstream/master --unified=0 -- custom_components/ tests/ | grep -E "^\+.*\b[0-9a-f]{8}\b" || echo "keine SHAs"
```
Expected: `keine SHAs`.

---

### Task 6: PR (Freigabe nötig)

- [ ] **Step 1: PR-Text entwerfen** (englisch): Befund aus der CI von #140, Wurzel mit Zeile, Belegtabelle (eingefrorene Uhr, nur PyETOs Uhr), die Aufrufer-Tabelle, die Regel für den Wettertag und warum Beginn statt Ende, Wirkung (keine Änderung bei Abendrechnung; Frührechnung und Mitternachts-Absicherung einen Tag zurück; Vorhersagetage; Kalender sichtbar), die zwei weiteren Tests, die im Herbst gekippt wären, Tests mit Mutationstabelle, Datumsprobe an vier Tagen, Suite-Zahlen gegen die Basis vom selben Tag, „Noticed, not in this PR“ aus dem Spec-Abschnitt „Außerhalb“. Ende mit `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2: Text im Chat zeigen und Freigabe abwarten.**
- [ ] **Step 3: Nach Freigabe:**

```bash
git push -u origin fix/pyeto-day-of-year
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/pyeto-day-of-year --title "PyETO: price the day the weather belongs to, not the day the clock shows" --body-file <datei>
```

- [ ] **Step 4: Nach dem Merge upstream** (eigene Freigabe): `master` in `fix/bound-wall-clock-hardware-window` mergen (kein Rebase, der Branch ist gepusht), damit die CI von #140 neu läuft und grün wird.
