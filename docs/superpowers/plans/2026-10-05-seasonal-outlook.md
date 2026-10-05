# Saisonaler Ausblick nach den Regeln der Rechnung — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Die 12-Monats-Prognose rechnet ET, Regen und Kc nach den Regeln der echten Rechnung, ihr Klimamodell tut, was
seine Kommentare sagen, und jede Stelle, die sie zeigt oder beschreibt, nennt sie eine Veranschaulichung aus dem
Breitengrad.

**Architektur:** Punktuell im Bestand (Spec-Entscheidung E2): die drei Modul-Zweige und die Mengenformel in
`watering_calendar.py`, die Phasen in `_generate_monthly_climate_data`, dazu Texte in Panel, Dienstbeschreibung und
Doku. Ob Regen zählt, fragt die Prognose `calculation.zone_module_models_weather`, dieselbe Regel wie die Rechnung.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über `pytest-homeassistant-custom-component`;
Frontend Lit/TypeScript, Build mit Node 24 (`npm ci && npm run build` = eslint + rollup).

**Spec:** `docs/superpowers/specs/2026-10-05-seasonal-outlook-design.md` (freigegeben 2026-10-05, archiviert
`archive/design-history` `1e262f66`; danach um „Präzisierungen aus der Planung“ ergänzt).

**Probelauf (2026-10-05, gegen `bbf2e151`):** `D:\Entwicklung\HASI\issue10-work\probe_plan.py` liest jeden „Ersetze“-
und „Hänge an“-Block dieses Plans wörtlich und wendet sie Task für Task in einem Wegwerf-Worktree an; jeder Anker passte
genau einmal (`probe-run-2.txt`).
- Jeder Task wurde mit genau den hier genannten Meldungen RED und danach GREEN; nach jedem Task liefen die Kalender-,
  API- und Katalog-Tests ohne „failed“, ihre ERRORs sind nur die teardown-ERRORs (siehe Arbeitsumgebung).
- black und ruff sauber auf `custom_components/irrigation_plus/`, die Testdatei black-sauber (eine Zeile in Task 6
  danach im Plan berichtigt); Frontend-Build (eslint + rollup) und `npx tsc --noEmit -p .` ohne Fehler; geändert genau
  zwei Bundles (Task 8).
- Volle Suite `7 failed, 3681 passed, 9 skipped, 427 errors` gegen die Baseline `7 / 3667 / 9 / 415`; neu sind genau die
  zwölf Fixture-Tests als teardown-ERROR (Task 10), nichts fiel weg.
- Mutationen: **24/24 KILLED** (`mutate-probe.txt`), jeder Lauf sammelte 25 Tests. Jede Rechen- und Klima-Mutation
  fällt durch einen Verhaltenstest; nur die drei Text-Mutationen (M22–M24) fallen durch die Text-Prüfungen, wie gemeint.
- Getesteter Stand: `D:\Entwicklung\HASI\issue10-work\probe-2026-10-05.patch` (gilt bei Abweichung vom Plan).

**Umsetzung (2026-10-05, subagent-driven):** Tasks 0–10 erledigt, Branch `fix/seasonal-outlook` = 9 Commits auf
`bbf2e151`, Kopf `ec70de5f` (nach den Fixups des Abschluss-Reviews). Jeder Task: Plan-Blöcke per
`issue10-work\apply_plan_task.py`, RED/GREEN wie gemessen, Spec-Check byte-genau (`spec_check.py`), volle Suite mit
Namensvergleich (`expect_names.py`), Quality-Review + Nachprüfung; danach Abschluss-Review des ganzen Branches (Opus).
Alle Abweichungen vom Plan (Test-Pins, Kommentar-/Doku-Wahrheit, ein Testname, zwei Commit-Messages, slowakischer
Kartentext) mit Befund und Begründung in `D:\Entwicklung\HASI\issue10-work\deviations.md`; Mutanten 40 (statt 24),
alle getötet (`mutate-final2.txt`). Offene Fragen an den User und PR-Notizen: `issue10-work\final-review-carry.md`.

## Arbeitsumgebung

- **Worktree:** `D:\Entwicklung\HASI\issue10-work\wt`, Branch `fix/seasonal-outlook`, Basis `bbf2e151`
  (`upstream/master`, v2026.10.04), ohne Tracking. `_local_socket_unblock.py` liegt im Worktree (über
  `.git/info/exclude` ausgeblendet).
- **Tests** (aus dem Worktree; es gibt dort kein eigenes `.venv`):
  `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **Volle Suite mit Namensvergleich:** `bash /d/Entwicklung/HASI/issue10-work/run_suite.sh <tag>` →
  `../suite-<tag>.txt`, `../names-<tag>.txt`, Vergleich gegen `../names-base.txt` (Baseline auf `bbf2e151`).
- **Lint** (zählt in CI, nur das Integrationsverzeichnis): `uvx black custom_components/irrigation_plus/` und
  `uvx ruff check custom_components/irrigation_plus/`. Die Testdatei zusätzlich mit `uvx black` formatieren.
- **Commits:** einer je grünem Task, Message per Heredoc (`git commit -F - <<'EOF' … EOF`), Englisch, endet mit
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **Kein Text verweist auf unsere Issues** (`Eifel-Joe#…`,
  Spec- oder Task-Nummern), weder im Code noch in Tests noch in Commit-Messages: der PR geht an JustChr.
- **Anker:** Jeder „Ersetze“-Block kommt in seiner Datei genau einmal vor. Kommt er nicht oder mehrfach vor, ist die
  Basis eine andere als geplant: STOP und melden, nicht frei anpassen.
- ⚠️ **Lokaler Vorbestand, kein Fehler dieses Plans:** Jeder Test mit dem `coordinator`-Fixture endet lokal
  **zusätzlich** mit `ERROR at teardown … Lingering timer after test` (der Zeit-Listener `_reset_event_fired_today` des
  Koordinators; alle elf bestehenden Kalender-Tests stehen so in der Baseline, in JustChrs CI laufen sie sauber). RED und
  GREEN liest man an der **Testphase** ab: „failed“ bzw. „passed“. Die Zahl der teardown-ERRORs ist je Lauf gleich der
  Zahl der gewählten Fixture-Tests und ändert sich zwischen RED und GREEN nicht. Ein ERROR, der **nicht** „at teardown“
  mit „Lingering timer“ ist, ist echt: STOP.

## Datei-Übersicht

| Datei | Änderung | Task |
|---|---|---|
| `custom_components/irrigation_plus/watering_calendar.py` | PyETO ohne Regen; Mengenformel mit Kc und Regel-Frage; Static- und Passthrough-Zweig; Klimaphasen; `calculation_notes` | 1–6 |
| `tests/test_watering_calendar.py` | neue Tests, zwei Fixtures ergänzt | 1–8 |
| `custom_components/irrigation_plus/services.yaml`, `translations/*.json` (8) | Dienstbeschreibung | 7 |
| `custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts`, `frontend/localize/languages/*.json` (8), `frontend/dist/*` | Hinweiszeile | 8 |
| `docs/configuration-weather-location.md`, `docs/usage-services.md` | Doku | 9 |

---

### Task 0: Baseline

- [x] **Schritt 1:** `bash /d/Entwicklung/HASI/issue10-work/run_suite.sh base` (nur falls `../names-base.txt` fehlt).
  Erwartet: `BASE NAMES IDENTICAL WITH issue8 bbf2 BASELINE (422 names)`; Zählerzeile `7 failed, 3667 passed, 9 skipped,
  415 errors` (die 7/415 sind Vorbestand der lokalen Windows-Umgebung, siehe Memory `hasi-local-test-env-rebuild`).
- [x] **Schritt 2:** `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest
  tests/test_watering_calendar.py tests/test_watering_calendar_api.py tests/test_i18n_completeness.py -p
  _local_socket_unblock -q` → `82 passed, 11 errors` (die elf teardown-ERRORs der Kalender-Tests, siehe
  Arbeitsumgebung).

---

### Task 1: Die PyETO-ET enthält keinen Regen

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (Docstring, Imports,
`_calculate_monthly_et_pyeto`); Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Imports und Hilfen der Testdatei**

**Ersetze in `tests/test_watering_calendar.py`:**
```python
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
```
**durch:**
```python
import json
import math
import pathlib
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
    ZONE_ID,
    ZONE_MAPPING,
```
**durch:**
```python
    ZONE_ID,
    ZONE_KC,
    ZONE_MAPPING,
```

- [x] **Schritt 2: Die zwei roten Tests anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python


_ROOT = pathlib.Path(__file__).parent.parent / "custom_components" / "irrigation_plus"

# Weather for the PyETO helper; only the mocked equation reads it.
_JULY_WEATHER = {
    "avg_temp": 25.0,
    "min_temp": 15.0,
    "max_temp": 35.0,
    "precipitation": 50.0,
    "humidity": 65.0,
    "wind_speed": 3.0,
    "pressure": 1013.25,
    "dewpoint": 18.0,
}


def _module_instance(name, **attrs):
    """A calculation-module instance as the calendar sees it: a name and its call."""
    module = Mock()
    module.name = name
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


class TestAMonthIsPricedByTheCalculationsRules:
    """The projection prices a month the way the calculation prices its days.

    Only PyETO books rain, Kc scales the ET term and not the rain, and a
    module's daily figure is scaled by the days of the month.
    """

    @pytest.mark.asyncio
    async def test_a_pyeto_month_carries_no_rain(self, coordinator, mock_pyeto_module):
        """The equation returns -ET0 with no rain in it; the month is ET0 x days.

        Adding the month's rain to it showed rain as ET, and subtracting it again
        later left the volume blind to rain.
        """
        mock_pyeto_module.calculate_et_for_day = Mock(return_value=-2.0)

        july = coordinator._calculate_monthly_et_pyeto(
            _JULY_WEATHER, mock_pyeto_module, 7
        )

        assert july == pytest.approx(62.0)  # 2.0 mm x 31 days

    @pytest.mark.asyncio
    async def test_a_pyeto_zone_has_the_rain_subtracted_once(
        self, coordinator, mock_pyeto_module
    ):
        """Through the whole calendar: ET without rain, the volume net of it once."""
        mock_pyeto_module.calculate_et_for_day = Mock(return_value=-2.0)

        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=mock_pyeto_module),
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        july = calendar_data[1]["monthly_estimates"][6]
        rain = july["average_precipitation_mm"]
        assert july["estimated_et_mm"] == pytest.approx(62.0)
        # The fixture zone: 100 m2, multiplier 1, no Kc (reads as 1.0).
        assert july["estimated_watering_volume_liters"] == pytest.approx(
            round(max(0.0, 62.0 - rain) * 100.0, 1)
        )
```

- [x] **Schritt 3: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "carries_no_rain or subtracted_once" -p _local_socket_unblock -q`
Expected: 2 failed — `assert 112.0 == 62.0 ± …` und `assert 122.0 == 62.0 ± …` (heute steckt der Monatsregen in der ET). Dazu 2 teardown-ERRORs.

- [x] **Schritt 4: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
elevation). Named watering_calendar (not calendar) to avoid shadowing the stdlib
``calendar`` module, which _calculate_monthly_et_pyeto imports locally.
"""

import logging
```
**durch:**
```python
elevation). Named watering_calendar (not calendar) to avoid shadowing the stdlib
``calendar`` module, which this module imports.
"""

import calendar
import logging
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # Get days in month
        import calendar

        days_in_month = calendar.monthrange(2024, month)[
            1
        ]  # Use 2024 as reference year

        # Convert daily ET delta to monthly total (remove precipitation since we want just ET)
        daily_et = abs(daily_et_delta) + month_data["precipitation"] / days_in_month
        return daily_et * days_in_month
```
**durch:**
```python
        days_in_month = calendar.monthrange(2024, month)[1]  # 2024: reference year

        # The delta is -ET0 with no precipitation in it (calculate_et_for_day
        # returns ``-eto``), so the month's ET is its size times the days. Rain is
        # subtracted once, in the volume, and only where the calculation books it.
        return abs(daily_et_delta) * days_in_month
```

- [x] **Schritt 5: GREEN prüfen**

Run: wie Schritt 3. Expected: 2 passed (+ 2 teardown-ERRORs). Dann `… -m pytest tests/test_watering_calendar.py -p
_local_socket_unblock -q` → kein „failed“.

- [x] **Schritt 6: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): the seasonal ET carries no rain

calculate_et_for_day returns -ET0 with no precipitation in it. The PyETO
branch nevertheless added the month's rain to the ET and the volume
subtracted it again, so the seasonal outlook showed rain as evaporation
and the watering volume never went down for rain.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Die Menge fragt die Regel der Rechnung und skaliert mit Kc

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (Import, `_calculate_monthly_watering_volume`);
Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Die zwei bestehenden Volumen-Tests bekommen ihr Modul ausdrücklich**

Der Mock-Store liefert für jede ID das PyETO-Modul; die Zonen dieser zwei Tests nennen künftig ihr Modul selbst, statt
vom Auffangverhalten des Mocks zu leben. Erwartungen unverändert.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,  # 100 m²
            ZONE_MULTIPLIER: 1.0,
        }
```
**durch:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,  # 100 m²
            ZONE_MULTIPLIER: 1.0,
            ZONE_MODULE: 1,  # PyETO: the module rain is booked for
        }
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        test_zone = {ZONE_SIZE: 100.0, ZONE_MULTIPLIER: 1.0}
```
**durch:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,
            ZONE_MULTIPLIER: 1.0,
            ZONE_MODULE: 1,  # PyETO: the module rain is booked for
        }
```

- [x] **Schritt 2: Rote Tests anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    @pytest.mark.asyncio
    async def test_kc_scales_the_et_term_and_not_the_rain(self, coordinator):
        """As in the calculation: et_delta = delta x kc, precipitation unscaled."""
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: 0.5}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 * 0.5 - 20.0) * 10.0)  # 110 L

    @pytest.mark.asyncio
    async def test_a_zone_whose_kc_is_none_reads_as_the_default(self, coordinator):
        """A stored ``kc: None`` falls back to 1.0, as in the calculation."""
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: None}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 - 20.0) * 10.0)

    @pytest.mark.asyncio
    async def test_a_module_without_rain_gets_none_subtracted(
        self, coordinator, mock_store
    ):
        """Static and Passthrough book no rain in the calculation, so here neither."""
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 93.0, {"precipitation": 60.0}
        )

        assert volume == pytest.approx(930.0)
```

- [x] **Schritt 3: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "kc_scales or kc_is_none or module_without_rain" -p
_local_socket_unblock -q`
Expected: 2 failed (`420.0 == 110.0`, `330.0 == 930.0`), 1 passed (`kc_is_none` ist ein Pin für den `None`-Fall; er
ist schon heute grün, weil Kc noch gar nicht gelesen wird). Dazu 3 teardown-ERRORs.

- [x] **Schritt 4: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
from . import const
from .const import SmartIrrigationError
```
**durch:**
```python
from . import const
from .calculation import zone_module_models_weather
from .const import SmartIrrigationError
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        """Calculate monthly watering volume in liters for a zone.

        Args:
            zone: Zone configuration dictionary.
            et_mm: Monthly evapotranspiration in mm.
            month_data: Monthly climate data.

        Returns:
            float: Watering volume in liters.

        """
        zone_size_m2 = zone.get(const.ZONE_SIZE, 1.0)  # Default 1 m²
        multiplier = zone.get(const.ZONE_MULTIPLIER, 1.0)
        precipitation_mm = month_data.get("precipitation", 0.0)
```
**durch:**
```python
        """Calculate monthly watering volume in liters for a zone.

        A day of the calculation, summed over the month: the zone's Kc scales the
        ET term and not the rain, and rain counts only for a module the
        calculation books it for (``zone_module_models_weather``, the question
        the calculation itself asks).

        Args:
            zone: Zone configuration dictionary.
            et_mm: Monthly evapotranspiration in mm, before the zone's Kc.
            month_data: Monthly climate data.

        Returns:
            float: Watering volume in liters.

        """
        zone_size_m2 = zone.get(const.ZONE_SIZE, 1.0)  # Default 1 m²
        multiplier = zone.get(const.ZONE_MULTIPLIER, 1.0)
        kc = zone.get(const.ZONE_KC, const.CONF_DEFAULT_KC)
        if kc is None:
            kc = const.CONF_DEFAULT_KC
        if zone_module_models_weather(self.store, zone):
            precipitation_mm = month_data.get("precipitation", 0.0)
        else:
            # Static and Passthrough hand back a number the install supplied; the
            # calculation books no rain for them, so neither does the projection.
            precipitation_mm = 0.0
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        net_water_need_mm = max(0, et_mm - precipitation_mm)
```
**durch:**
```python
        net_water_need_mm = max(0, et_mm * kc - precipitation_mm)
```

- [x] **Schritt 5: GREEN prüfen**

Run: wie Schritt 3. Expected: 3 passed (+ 3 teardown-ERRORs). Dann die ganze Datei → kein „failed“.

- [x] **Schritt 6: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): the seasonal volume follows the calculation's rain and Kc

The calculation books rain only for a module that models weather (PyETO)
and scales the ET term, not the rain, by the zone's crop coefficient.
The seasonal volume subtracted rain for every module and never read Kc.
It now asks zone_module_models_weather, the question the calculation and
the live estimate already ask, and applies Kc like the calculation does.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Static liefert einen Monatsbedarf

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (Schleife in
`_calculate_monthly_watering_for_zone`); Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Rote Tests anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    @pytest.mark.asyncio
    async def test_a_static_demand_becomes_a_monthly_volume(
        self, coordinator, mock_store
    ):
        """The static delta is a daily bucket change, negative for demand.

        Read as a month's ET it was a negative number, and max(0, ...) turned
        every demand into 0 L.
        """
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        static = _module_instance("Static", calculate=Mock(return_value=-3.0))

        with patch.object(
            coordinator, "getModuleInstanceByID", new=AsyncMock(return_value=static)
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        july = calendar_data[1]["monthly_estimates"][6]
        assert july["estimated_et_mm"] == pytest.approx(93.0)  # 3.0 mm x 31 days
        # 100 m2, multiplier 1, Kc 1.0, and no rain subtracted for Static.
        assert july["estimated_watering_volume_liters"] == pytest.approx(9300.0)

    @pytest.mark.asyncio
    async def test_a_static_surplus_needs_nothing(self, coordinator, mock_store):
        """A positive static delta adds water every day: no demand, no volume."""
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        static = _module_instance("Static", calculate=Mock(return_value=2.0))

        with patch.object(
            coordinator, "getModuleInstanceByID", new=AsyncMock(return_value=static)
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        july = calendar_data[1]["monthly_estimates"][6]
        assert july["estimated_et_mm"] == 0.0
        assert july["estimated_watering_volume_liters"] == 0.0
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "static_demand or static_surplus" -p _local_socket_unblock -q`
Expected: 2 failed (`-3.0 == 93.0`, `2.0 == 0.0`), dazu 2 teardown-ERRORs.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
            month_data = monthly_data[month - 1]

            try:
```
**durch:**
```python
            month_data = monthly_data[month - 1]
            days_in_month = calendar.monthrange(2024, month)[1]

            try:
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
                elif modinst.name == "Static":
                    et_estimate = modinst.calculate()
```
**durch:**
```python
                elif modinst.name == "Static":
                    # A daily bucket change with the calculation's sign: negative
                    # is demand, and a surplus needs nothing.
                    et_estimate = max(0.0, -modinst.calculate()) * days_in_month
```

- [x] **Schritt 4: GREEN prüfen**

Run: wie Schritt 2. Expected: 2 passed (+ 2 teardown-ERRORs). Ganze Datei ohne „failed“.

- [x] **Schritt 5: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): a static zone's demand becomes a monthly volume

The Static module hands back a daily bucket change with the calculation's
sign, negative for demand. The calendar read it as the month's ET, so a
demand became a negative ET and max(0, ...) turned it into 0 L. It is now
the demand per day times the days of the month; a surplus needs nothing.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Passthrough rechnet mit den Tagen des Monats

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py`; Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Roten Test anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    @pytest.mark.asyncio
    async def test_a_passthrough_month_has_its_own_number_of_days(
        self, coordinator, mock_store
    ):
        """February 2024 has 29 days, not 30, and Passthrough books no rain."""
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Passthrough"}
        passthrough = _module_instance("Passthrough")

        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=passthrough),
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        daily = coordinator._generate_monthly_climate_data()[1]["average_daily_et"]
        february = calendar_data[1]["monthly_estimates"][1]
        assert february["estimated_et_mm"] == pytest.approx(round(daily * 29, 2))
        assert february["estimated_watering_volume_liters"] == pytest.approx(
            round(daily * 29 * 100.0, 1)
        )
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "own_number_of_days" -p _local_socket_unblock -q`
Expected: 1 failed (`8.04 == 7.77`: ET mit 30 statt 29 Tagen), dazu 1 teardown-ERROR.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
                    et_estimate = (
                        month_data.get("average_daily_et", 3.0) * 30
                    )  # mm/month
```
**durch:**
```python
                    et_estimate = (
                        month_data.get("average_daily_et", 3.0) * days_in_month
                    )  # mm/month
```

- [x] **Schritt 4: GREEN prüfen**

Run: wie Schritt 2. Expected: 1 passed (+ 1 teardown-ERROR). Ganze Datei ohne „failed“.

- [x] **Schritt 5: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): every branch scales a daily figure by the days of the month

The PyETO branch multiplies its daily ET by the month's days; the branch
for the other modules multiplied by 30, so February came out a day long.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Jede Jahreskurve tut, was ihr Kommentar sagt

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (`_generate_monthly_climate_data`);
Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Rote Tests anhängen (neue Klasse)**

**Hänge an `tests/test_watering_calendar.py` an:**
```python


class TestTheClimateCurvesDoWhatTheirCommentsSay:
    """The synthetic climate is an illustration, but each curve keeps its word."""

    @pytest.mark.asyncio
    async def test_a_northern_winter_is_wetter_windier_and_more_humid(
        self, coordinator
    ):
        """Temperate north: humidity, wind and rain peak in January, ET in July."""
        coordinator._latitude = 50.0

        rows = coordinator._generate_monthly_climate_data()
        january, july = rows[0], rows[6]

        assert january["humidity"] == pytest.approx(80.0)
        assert july["humidity"] == pytest.approx(50.0)
        assert january["wind_speed"] == pytest.approx(4.0)
        assert july["wind_speed"] == pytest.approx(2.0)
        assert january["precipitation"] == pytest.approx(120.0)
        assert july["precipitation"] == pytest.approx(60.0)
        assert july["average_daily_et"] > january["average_daily_et"]
        assert july["avg_temp"] > january["avg_temp"]

    @pytest.mark.asyncio
    async def test_the_southern_hemisphere_mirrors_every_seasonal_curve(
        self, coordinator
    ):
        """South of the equator July is winter for every curve, not just the heat."""
        coordinator._latitude = -50.0

        rows = coordinator._generate_monthly_climate_data()
        january, july = rows[0], rows[6]

        assert july["humidity"] == pytest.approx(80.0)
        assert january["humidity"] == pytest.approx(50.0)
        assert july["wind_speed"] == pytest.approx(4.0)
        assert july["precipitation"] == pytest.approx(120.0)
        assert january["average_daily_et"] > july["average_daily_et"]
        assert january["avg_temp"] > july["avg_temp"]

    @pytest.mark.asyncio
    async def test_tropical_rain_keeps_its_curve(self, coordinator):
        """Its comment names no season, so this curve stays as it was (a pin)."""
        coordinator._latitude = 10.0

        rows = coordinator._generate_monthly_climate_data()

        assert [round(r["precipitation"], 6) for r in rows] == [
            round(60.0 * (1.0 + 0.3 * math.sin((m - 1) * math.pi / 6)), 6)
            for m in range(1, 13)
        ]
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "TestTheClimateCurves" -p _local_socket_unblock -q`
Expected: 2 failed (Norden: Feuchte Januar `50.0 == 80.0`; Süden: `average_daily_et` Januar nicht über Juli),
1 passed (der tropische Pin ist schon heute grün), dazu 3 teardown-ERRORs.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        monthly_data = []

        for month in range(1, 13):
            # Calculate seasonal temperature variation
            temp_factor = math.cos((month - 7) * math.pi / 6)  # Peak in July (month 7)
            if self._latitude and self._latitude < 0:  # Southern hemisphere
                temp_factor = -temp_factor

            avg_temp = base_temp + (temp_variation * temp_factor)
```
**durch:**
```python
        monthly_data = []

        # Every seasonal curve below peaks in the local summer or the local
        # winter, so the southern hemisphere mirrors all of them, not just the
        # temperature.
        hemisphere = -1.0 if self._latitude and self._latitude < 0 else 1.0

        for month in range(1, 13):
            # +1 at the height of the local summer, -1 in the depth of its winter
            # (July and January in the north).
            summer = hemisphere * math.cos((month - 7) * math.pi / 6)

            avg_temp = base_temp + (temp_variation * summer)
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
                precip_factor = 1.5 - 0.5 * math.cos(
                    (month - 1) * math.pi / 6
                )  # More in winter
```
**durch:**
```python
                precip_factor = 1.5 - 0.5 * summer  # More in winter
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
            humidity = 65.0 + 15.0 * math.cos((month - 7) * math.pi / 6)

            # Wind speed (slightly higher in winter)
            wind_speed = 3.0 + 1.0 * math.cos((month - 7) * math.pi / 6)
```
**durch:**
```python
            humidity = 65.0 - 15.0 * summer

            # Wind speed (slightly higher in winter)
            wind_speed = 3.0 - 1.0 * summer
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
                    "average_daily_et": 2.0
                    + 2.0 * math.cos((month - 7) * math.pi / 6),  # Higher ET in summer
```
**durch:**
```python
                    "average_daily_et": 2.0 + 2.0 * summer,  # Higher ET in summer
```

- [x] **Schritt 4: GREEN prüfen**

Run: wie Schritt 2. Expected: 3 passed (+ 3 teardown-ERRORs). Ganze Datei ohne „failed“ (auch `test_generate_monthly_climate_data`: Juli wärmer als
Januar).

- [x] **Schritt 5: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): each seasonal curve peaks where its comment says

Humidity, wind and temperate rain are commented "higher in winter" but
peaked in July, and the southern hemisphere mirrored only the
temperature. All seasonal curves now share one sign: the local summer.
The constants of the synthetic climate are unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Jeder Monat nennt seine Herkunft

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py`; Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Roten Test anhängen (neue Klasse)**

**Hänge an `tests/test_watering_calendar.py` an:**
```python


class TestTheOutlookSaysWhatItIs:
    """Every place that shows or describes the outlook calls it an illustration."""

    @pytest.mark.asyncio
    async def test_each_month_notes_its_climate_comes_from_latitude(
        self, coordinator, mock_pyeto_module
    ):
        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=mock_pyeto_module),
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        notes = [m["calculation_notes"] for m in calendar_data[1]["monthly_estimates"]]
        assert all("latitude" in note for note in notes), notes
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "comes_from_latitude" -p _local_socket_unblock -q`
Expected: 1 failed (`Based on typical January climate patterns`), dazu 1 teardown-ERROR.

- [x] **Schritt 3: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
                        "calculation_notes": f"Based on typical {month_name} climate patterns",
```
**durch:**
```python
                        "calculation_notes": f"Illustrative {month_name} climate derived from latitude only",
```

- [x] **Schritt 4: GREEN prüfen**, dann **Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): each month says its climate is derived from latitude

"Based on typical climate patterns" read like local climate. The climate
behind the outlook is a fixed curve chosen by latitude alone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Die Dienstbeschreibung sagt, woher das Klima kommt

**Files:** Modify `custom_components/irrigation_plus/services.yaml`, `custom_components/irrigation_plus/translations/*.json`
(8); Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Roten Test anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    def test_the_service_description_says_where_the_climate_comes_from(self):
        """Not 'representative climate data': a climate derived from latitude alone.

        NOT-TO-DO: do not pin the other seven languages word for word; key parity
        and the untranslated-string check in test_i18n_completeness cover them.
        """
        en = json.loads(
            (_ROOT / "translations" / "en.json").read_text(encoding="utf-8")
        )
        description = en["services"]["generate_watering_calendar"]["description"]
        yaml_text = (_ROOT / "services.yaml").read_text(encoding="utf-8")

        assert "latitude" in description
        assert "representative" not in description
        assert "representative climate data" not in yaml_text
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "service_description" -p _local_socket_unblock -q`
Expected: 1 failed.

- [x] **Schritt 3: Implementierung (9 Dateien)**

**Ersetze in `custom_components/irrigation_plus/services.yaml`:**
```yaml
  description: Generate a 12-month watering calendar for irrigation zones based on representative climate data.
```
**durch:**
```yaml
  description: Generate a 12-month watering calendar for irrigation zones based on an illustrative climate derived from latitude only.
```

**Ersetze in `custom_components/irrigation_plus/translations/en.json`:**
```json
      "description": "Generate a 12-month watering calendar for irrigation zones based on representative climate data",
```
**durch:**
```json
      "description": "Generate a 12-month watering calendar for irrigation zones based on an illustrative climate derived from latitude only",
```

**Ersetze in `custom_components/irrigation_plus/translations/de.json`:**
```json
      "description": "Einen 12-Monats-Bewässerungskalender für Bewässerungszonen auf Basis repräsentativer Klimadaten erstellen",
```
**durch:**
```json
      "description": "Einen 12-Monats-Bewässerungskalender für Bewässerungszonen auf Basis eines veranschaulichenden Klimas allein aus dem Breitengrad erstellen",
```

**Ersetze in `custom_components/irrigation_plus/translations/es.json`:**
```json
      "description": "Generar un calendario de riego de 12 meses para las zonas de riego basado en datos climáticos representativos",
```
**durch:**
```json
      "description": "Generar un calendario de riego de 12 meses para las zonas de riego basado en un clima ilustrativo derivado solo de la latitud",
```

**Ersetze in `custom_components/irrigation_plus/translations/fr.json`:**
```json
      "description": "Générer un calendrier d'arrosage de 12 mois pour les zones d'irrigation à partir de données climatiques représentatives",
```
**durch:**
```json
      "description": "Générer un calendrier d'arrosage de 12 mois pour les zones d'irrigation à partir d'un climat indicatif déduit de la seule latitude",
```

**Ersetze in `custom_components/irrigation_plus/translations/it.json`:**
```json
      "description": "Genera un calendario di irrigazione di 12 mesi per le zone di irrigazione in base a dati climatici rappresentativi",
```
**durch:**
```json
      "description": "Genera un calendario di irrigazione di 12 mesi per le zone di irrigazione in base a un clima indicativo ricavato solo dalla latitudine",
```

**Ersetze in `custom_components/irrigation_plus/translations/nl.json`:**
```json
      "description": "Genereer een irrigatiekalender van 12 maanden voor irrigatiezones op basis van representatieve klimaatgegevens",
```
**durch:**
```json
      "description": "Genereer een irrigatiekalender van 12 maanden voor irrigatiezones op basis van een illustratief klimaat dat alleen van de breedtegraad is afgeleid",
```

**Ersetze in `custom_components/irrigation_plus/translations/no.json`:**
```json
      "description": "Generer en 12-måneders vanningskalender for vanningssoner basert på representative klimadata",
```
**durch:**
```json
      "description": "Generer en 12-måneders vanningskalender for vanningssoner basert på et illustrativt klima utledet kun fra breddegraden",
```

**Ersetze in `custom_components/irrigation_plus/translations/sk.json`:**
```json
      "description": "Vygenerovať 12-mesačný zavlažovací kalendár pre zavlažovacie zóny na základe reprezentatívnych klimatických údajov",
```
**durch:**
```json
      "description": "Vygenerovať 12-mesačný zavlažovací kalendár pre zavlažovacie zóny na základe ilustratívnej klímy odvodenej iba zo zemepisnej šírky",
```

- [x] **Schritt 4: GREEN prüfen**

Run: `… -m pytest tests/test_watering_calendar.py tests/test_i18n_completeness.py -p _local_socket_unblock -q` → kein
„failed“; die ERRORs sind nur teardown-ERRORs.

- [x] **Schritt 5: Commit**

```bash
git add custom_components/irrigation_plus/services.yaml custom_components/irrigation_plus/translations/ tests/test_watering_calendar.py
git diff --cached --name-only | wc -l    # erwartet 10
git commit -F - <<'EOF'
fix(calendar): the service description says where the climate comes from

"Representative climate data" promised more than a fixed seasonal curve
chosen by latitude. Reworded in services.yaml and all eight languages.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Die Karte „Saisonaler Ausblick“ zeigt eine Hinweiszeile

**Files:** Modify `custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts`,
`custom_components/irrigation_plus/frontend/localize/languages/*.json` (8), `frontend/dist/` (gebaut);
Test `tests/test_watering_calendar.py`.

- [x] **Schritt 1: Roten Test anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    def test_the_seasonal_card_shows_the_illustration_note(self):
        """A tripwire on the panel's source, kept here because CI runs pytest only."""
        view = (
            _ROOT / "frontend" / "src" / "views" / "weather" / "view-weather-data.ts"
        ).read_text(encoding="utf-8")
        en = json.loads(
            (_ROOT / "frontend" / "localize" / "languages" / "en.json").read_text(
                encoding="utf-8"
            )
        )

        seasonal = view[view.index("private _renderSeasonal") :]
        seasonal = seasonal[: seasonal.index("private _renderForecast")]
        assert "panels.setup.weather_data.seasonal_note" in seasonal
        assert "latitude" in en["panels"]["setup"]["weather_data"]["seasonal_note"]
```

- [x] **Schritt 2: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "illustration_note" -p _local_socket_unblock -q`
Expected: 1 failed.

- [x] **Schritt 3: Implementierung — Ansicht**

**Ersetze in `custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts`:**
```ts
            : html`
                <div class="seasonal-table">
```
**durch:**
```ts
            : html`
                <div class="weather-note">
                  ${localize("panels.setup.weather_data.seasonal_note", lang)}
                </div>
                <div class="seasonal-table">
```

- [x] **Schritt 4: Implementierung — acht Sprachdateien**

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/en.json`:**
```json
        "seasonal_title": "Seasonal outlook"
```
**durch:**
```json
        "seasonal_title": "Seasonal outlook",
        "seasonal_note": "Illustrative values derived from your latitude only — not measured weather data."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/de.json`:**
```json
        "seasonal_title": "Saisonaler Ausblick"
```
**durch:**
```json
        "seasonal_title": "Saisonaler Ausblick",
        "seasonal_note": "Veranschaulichung allein aus dem Breitengrad – keine gemessenen Wetterdaten."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/es.json`:**
```json
        "seasonal_title": "Perspectiva estacional"
```
**durch:**
```json
        "seasonal_title": "Perspectiva estacional",
        "seasonal_note": "Valores ilustrativos derivados solo de la latitud, no datos meteorológicos medidos."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/fr.json`:**
```json
        "seasonal_title": "Perspective saisonnière"
```
**durch:**
```json
        "seasonal_title": "Perspective saisonnière",
        "seasonal_note": "Valeurs indicatives déduites de la seule latitude, pas des données météo mesurées."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/it.json`:**
```json
        "seasonal_title": "Prospettiva stagionale"
```
**durch:**
```json
        "seasonal_title": "Prospettiva stagionale",
        "seasonal_note": "Valori indicativi ricavati solo dalla latitudine, non dati meteo misurati."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/nl.json`:**
```json
        "seasonal_title": "Seizoensvooruitzicht"
```
**durch:**
```json
        "seasonal_title": "Seizoensvooruitzicht",
        "seasonal_note": "Illustratieve waarden, alleen afgeleid van de breedtegraad, geen gemeten weergegevens."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/no.json`:**
```json
        "seasonal_title": "Sesongutsikt"
```
**durch:**
```json
        "seasonal_title": "Sesongutsikt",
        "seasonal_note": "Illustrative verdier utledet kun fra breddegraden, ikke målte værdata."
```

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/sk.json`:**
```json
        "seasonal_title": "Sezónny výhľad"
```
**durch:**
```json
        "seasonal_title": "Sezónny výhľad",
        "seasonal_note": "Ilustračné hodnoty odvodené iba zo zemepisnej šírky, nie namerané údaje o počasí."
```

- [x] **Schritt 5: GREEN prüfen**

Run: `… -m pytest tests/test_watering_calendar.py tests/test_i18n_completeness.py -p _local_socket_unblock -q` → kein
„failed“, nur teardown-ERRORs (die Vollständigkeitstests prüfen den neuen Schlüssel in allen acht Sprachen und dass keiner englisch geblieben ist).

- [x] **Schritt 6: Frontend bauen**

```bash
cd custom_components/irrigation_plus/frontend && npm ci && npm run build && npx tsc --noEmit -p . ; cd -
for f in custom_components/irrigation_plus/frontend/dist/*.js; do git diff --quiet -- "$f" && echo "same    $f" || echo "CHANGED $f"; done
```
Expected: Build ohne Fehler, `tsc` ohne Fehler; geändert genau `irrigation-plus.js` (Ansicht und Kataloge, im
Probelauf +4/−1 Zeilen) und `irrigation-plus-card-impl.js` (enthält die Kataloge, +1/−1); `-card.js` und
`-card-legacy.js` inhaltlich gleich. Bundles, die `git diff --quiet` als gleich
meldet und `git status` trotzdem mit `M` zeigt, sind nur `autocrlf`: `git checkout -- <bundle>`.

- [x] **Schritt 7: Commit**

```bash
git add custom_components/irrigation_plus/frontend/src/views/weather/view-weather-data.ts custom_components/irrigation_plus/frontend/localize/languages/ tests/test_watering_calendar.py
git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js
git diff --cached --name-only | wc -l    # erwartet 12 (Ansicht, 8 Kataloge, Testdatei, 2 Bundles)
git commit -F - <<'EOF'
fix(calendar): the seasonal outlook card says it is an illustration

The card showed evapotranspiration, rain and temperature per month as if
they were the local climate. A note line now says they are derived from
the latitude alone, in all eight languages.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Doku

**Files:** Modify `docs/configuration-weather-location.md`, `docs/usage-services.md`.

- [x] **Schritt 1: Implementierung**

**Ersetze in `docs/configuration-weather-location.md`:**
```markdown
A 12-month climate estimate for your location: expected evapotranspiration, precipitation and average temperature per month. It answers "how much watering should I expect over the year" and is the replacement for the old per-zone watering calendar — climate is a property of your location, not of a zone, so it is shown once here.
```
**durch:**
```markdown
A rough 12-month illustration: evapotranspiration, precipitation and average temperature per month, derived from your latitude alone. The climate behind it is a fixed seasonal curve, not measured weather and not a forecast for your garden, so read it as an order of magnitude. With PyETO, "ET" is the reference evapotranspiration, before a zone's crop coefficient. It replaces the old per-zone watering calendar and is shown once here, because it depends only on where you are. The monthly watering volume per zone is available through the `generate_watering_calendar` service.
```

**Ersetze in `docs/usage-services.md`:**
```markdown
|`Irrigation Plus: generate_watering_calendar`|Generate a 12-month watering calendar for a zone based on representative climate data.|
```
**durch:**
```markdown
|`Irrigation Plus: generate_watering_calendar`|Generate a 12-month watering calendar for a zone based on an illustrative climate derived from latitude only (not measured weather).|
```

- [x] **Schritt 2: Prüfen und Commit**

```bash
git grep -n -i "representative climate\|climate estimate for your location" -- docs custom_components ; echo "exit $? (1 = nichts gefunden, gewollt)"
git add docs/configuration-weather-location.md docs/usage-services.md
git commit -F - <<'EOF'
docs(calendar): the seasonal outlook is an illustration from latitude

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Gesamtprüfung

- [x] **Schritt 1: Volle Suite** — `bash /d/Entwicklung/HASI/issue10-work/run_suite.sh final`.
  Expected (im Probelauf so gemessen): `7 failed, 3681 passed, 9 skipped, 427 errors` gegen die Baseline
  `7 / 3667 / 9 / 415`: +14 passed = die 14 neuen Tests, +12 errors = die 12 neuen Tests am `coordinator`-Fixture mit dem
  teardown-ERROR. `NAMES DIFFER (422 -> 434)`, unter „added“ **genau** diese zwölf, unter „gone“ nichts:
  `TestAMonthIsPricedByTheCalculationsRules::` `test_a_module_without_rain_gets_none_subtracted`,
  `test_a_passthrough_month_has_its_own_number_of_days`, `test_a_pyeto_month_carries_no_rain`,
  `test_a_pyeto_zone_has_the_rain_subtracted_once`, `test_a_static_demand_becomes_a_monthly_volume`,
  `test_a_static_surplus_needs_nothing`, `test_a_zone_whose_kc_is_none_reads_as_the_default`,
  `test_kc_scales_the_et_term_and_not_the_rain`; `TestTheClimateCurvesDoWhatTheirCommentsSay::`
  `test_a_northern_winter_is_wetter_windier_and_more_humid`, `test_the_southern_hemisphere_mirrors_every_seasonal_curve`,
  `test_tropical_rain_keeps_its_curve`; `TestTheOutlookSaysWhatItIs::test_each_month_notes_its_climate_comes_from_latitude`.
  Jeder andere neue oder fehlende Name ist ein echter Befund: STOP.
- [x] **Schritt 2: Lint** — `uvx black --check custom_components/irrigation_plus/` und `uvx ruff check
  custom_components/irrigation_plus/` sauber; `uvx black --check tests/test_watering_calendar.py` sauber.
- [x] **Schritt 3: Frontend-Frische** — im `frontend/`: `npm run build`, danach `git status --short -- dist/` zeigt keine
  inhaltliche Änderung (`git diff --quiet` je Bundle).
- [x] **Schritt 4: Mutationen** — `/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
  D:/Entwicklung/HASI/issue10-work/mutate.py` (wendet jede Mutation auf eine Kopie der Datei im Worktree an, führt
  `tests/test_watering_calendar.py` mit Timeout aus, stellt die Datei wieder her). Expected: jede Mutation `KILLED`,
  keine `SURVIVED`, keine `HANG`; Ergebnis in `D:\Entwicklung\HASI\issue10-work\mutate-final.txt`.
- [x] **Schritt 5: Keine eigenen Verweise** (Diff und Commit-Messages):

```bash
git diff bbf2e151..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b"
git log bbf2e151..HEAD --format='%H%n%B' | grep -n "Eifel-Joe#"
```
Expected: beide ohne Ausgabe.

- [x] **Schritt 6: Schwester-Pfade** — `git grep -n 'precipitation' custom_components/irrigation_plus/watering_calendar.py`:
  jeder Regenabzug läuft über den einen Zweig in `_calculate_monthly_watering_volume`.

---

### Task 11: Pre-Release und Live-Test auf HA-Test (Ende-zu-Ende-Kriterium der Spec)

Braucht die Freigabe des Users für Push und Release. Ablauf nach Memory `hasi-production-on-upstream` und
Projekt-`CLAUDE.md` (production = `upstream/master` + alle offenen eigenen PRs + Branding; Versionen synchron;
ZIP aus dem SHA).

- [ ] **Schritt 1:** production-Rebuild mit diesem Branch obendrauf (neben `fix/stale-weather-sensor`), Pre-Release
  `vJJJJ.MM.TTbN`, ZIP aus dem SHA, Download geprüft.
- [ ] **Schritt 2:** Auf HA-Test per HACS installieren (`update_information`, dann `download` mit `version`),
  Neustart von HA-Test ankündigen und ausführen.
- [ ] **Schritt 3:** GET `/api/irrigation_plus/watering_calendar` per `ha_manage_custom_tool` (`api_get`), Zonen aus
  den Diagnostics (`data.store.zones`: `size`, `multiplier`, `kc`, `module`). Prüfen:
  (1) Für jede PyETO-Zone und jeden Monat
  `estimated_watering_volume_liters == round(max(0, estimated_et_mm × kc − average_precipitation_mm) × multiplier × size,
  1)` mit Toleranz `0,005 × kc × multiplier × size + 0,05`;
  (2) Niederschlag Januar 120, Juli 60;
  (3) Hinweiszeile in der Karte „Saisonaler Ausblick“ (Sichtprüfung durch den User nach Strg+F5).
  Ergebnis in `D:\Entwicklung\HASI\issue10-work\livetest\L-calendar.md`.

---

### Task 12: PR und Nachlauf

Jeder Schritt nach außen nur mit Freigabe im Chat; vorher die Upstream-Runde wiederholen.

- [ ] **Schritt 1:** PR-Text deutsch, dann englisch zur Freigabe (`## Problem` / `## Fix` / `## Testing`; sagt, dass das
  Klimamodell synthetisch bleibt und nur beschriftet wird, und bietet echte Klimadaten als Folgeschritt an; Footer
  „🤖 Generated with [Claude Code](https://claude.com/claude-code)“; keine eigenen Issue-Verweise).
- [ ] **Schritt 2:** `git push -u origin fix/seasonal-outlook`;
  `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/seasonal-outlook --title "…"
  --body-file <datei>`.
- [ ] **Schritt 3:** P2: Kommentar auf Eifel-Joe#10 (PR-Link, Stand), Label `upstream:gemeldet`; `Eifel-Joe#42` Punkt 11.
- [ ] **Schritt 4:** P1: Plan mit Häkchen und Live-Beleg auf `archive/design-history`.
