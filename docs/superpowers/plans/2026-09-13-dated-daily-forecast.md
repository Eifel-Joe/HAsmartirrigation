# Datierte Tageseinträge — Implementation Plan (PR 1 von 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jeder Eintrag aus `get_forecast_data()` trägt Beginn und Ende des Tages, den er beschreibt; Open-Meteo beginnt wieder morgen; das Panel beschriftet Tage mit dem mitgelieferten Datum.

**Architecture:** Zwei neue Konstanten (`FORECAST_DAY_START`, `FORECAST_DAY_END`) als zeitzonenbehaftete UTC-Zeitpunkte, gesetzt in allen vier Wetter-Clients nach deren eigener Tagesgrenze. Open-Meteo filtert nach Datum statt nach Index 0. `websocket_get_weather_forecast` liest das Datum aus dem Eintrag. Kein Konsument, der positionale Indizes nutzt, wird angefasst — das macht PR 2.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component, pytest + freezegun.

**Spec:** `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md` (Branch `archive/design-history`).

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`.
- Test-Kommando (lokale Env, Windows):
  `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint (nur diese zählen in CI):
  `uvx black custom_components/irrigation_plus/` und `uvx ruff check custom_components/irrigation_plus/`
- Die lokale Suite hat Vorbestands-Fehler (7 failed, ~300 Teardown-Errors „Lingering timer"). **Immer gegen die Basis vergleichen, nie gegen null.**
- **Mutationsprobe ist Pflicht:** nach grünem Test den Produktionscode gezielt zurückdrehen, Test muss rot werden, dann wiederherstellen. Wiederherstellen per Byte-Backup + `sha256sum -c`, **nicht** per `git checkout --` (`core.autocrlf=true` schreibt LF→CRLF um).
- Commit-Messages englisch, am Ende:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- Kommentare/Docstrings beschreiben, was der Code JETZT tut. **Keine SHAs des eigenen Arbeitsbranches** in Kommentaren.
- `push` und PR nur nach Freigabe im Chat.

## Dateien

| Datei | Änderung |
|---|---|
| `custom_components/irrigation_plus/const.py` | zwei Konstanten nach `OBSERVATION_TIME` |
| `custom_components/irrigation_plus/weathermodules/OWMClient.py` | Tages-Spanne je Eintrag (UTC-Tag) |
| `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py` | Tages-Spanne je Eintrag (UTC-Tag) |
| `custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py` | Datumsfilter statt Index 0; Tages-Spanne (Ortstag) |
| `custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py` | Tages-Spanne aus `time` |
| `custom_components/irrigation_plus/websockets.py` | Panel-Datum aus Eintrag |
| `tests/test_weather_modules.py` | Tests OWM, Met Office, Open-Meteo |
| `tests/test_pirateweather_daily.py` | neu |
| `tests/test_websocket_get_weather_forecast.py` | neu |

---

### Task 0: Branch und Basis messen

- [ ] **Step 1: Branch von upstream anlegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --branch
git fetch upstream
git checkout -b fix/dated-daily-forecast upstream/master
git log --oneline -1
```
Expected: Arbeitsbaum sauber (untracked `docs/SESSION-STAND.md` ist ok), HEAD = aktuelles `upstream/master`.

- [ ] **Step 2: Basis der vollen Suite messen und namentlich sichern**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/baseline-pr1.txt
tail -1 /d/Entwicklung/HASI/baseline-pr1.txt
```
Expected: eine Zeile `N failed, M passed, …`. Datei bleibt bis Task 7 liegen.

---

### Task 1: Konstanten + OWM trägt den UTC-Tag

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (nach Zeile `OBSERVATION_TIME = "observed"`)
- Modify: `custom_components/irrigation_plus/weathermodules/OWMClient.py` (`get_forecast_data`)
- Test: `tests/test_weather_modules.py` (Klasse `TestOWMClientGetForecastData`)

- [ ] **Step 1: Import im Test ergänzen**

In `tests/test_weather_modules.py` den Block `from custom_components.irrigation_plus.const import (` um zwei Namen erweitern (alphabetisch vor `MAPPING_CURRENT_PRECIPITATION`):

```python
from custom_components.irrigation_plus.const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_CURRENT_PRECIPITATION,
```

- [ ] **Step 2: Fehlschlagenden Test schreiben**

In `class TestOWMClientGetForecastData` nach `test_today_excluded` einfügen:

```python
    @freeze_time("2024-06-01 06:00:00")
    def test_entries_carry_their_utc_day(self):
        # OWM buckets its three-hourly slots by UTC calendar date, so each entry
        # covers UTC midnight to the next UTC midnight. A bare date would not say
        # that; the span does.
        client = OWMClient(api_key="k", latitude=52.0, longitude=5.0, elevation=0)
        with patch(_OWM_PATCH, return_value=_make_response(200, self._forecast_body())):
            data = client.get_forecast_data()

        utc = datetime.timezone.utc
        assert data[0][FORECAST_DAY_START] == datetime.datetime(2024, 6, 2, tzinfo=utc)
        assert data[0][FORECAST_DAY_END] == datetime.datetime(2024, 6, 3, tzinfo=utc)
        assert data[1][FORECAST_DAY_START] == datetime.datetime(2024, 6, 3, tzinfo=utc)
        assert data[1][FORECAST_DAY_END] == datetime.datetime(2024, 6, 4, tzinfo=utc)
```

- [ ] **Step 3: Test läuft rot**

Run: `./.venv/Scripts/python.exe -m pytest "tests/test_weather_modules.py::TestOWMClientGetForecastData::test_entries_carry_their_utc_day" -p _local_socket_unblock -q`
Expected: FAIL, `ImportError: cannot import name 'FORECAST_DAY_END'`.

- [ ] **Step 4: Konstanten anlegen**

In `const.py` direkt nach `OBSERVATION_TIME = "observed"  # when the weather station measured it (API dt)`:

```python
# The span a daily forecast entry covers, as aware UTC datetimes. The clients
# bucket days differently -- OWM and Met Office by UTC date, Open-Meteo and
# Pirate Weather by the site's local date -- so a bare date would not say which
# day an entry means. Not a sensor mapping: never offered as a mappable field.
FORECAST_DAY_START = "day_start"
FORECAST_DAY_END = "day_end"
```

- [ ] **Step 5: OWM setzt die Spanne**

In `OWMClient.py` den Import erweitern:

```python
from ..const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_CURRENT_PRECIPITATION,
```

In `get_forecast_data` in der Schleife `for day in sorted(daily_buckets.keys()):` vor `parsed_data_total.append(` einfügen:

```python
                    # The bucket IS a UTC calendar day (see the grouping above).
                    day_start = datetime.datetime(
                        day.year, day.month, day.day, tzinfo=datetime.timezone.utc
                    )
```

und im angehängten Dict nach `MAPPING_PRECIPITATION: rain + snow_mm,` ergänzen:

```python
                            FORECAST_DAY_START: day_start,
                            FORECAST_DAY_END: day_start
                            + datetime.timedelta(days=1),
```

- [ ] **Step 6: Test läuft grün, OWM-Klasse komplett**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_modules.py::TestOWMClientGetForecastData -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 7: Mutationsprobe**

`day_start + datetime.timedelta(days=1)` in `OWMClient.py` testweise auf `day_start` ändern → Test muss FAIL. Datei per Backup wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 8: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_weather_modules.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/weathermodules/OWMClient.py tests/test_weather_modules.py
git commit -F - <<'EOF'
feat(forecast): OWM daily entries carry the UTC day they cover

Daily forecast entries were positional: index 0 meant tomorrow by convention
and nothing in the entry said so. The clients do not even agree on what a day
is -- OWM buckets by UTC date -- so every consumer had to trust a position.

Each entry now carries FORECAST_DAY_START and FORECAST_DAY_END as aware UTC
datetimes. Nothing reads them yet; the other clients follow.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Met Office trägt den UTC-Tag

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py` (`get_forecast_data`)
- Test: `tests/test_weather_modules.py` (Klasse `TestMetOfficeClientGetForecastData`)

- [ ] **Step 1: Fehlschlagenden Test schreiben**

In `class TestMetOfficeClientGetForecastData` nach `test_aggregates_to_daily_and_skips_today`:

```python
    @freeze_time("2024-06-01 12:30:00")
    def test_entries_carry_their_utc_day(self):
        # Met Office groups its three-hourly steps by UTC date, like OWM.
        client = MetOfficeClient(api_key="k", latitude=52.0, longitude=5.0, elevation=0)
        with patch(_MET_PATCH, return_value=_make_response(200, self._THREE_HOURLY)):
            fc = client.get_forecast_data()

        utc = datetime.timezone.utc
        assert fc[0][FORECAST_DAY_START] == datetime.datetime(2024, 6, 2, tzinfo=utc)
        assert fc[0][FORECAST_DAY_END] == datetime.datetime(2024, 6, 3, tzinfo=utc)
```

- [ ] **Step 2: Test läuft rot**

Run: `./.venv/Scripts/python.exe -m pytest "tests/test_weather_modules.py::TestMetOfficeClientGetForecastData::test_entries_carry_their_utc_day" -p _local_socket_unblock -q`
Expected: FAIL, `KeyError: 'day_start'`.

- [ ] **Step 3: Implementieren**

Import in `MetOfficeClient.py` erweitern:

```python
from ..const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_CURRENT_PRECIPITATION,
```

Im Dict `day_data = {` nach `MAPPING_PRECIPITATION: precip,` ergänzen:

```python
                    # ``day`` is the UTC calendar date the steps were grouped by.
                    # When the product ends mid-day the last entry still spans the
                    # whole date, but its precipitation holds only the steps that
                    # exist, so that day's total is short.
                    FORECAST_DAY_START: datetime.datetime(
                        day.year, day.month, day.day, tzinfo=datetime.timezone.utc
                    ),
                    FORECAST_DAY_END: datetime.datetime(
                        day.year, day.month, day.day, tzinfo=datetime.timezone.utc
                    )
                    + datetime.timedelta(days=1),
```

- [ ] **Step 4: Test grün, Klasse komplett**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_modules.py::TestMetOfficeClientGetForecastData -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 5: Mutationsprobe**

`+ datetime.timedelta(days=1)` bei `FORECAST_DAY_END` entfernen → FAIL. Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_weather_modules.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weathermodules/MetOfficeClient.py tests/test_weather_modules.py
git commit -F - <<'EOF'
feat(forecast): Met Office daily entries carry the UTC day they cover

Met Office groups its three-hourly steps by UTC calendar date, so each entry
spans UTC midnight to the next.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Open-Meteo beginnt wieder morgen und trägt den Ortstag

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py` (`get_forecast_data`)
- Test: `tests/test_weather_modules.py` (neue Klasse `TestOpenMeteoClientGetForecastData`)

**Hintergrund:** Die URL enthält `&past_days=1`. Damit steht in `daily.time` an Index 0 **gestern**, an Index 1 heute. Der Code überspringt nur Index 0 und liefert deshalb heute als ersten Tag. Kein Test deckt das ab.

- [ ] **Step 1: Fehlschlagenden Test schreiben**

Neue Klasse direkt vor `class TestOpenMeteoClientCaching:` einfügen:

```python
class TestOpenMeteoClientGetForecastData:
    """The daily forecast starts tomorrow, as every consumer assumes.

    The request carries ``past_days=1`` for the intra-day estimate, so the daily
    arrays begin YESTERDAY. Skipping index 0 therefore dropped yesterday and
    served today as the first forecast day. Filtering on the date itself is what
    makes the result independent of how many past days are requested.
    """

    @freeze_time("2024-06-01 10:00:00")
    def test_starts_tomorrow_despite_past_days(self):
        doc = {
            "utc_offset_seconds": 7200,
            "hourly": {"time": []},
            "daily": {
                "time": ["2024-05-31", "2024-06-01", "2024-06-02", "2024-06-03"],
                "temperature_2m_max": [20.0, 21.0, 22.0, 23.0],
                "temperature_2m_min": [10.0, 11.0, 12.0, 13.0],
                "precipitation_sum": [0.0, 1.0, 2.0, 3.0],
                "wind_speed_10m_max": [3.0, 3.0, 3.0, 3.0],
            },
        }
        client = OpenMeteoClient(latitude=52.0, longitude=5.0)
        with patch(_OPENMETEO_PATCH, return_value=_make_response(200, doc)):
            data = client.get_forecast_data()

        # yesterday (05-31) and today (06-01) are both excluded
        assert [d[MAPPING_PRECIPITATION] for d in data] == [2.0, 3.0]

    @freeze_time("2024-06-01 10:00:00")
    def test_entries_carry_their_local_day(self):
        # Open-Meteo reports daily values per LOCAL date (timezone=auto). At UTC+2
        # local midnight of 06-02 is 22:00 UTC on 06-01.
        doc = {
            "utc_offset_seconds": 7200,
            "hourly": {"time": []},
            "daily": {
                "time": ["2024-06-01", "2024-06-02"],
                "temperature_2m_max": [21.0, 22.0],
                "temperature_2m_min": [11.0, 12.0],
                "precipitation_sum": [1.0, 2.0],
                "wind_speed_10m_max": [3.0, 3.0],
            },
        }
        client = OpenMeteoClient(latitude=52.0, longitude=5.0)
        with patch(_OPENMETEO_PATCH, return_value=_make_response(200, doc)):
            data = client.get_forecast_data()

        utc = datetime.timezone.utc
        assert data[0][FORECAST_DAY_START] == datetime.datetime(
            2024, 6, 1, 22, 0, tzinfo=utc
        )
        assert data[0][FORECAST_DAY_END] == datetime.datetime(
            2024, 6, 2, 22, 0, tzinfo=utc
        )
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_modules.py::TestOpenMeteoClientGetForecastData -p _local_socket_unblock -q`
Expected: beide FAIL — der erste mit `[1.0, 2.0, 3.0] != [2.0, 3.0]`, der zweite mit `KeyError: 'day_start'`.

- [ ] **Step 3: Implementieren**

Import in `OpenMeteoClient.py` erweitern:

```python
from ..const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_CURRENT_PRECIPITATION,
```

In `get_forecast_data` ersetzen:

```python
            doc = self._fetch()
            daily = doc.get("daily", {})
            n_days = len(daily.get("time", []))

            result = []
            # Skip index 0 (today); iterate the remaining forecast days
            for i in range(1, n_days):
```

durch:

```python
            doc = self._fetch()
            daily = doc.get("daily", {})
            times = daily.get("time", [])
            n_days = len(times)
            # Daily values are per LOCAL date (timezone=auto). Filter on the date
            # rather than on a position: the request also asks for past_days, so
            # index 0 is yesterday and index 1 is today, and a positional skip
            # served today as the first forecast day.
            offset = datetime.timedelta(seconds=doc.get("utc_offset_seconds", 0))
            local_today = (datetime.datetime.now(datetime.timezone.utc) + offset).date()

            result = []
            for i in range(n_days):
                try:
                    day_date = datetime.date.fromisoformat(times[i])
                except (TypeError, ValueError):
                    continue
                if day_date <= local_today:
                    continue
```

Im Dict `day = {` nach `MAPPING_WINDSPEED: self._wind_2m(wind),` ergänzen:

```python
                    # Local midnight of this date, expressed in UTC. One offset
                    # for the whole document, so a DST change inside the forecast
                    # puts that day's boundary an hour off.
                    FORECAST_DAY_START: datetime.datetime(
                        day_date.year,
                        day_date.month,
                        day_date.day,
                        tzinfo=datetime.timezone.utc,
                    )
                    - offset,
                    FORECAST_DAY_END: datetime.datetime(
                        day_date.year,
                        day_date.month,
                        day_date.day,
                        tzinfo=datetime.timezone.utc,
                    )
                    - offset
                    + datetime.timedelta(days=1),
```

- [ ] **Step 4: Tests grün, Open-Meteo-Tests komplett**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_weather_modules.py tests/test_openmeteo_hourly.py -p _local_socket_unblock -q`
Expected: alle PASS (inkl. `TestOpenMeteoClientCaching`).

- [ ] **Step 5: Mutationsproben**

1. `if day_date <= local_today:` → `if day_date < local_today:` → `test_starts_tomorrow_despite_past_days` FAIL.
2. `- offset` im `FORECAST_DAY_START` entfernen → `test_entries_carry_their_local_day` FAIL.
Jeweils wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_weather_modules.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py tests/test_weather_modules.py
git commit -F - <<'EOF'
fix(open-meteo): start the daily forecast tomorrow again

The request asks for past_days=1 so the intra-day estimate can reach back to
the previous evening's calculation. That prepends yesterday to every daily
array, and get_forecast_data still skipped only index 0 -- so it dropped
yesterday and served TODAY as the first forecast day.

Every consumer reads that list as starting tomorrow: the freeze guard's
"coming night", forecast weighting, PyETO's forecast days, the precipitation
guard and the panel's date labels. For Open-Meteo installs all of them have
been one day early. No test covered it; the only get_forecast_data test for
this client checks caching against an empty document.

The loop now filters on the date itself, so the result no longer depends on how
many past days are requested, and each entry carries the local day it covers.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Pirate Weather trägt die Spanne seines Tages

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py` (`get_forecast_data`)
- Test: `tests/test_pirateweather_daily.py` (neu)

**Hintergrund:** `daily.data[x].time` ist ein UNIX-Zeitstempel (Beginn des Ortstags der Station). Die Schleife läuft `range(1, len - 1)`; das Weglassen des letzten Tages bleibt unverändert (außerhalb des Umfangs), sichert aber, dass `data[x + 1]` immer existiert. **Annahme, ungemessen:** kein API-Schlüssel, keine echten Testdaten.

- [ ] **Step 1: Fehlschlagenden Test schreiben**

Datei `tests/test_pirateweather_daily.py`:

```python
"""PirateWeatherClient.get_forecast_data: each day carries the span it covers.

Pirate Weather stamps each daily block with the UNIX time its local day begins,
so the span is that instant up to the next block's. The loop drops the first
(today) and the last block, which guarantees a next block exists for every day
it returns. That convention is taken from the API and has not been measured
against a live response.
"""

import datetime
import json
from unittest.mock import MagicMock, patch

from custom_components.irrigation_plus.const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_PRECIPITATION,
)
from custom_components.irrigation_plus.weathermodules.PirateWeatherClient import (
    PirateWeatherClient,
)

_PATCH = (
    "custom_components.irrigation_plus.weathermodules.PirateWeatherClient._SESSION.get"
)


def _block(start, precip_cm):
    return {
        "time": int(start.timestamp()),
        "windSpeed": 3.0,
        "pressure": 1013.0,
        "humidity": 0.6,
        "temperatureMax": 22.0,
        "temperatureMin": 12.0,
        "dewPoint": 9.0,
        "precipAccumulation": precip_cm,
    }


def test_entries_carry_the_span_of_their_day():
    utc = datetime.timezone.utc
    # Local midnights of a UTC+2 site are 22:00 UTC the evening before.
    starts = [
        datetime.datetime(2024, 5, 31, 22, 0, tzinfo=utc) + datetime.timedelta(days=i)
        for i in range(4)
    ]
    doc = {"daily": {"data": [_block(s, 0.1 * (i + 1)) for i, s in enumerate(starts)]}}
    response = MagicMock(status_code=200, text=json.dumps(doc))
    client = PirateWeatherClient("key", "1", 52.0, 5.0, 0)

    with patch(_PATCH, return_value=response):
        data = client.get_forecast_data()

    # blocks 1 and 2 are returned (today and the last block are dropped)
    assert [round(d[MAPPING_PRECIPITATION], 6) for d in data] == [2.0, 3.0]
    assert data[0][FORECAST_DAY_START] == starts[1]
    assert data[0][FORECAST_DAY_END] == starts[2]
    assert data[1][FORECAST_DAY_START] == starts[2]
    assert data[1][FORECAST_DAY_END] == starts[3]
```

- [ ] **Step 2: Test läuft rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pirateweather_daily.py -p _local_socket_unblock -q`
Expected: FAIL, `KeyError: 'day_start'`.

- [ ] **Step 3: Implementieren**

Import in `PirateWeatherClient.py` erweitern:

```python
from ..const import (
    FORECAST_DAY_END,
    FORECAST_DAY_START,
    MAPPING_CURRENT_PRECIPITATION,
```

In `get_forecast_data` in der Schleife nach `data = doc[PirateWeather_daily_weather_key_name]["data"][x]` einfügen:

```python
                        # Each block is stamped with the start of its local day;
                        # the next block's stamp ends it. The loop stops one short
                        # of the last block, so x + 1 always exists.
                        next_data = doc[PirateWeather_daily_weather_key_name]["data"][
                            x + 1
                        ]
```

Vor `parsed_data_total.append(parsed_data)` einfügen:

```python
                        parsed_data[FORECAST_DAY_START] = datetime.datetime.fromtimestamp(
                            data["time"], datetime.timezone.utc
                        )
                        parsed_data[FORECAST_DAY_END] = datetime.datetime.fromtimestamp(
                            next_data["time"], datetime.timezone.utc
                        )
```

- [ ] **Step 4: Test grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pirateweather_daily.py tests/test_weather_modules.py -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 5: Mutationsprobe**

`next_data["time"]` testweise auf `data["time"]` ändern → FAIL. Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_pirateweather_daily.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py tests/test_pirateweather_daily.py
git commit -F - <<'EOF'
feat(forecast): Pirate Weather daily entries carry the span of their day

Each daily block is stamped with the start of its local day, and the next
block's stamp ends it. First test of this client's daily forecast; the shape is
taken from the API and has not been measured against a live response.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Panel beschriftet Tage mit dem mitgelieferten Datum

**Files:**
- Modify: `custom_components/irrigation_plus/websockets.py` (`websocket_get_weather_forecast`)
- Test: `tests/test_websocket_get_weather_forecast.py` (neu)

- [ ] **Step 1: Fehlschlagenden Test schreiben**

Datei `tests/test_websocket_get_weather_forecast.py`:

```python
"""The panel labels each forecast day with the day the client says it covers.

It used to compute ``today + i + 1`` on the assumption that every client starts
at tomorrow and returns consecutive days. The entry now carries its own span, so
the label no longer depends on position.
"""

import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import homeassistant.util.dt as dt_util

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.websockets import (
    websocket_get_weather_forecast,
)


def _env(entries):
    client = SimpleNamespace(get_forecast_data=lambda: entries)

    async def run_executor(func, *args):
        return func(*args)

    hass = SimpleNamespace(
        data={
            const.DOMAIN: {
                const.CONF_USE_WEATHER_SERVICE: True,
                "coordinator": SimpleNamespace(_WeatherServiceClient=client),
            }
        },
        async_add_executor_job=run_executor,
    )
    connection = Mock()
    sent = {}
    connection.send_result = Mock(
        side_effect=lambda mid, payload: sent.update(result=payload)
    )
    return hass, connection, sent


def _entry(day):
    start = dt_util.start_of_local_day(day)
    return {
        const.FORECAST_DAY_START: dt_util.as_utc(start),
        const.FORECAST_DAY_END: dt_util.as_utc(start + datetime.timedelta(days=1)),
        const.MAPPING_MIN_TEMP: 10.0,
        const.MAPPING_MAX_TEMP: 20.0,
        const.MAPPING_PRECIPITATION: 1.0,
        const.MAPPING_WINDSPEED: 2.0,
    }


async def test_each_day_is_labelled_with_the_day_it_covers():
    today = dt_util.now().date()
    # Deliberately not "tomorrow, then the day after": a positional label would
    # say today+1 and today+2.
    days = [today + datetime.timedelta(days=2), today + datetime.timedelta(days=5)]
    hass, connection, sent = _env([_entry(d) for d in days])

    await websocket_get_weather_forecast.__wrapped__(hass, connection, {"id": 1})

    assert sent["result"]["available"] is True
    assert [d["date"] for d in sent["result"]["days"]] == [d.isoformat() for d in days]
```

- [ ] **Step 2: Test läuft rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_websocket_get_weather_forecast.py -p _local_socket_unblock -q`
Expected: FAIL, Liste mit `today+1`/`today+2` statt `today+2`/`today+5`.

- [ ] **Step 3: Implementieren**

In `websockets.py`, `websocket_get_weather_forecast`, ersetzen:

```python
    today = dt_util.now().date()
    days = []
    for i, day in enumerate(raw):
        days.append(
            {
                # All clients skip "today" and start at tomorrow.
                "date": (today + datetime.timedelta(days=i + 1)).isoformat(),
```

durch:

```python
    today = dt_util.now().date()
    days = []
    for i, day in enumerate(raw):
        start = day.get(const.FORECAST_DAY_START)
        if start is not None:
            # The day the client says this entry covers, in local time. Reading
            # it off the entry rather than off its position is what keeps a
            # client whose list does not start at tomorrow from being mislabelled.
            label = dt_util.as_local(start).date()
        else:
            label = today + datetime.timedelta(days=i + 1)
        days.append(
            {
                "date": label.isoformat(),
```

Außerdem im Docstring derselben Funktion ersetzen:

```python
    Reuses the coordinator's weather client (the same forecast already used for
    the precip look-ahead skip). The clients return a normalized list of per-day
    dicts starting tomorrow, with no date field, so we attach the date here.
```

durch:

```python
    Reuses the coordinator's weather client (the same forecast already used for
    the precip look-ahead skip). Each entry carries the span of the day it
    covers (``FORECAST_DAY_START``), and its local date is the label.
```

Die Docstring-Zeilen danach (`Values are metric …`) bleiben unverändert.

- [ ] **Step 4: Test grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_websocket_get_weather_forecast.py -p _local_socket_unblock -q`
Expected: PASS.

- [ ] **Step 5: Mutationsprobe**

`if start is not None:` testweise auf `if False:` → FAIL. Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 6: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_websocket_get_weather_forecast.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/websockets.py tests/test_websocket_get_weather_forecast.py
git commit -F - <<'EOF'
fix(panel): label forecast days with the day each entry covers

The panel computed each label as today + i + 1, assuming every client starts at
tomorrow and returns consecutive days. Open-Meteo did not, so its forecast was
shown a day late. The entry now says which day it covers, and that is the label.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Geschwister-Prüfung — liest noch jemand Tage positional?

Kein Code. Belegen, dass PR 1 nichts Positionales **verändert**, sondern nur Daten ergänzt.

- [ ] **Step 1: Konsumenten auflisten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
grep -rn "forecast_data\[\|fd\[\|forecast\[0\]" custom_components/irrigation_plus/*.py
```
Expected: genau `skip_conditions.py` (Regen, Frost), `calculation.py` (Gewichtung), `live_estimate.py` (Rückfallstufe) — unverändert. Sie bekommen für Open-Meteo jetzt den vorgesehenen Tag; PR 2 stellt den Regen-Wächter auf Daten um.

- [ ] **Step 2: Prüfen, dass kein Konsument alle Schlüssel durchläuft**

```bash
grep -rn "\.items()" custom_components/irrigation_plus/calcmodules/pyeto/__init__.py custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/calculation.py | grep -i "forecast\|day"
```
Expected: keine Treffer.

---

### Task 7: Volle Suite gegen die Basis, Lint

- [ ] **Step 1: Lint**

```bash
uvx black --check custom_components/irrigation_plus/ tests/
uvx ruff check custom_components/irrigation_plus/
```
Expected: `would be left unchanged`, `All checks passed!`.

- [ ] **Step 2: Volle Suite, namentlich vergleichen**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/after-pr1.txt
grep "^FAILED" /d/Entwicklung/HASI/baseline-pr1.txt | sort > /tmp/b.txt
grep "^FAILED" /d/Entwicklung/HASI/after-pr1.txt | sort > /tmp/a.txt
diff /tmp/b.txt /tmp/a.txt && echo "IDENTISCHE Vorbestands-Fehler"
tail -1 /d/Entwicklung/HASI/baseline-pr1.txt; tail -1 /d/Entwicklung/HASI/after-pr1.txt
```
Expected: `IDENTISCHE Vorbestands-Fehler`; `passed` um genau die neuen Tests höher (OWM 1, Met Office 1, Open-Meteo 2, Pirate Weather 1, Panel 1 = +6).

- [ ] **Step 3: Kein Commit-SHA des Arbeitsbranches in Kommentaren**

```bash
git diff upstream/master --unified=0 -- custom_components/ | grep -E "^\+.*\b[0-9a-f]{8}\b" || echo "keine SHAs"
```
Expected: `keine SHAs` (oder nur SHAs, die auf `upstream/master` existieren: `git merge-base --is-ancestor <sha> upstream/master`).

---

### Task 8: PR vorbereiten (Freigabe nötig)

- [ ] **Step 1: PR-Text entwerfen** (englisch, Datei im Scratchpad): was sich ändert, der Open-Meteo-Befund mit `past_days=1`, Tests und Mutationsproben als Tabelle, Suite-Zahlen gegen die Basis, Annahme zu Pirate Weather, Hinweis „PR 2 (#137) baut darauf auf". Ende mit `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2: Text im Chat zeigen und Freigabe abwarten.**
- [ ] **Step 3: Nach Freigabe:**

```bash
git push -u origin fix/dated-daily-forecast
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/dated-daily-forecast --title "Daily forecast entries carry the day they cover; Open-Meteo starts tomorrow again" --body-file <datei>
```
