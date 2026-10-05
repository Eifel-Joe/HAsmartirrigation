# Abweichungen vom Plan (aus den Quality-Reviews je Task)

Format wie der Plan: `apply_plan_task.py <N> deviations` wendet die Blöcke eines Tasks wörtlich an,
`spec_check.py <N>` erwartet „Basis + Plan-Blöcke + diese Blöcke“ für die Tasks 1..N. Jede Abweichung
nennt Befund, Prüfung und Begründung; abgelehnte Review-Punkte stehen mit Grund darunter.

### Task 1: Abweichungen

**Befunde (Review `10c9d0a8`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R1-1 übernommen: Der Ganzkalender-Test unterscheidet „einmal abgezogen“ von „zweimal“ und „gar nicht“
  nur, weil der Juli-Regen der Fixture-Breite (32,87° aus dem HA-Testgerüst) zufällig 60 mm < 62 mm ET ist
  (RED-Wert 122 = 62 + 60 bestätigt das). Bei Regen ≥ 62 würde die Erwartung 0,0 und „zweimal“ bestünde.
  Wächter-Zeile pinnt die Szene (Memory: Szene so wählen, dass keine falsche Kombination die richtige Zahl
  ergibt).
- R1-2 übernommen: Die Monatslänge des PyETO-Helfers ist nur für Juli (31) gepinnt; `monthrange(2023, …)`
  oder das laufende Jahr überlebte (nur der Februar unterscheidet). Ein Februar-Assert im selben Test, kein
  neuer Testname.
- R1-5 übernommen: Der Kommentar „only the mocked equation reads it“ ist falsch, der Helfer liest alle acht
  Schlüssel selbst (`watering_calendar.py`, `_calculate_monthly_et_pyeto`). Mit dem Februar-Aufruf trägt
  der Name `_JULY_WEATHER` nicht mehr → `_MONTH_WEATHER`.
- R1-3 abgelehnt: Vertragstest „die PyETO-Gleichung ignoriert Regen“ prüft ein anderes Modul; dieselbe
  Annahme trägt `calculation.py` (Regen wird auf das Modul-Delta addiert). Gehört nicht in diesen PR.
- R1-4 abgelehnt: Drei Sätze beschreiben den Stand am Branch-Ende (Regel-Frage, Kc, Klassen-Docstring);
  JustChr squasht, am Kopf sind sie wahr. Wird im Abschluss-Review am Endstand nachgelesen.
- R1-6 abgelehnt: Gerüst (Importe, `_ROOT`, `_module_instance`) ist erst ab späteren Tasks benutzt; CI
  lintet `tests/` nicht, am Kopf ist alles benutzt.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
# Weather for the PyETO helper; only the mocked equation reads it.
_JULY_WEATHER = {
```
**durch:**
```python
# A month as the PyETO helper takes it. The helper reads every key, the mocked
# equation ignores the values, so one month serves for any month number.
_MONTH_WEATHER = {
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        july = coordinator._calculate_monthly_et_pyeto(
            _JULY_WEATHER, mock_pyeto_module, 7
        )

        assert july == pytest.approx(62.0)  # 2.0 mm x 31 days
```
**durch:**
```python
        july = coordinator._calculate_monthly_et_pyeto(
            _MONTH_WEATHER, mock_pyeto_module, 7
        )
        february = coordinator._calculate_monthly_et_pyeto(
            _MONTH_WEATHER, mock_pyeto_module, 2
        )

        assert july == pytest.approx(62.0)  # 2.0 mm x 31 days
        assert february == pytest.approx(58.0)  # 2024, the reference year: 29 days
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        july = calendar_data[1]["monthly_estimates"][6]
        rain = july["average_precipitation_mm"]
        assert july["estimated_et_mm"] == pytest.approx(62.0)
```
**durch:**
```python
        july = calendar_data[1]["monthly_estimates"][6]
        rain = july["average_precipitation_mm"]
        # The scene: some rain, but less than the month's ET, so subtracting it
        # once, twice or not at all gives three different volumes.
        assert 0.0 < rain < 62.0
        assert july["estimated_et_mm"] == pytest.approx(62.0)
```

### Task 2: Abweichungen

**Befunde (Review `41486071`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R2-1 übernommen: Kc ≠ 1 war nur mit PyETO getestet; die Variante „Kc nur, wo Regen gebucht wird“ bestand alle
  Tests. Die Rechnung skaliert das Ergebnis JEDES Moduls (`calculation.py:1246`,
  `et_delta = delta * kc * hour_multiplier`), die Spec-Tabelle sagt `ET × kc` auch für Static/Passthrough → der
  Static-Test bekommt Kc 0,8 (744 L; falsche Varianten 930 / 144 L).
- R2-2 übernommen: Kc 0 ist gültig (UI `min="0"`, `view-zone-settings.ts:1003`; Schema `websockets.py:322`) und
  heißt in der Rechnung „kein ET-Bedarf“; die Variante `zone.get(ZONE_KC) or CONF_DEFAULT_KC` bestand beide
  Kc-Tests. Zweite Zone im None-Test (kein neuer Testname).
- R2-3 übernommen: Kommentar „ET minus precipitation“ direkt über der geänderten Zeile beschreibt sie nicht mehr.
- R2-4 übernommen: „A day of the calculation, summed over the month“ suggeriert Tagesrechnung; es ist die
  bewusste Monatsbilanz (Spec: Eimer-Obergrenze und Drainage nicht modelliert). Docstring präzisiert.
- Nachprüfung `82a921df`: APPROVED. Optionale Anmerkung abgelehnt: eine „Kc-Untergrenze bis 0,32“ bestünde den
  Kc-0-Pin wegen 20 mm Regen — keine realistische Variante; die realistische (`or`) ist getötet (M28).

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        """A stored ``kc: None`` falls back to 1.0, as in the calculation."""
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: None}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 - 20.0) * 10.0)
```
**durch:**
```python
        """A stored ``kc: None`` falls back to 1.0, as in the calculation.

        Only None does: a Kc of 0 is a valid setting and means no ET demand.
        """
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: None}
        zero = {**zone, ZONE_KC: 0.0}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )
        no_demand = coordinator._calculate_monthly_watering_volume(
            zero, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 - 20.0) * 10.0)
        assert no_demand == 0.0
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        """Static and Passthrough book no rain in the calculation, so here neither."""
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 93.0, {"precipitation": 60.0}
        )

        assert volume == pytest.approx(930.0)
```
**durch:**
```python
        """Static and Passthrough book no rain in the calculation, so here neither.

        Kc still scales their figure, as it scales every module's in the calculation.
        """
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: 0.8}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 93.0, {"precipitation": 60.0}
        )

        assert volume == pytest.approx(93.0 * 0.8 * 10.0)  # 744 L
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        A day of the calculation, summed over the month: the zone's Kc scales the
        ET term and not the rain, and rain counts only for a module the
        calculation books it for (``zone_module_models_weather``, the question
        the calculation itself asks).
```
**durch:**
```python
        The month's totals, netted once: the zone's Kc scales the ET term and not
        the rain, as in the calculation, and rain counts only for a module the
        calculation books it for (``zone_module_models_weather`` answers that).
        The bucket's cap and drainage are not modelled.
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # Calculate net water need (ET minus precipitation)
```
**durch:**
```python
        # Net water need: the Kc-scaled ET minus the rain the calculation books
```

### Task 3: Abweichungen

**Befunde (Review `debdb67f`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R3-1 übernommen: Die Monatslänge des Static-Zweigs ist nur für Juli (31) gepinnt; `* 31` fest verdrahtet bestand
  alle Tests (auch am Endstand: Task 4 pinnt den Februar nur für Passthrough über dieselbe Schleifenvariable, nicht
  den Static-Zweig). Gleiche Klasse wie R1-2 → Februar-Assert im selben Test (3,0 × 29 = 87,0), Mutant M29.
- Schwester-Hinweis abgelehnt: `abs(daily_et_delta)` im PyETO-Helfer statt `max(0, −x)` — so in der freigegebenen
  Spec (Rechenregel-Tabelle), und der Task-1-Reviewer fand über 2010 auswertbare Kombinationen (Breite −80…80,
  12 Monate, beide Phasen) kein negatives ET0; der Vorzeichenfall ist im synthetischen Klima unerreichbar.
- Optionale Anmerkung abgelehnt: gemeinsame Konstante für das Bezugsjahr 2024 (Schleife + PyETO-Helfer) wäre ein
  Umbau über die Fehlerbehebung hinaus.
- Nachprüfung `5565c6d1`: APPROVED (M29 und M13 getötet).

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        july = calendar_data[1]["monthly_estimates"][6]
        assert july["estimated_et_mm"] == pytest.approx(93.0)  # 3.0 mm x 31 days
```
**durch:**
```python
        july = calendar_data[1]["monthly_estimates"][6]
        february = calendar_data[1]["monthly_estimates"][1]
        assert july["estimated_et_mm"] == pytest.approx(93.0)  # 3.0 mm x 31 days
        assert february["estimated_et_mm"] == pytest.approx(87.0)  # 2024: 29 days
```

### Task 4: Abweichungen

**Befunde (Review `40d7e172`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R4-1 übernommen: Der Passthrough-Test pinnt nur den Februar; ein zweiglokales `* 29` bestand alle Tests (nur
  dieser Test erreicht den `else`-Zweig). Gleiche Klasse wie R1-2 / R3-1 → Juli (31 Tage) im selben Test,
  Mutant M30. Dazu der Szenen-Kommentar am Volumen-Assert: Februar-Regen am Fixture-Ort 69 mm (Subtropen-Kurve,
  60 · 1,15) gegen 7,77 mm ET — ein Regenabzug ergäbe 0 L.
- Nachprüfung `63eec2db`: APPROVED. Optionale Formulierung („July 31“ als Datum lesbar) abgelehnt: in „has 29 days,
  July 31“ ist die Ellipse eindeutig.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        """February 2024 has 29 days, not 30, and Passthrough books no rain."""
```
**durch:**
```python
        """February 2024 has 29 days, July 31, and Passthrough books no rain."""
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        daily = coordinator._generate_monthly_climate_data()[1]["average_daily_et"]
        february = calendar_data[1]["monthly_estimates"][1]
        assert february["estimated_et_mm"] == pytest.approx(round(daily * 29, 2))
        assert february["estimated_watering_volume_liters"] == pytest.approx(
            round(daily * 29 * 100.0, 1)
        )
```
**durch:**
```python
        climate = coordinator._generate_monthly_climate_data()
        feb_daily = climate[1]["average_daily_et"]
        july_daily = climate[6]["average_daily_et"]
        february = calendar_data[1]["monthly_estimates"][1]
        july = calendar_data[1]["monthly_estimates"][6]
        assert february["estimated_et_mm"] == pytest.approx(round(feb_daily * 29, 2))
        assert july["estimated_et_mm"] == pytest.approx(round(july_daily * 31, 2))
        # 100 m2, multiplier 1, Kc 1.0, and no rain: February's rain is above its
        # ET here, so subtracting it would leave 0 L.
        assert february["estimated_watering_volume_liters"] == pytest.approx(
            round(feb_daily * 29 * 100.0, 1)
        )
```

### Task 5: Abweichungen

**Befunde (Review `62765884`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R5-M1 übernommen: Der neue Kommentar über `hemisphere` („Every seasonal curve below … mirrors all of them“) und die
  Commit-Message („All seasonal curves now share one sign“) behaupten zu viel: der tropische/subtropische Regen
  darunter ist eine Jahreskurve und spiegelt bewusst nicht (Spec: „Ausdrücklich nicht … die Phase des tropischen und
  subtropischen Niederschlags“). Kommentar und Message präzisiert.
- Eigene Beobachtung, dieselbe Klasse: zwei interne Stellen nennen das Klima noch „representative“
  (`watering_calendar.py:125` Kommentar, `:190` Docstring) — genau die Behauptung, die die Arbeit zurücknimmt.
  Formuliert als „illustrative … a fixed curve per latitude band“ (nicht „latitude only“: der Luftdruck kommt aus der
  Höhe, `altitudeToPressure(self._elevation …)`).
- R5-M2 übernommen: Der Tropen-Pin lief nur bei +10°; die Variante „Sinuskurve auch spiegeln“
  (`1.0 + 0.3 * hemisphere * math.sin(…)`) bestand alle Tests. Pin bei +10° und −10°, gleicher Testname; Mutant M31.
- R5-M3 abgelehnt: Taupunkt-Pins — Formel unverändert, ihre Eingänge (Feuchte exakt, Temperatur per Ungleichung) sind
  gepinnt; exakte Temperatur/ET-Werte koppelten die Tests an Konstanten, die außerhalb des Umfangs liegen.
- Für den PR-Text (kein Defekt): Auf der Südhalbkugel ändert der Commit effektiv nur `average_daily_et`
  (Passthrough-ET); Feuchte, Wind, gemäßigter Regen und Taupunkt waren dort schon winterlich (Juli-Gipfel = Südwinter),
  die PyETO-ET-Spalte im Süden ist unverändert. Im Norden: PyETO-ET 50° N Juli 5,13 → 5,67 mm/Tag, Januar 0,85 → 0,66;
  Juli-Regen gemäßigt 120 → 60 mm (Reviewer-Nachrechnung).

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # Generate representative monthly climate data based on location
```
**durch:**
```python
        # The illustrative climate: a fixed seasonal curve per latitude band
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        """Generate representative monthly climate data based on latitude.
```
**durch:**
```python
        """Generate an illustrative monthly climate: a fixed curve per latitude band.
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # Every seasonal curve below peaks in the local summer or the local
        # winter, so the southern hemisphere mirrors all of them, not just the
        # temperature.
```
**durch:**
```python
        # Every curve below that peaks in the local summer or the local winter
        # follows this sign, so the southern hemisphere mirrors all of them, not
        # just the temperature. The tropical and subtropical rain names no season
        # and is the same in both hemispheres.
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        """Its comment names no season, so this curve stays as it was (a pin)."""
        coordinator._latitude = 10.0

        rows = coordinator._generate_monthly_climate_data()

        assert [round(r["precipitation"], 6) for r in rows] == [
            round(60.0 * (1.0 + 0.3 * math.sin((m - 1) * math.pi / 6)), 6)
            for m in range(1, 13)
        ]
```
**durch:**
```python
        """Its comment names no season, so this curve stays as it was (a pin).

        The same in both hemispheres: it is not one of the curves that mirror.
        """
        expected = [
            round(60.0 * (1.0 + 0.3 * math.sin((m - 1) * math.pi / 6)), 6)
            for m in range(1, 13)
        ]

        for latitude in (10.0, -10.0):
            coordinator._latitude = latitude
            rows = coordinator._generate_monthly_climate_data()

            assert [round(r["precipitation"], 6) for r in rows] == expected, latitude
```

**Runde 2 (Nachprüfung `564a3cfd`, „APPROVED WITH MINOR NOTES“):** Der neue Docstring „a fixed curve per latitude
band“ stimmt nicht für den Luftdruck (konstant, aus der Höhe) → ein Satz dazu. Block 5 dieses Abschnitts, aufzubringen
mit `apply_plan_task.py 5 deviations --from 5`. Ebenfalls gemeldet, NICHT umgesetzt: die freigegebenen Nutzertexte der
Tasks 6–9 sagen „latitude only“, obwohl die Höhe (Luftdruck; bei PyETO auch Strahlung/Psychrometerkonstante) leicht
einfließt — Entscheidung E5 des Users, wird ihm mit Alternative vorgelegt. Nachprüfung `5c169d38`: APPROVED.

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        """Generate an illustrative monthly climate: a fixed curve per latitude band.

        Returns:
```
**durch:**
```python
        """Generate an illustrative monthly climate: a fixed curve per latitude band.

        The pressure alone comes from the elevation and is the same in every month.

        Returns:
```

**Commit-Message:**
```text
fix(calendar): each seasonal curve peaks where its comment says

Humidity, wind and temperate rain are commented "higher in winter" but
peaked in July, and the southern hemisphere mirrored only the
temperature. Every curve tied to a season now shares one sign, the
local summer; the tropical and subtropical rain names no season and
stays as it was. The constants of the synthetic climate are unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Task 6: Abweichungen

**Befunde (Review `42687733`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R6-1 übernommen: `all(…)` über eine leere Liste ist wahr — fiele die Zone als Ganzes aus (`monthly_estimates == []`),
  bestünde der Test leer (die Suite fängt es nur woanders, `test_generate_watering_calendar_single_zone`). Und er
  pinnte nur „latitude“: eine Formulierung, die das Wort behält, aber „illustrativ“ verliert („climate typical for your
  latitude“), bestand. → `len == 12`, beide tragenden Wörter, ein Docstring wie bei jedem anderen Test. Mutant M32.
  Bewusst nicht der ganze Satz: die Formulierung „latitude only“ liegt dem User zur Entscheidung vor.
- Nachprüfung `b3e0960c`: APPROVED (M21, M32 getötet).
- Zur Kenntnis (Vorbestand, nicht dieser Commit): ein fehlgeschlagener Monat liefert `estimated_et_mm: 0.0` und Menge
  `0.0` neben `error`, die Karte ignoriert `error` und zeigte 0 ET → Kandidat für ein eigenes Issue (Nebenbefund).
- Für den PR-Text: `calculation_notes` ist API-sichtbar (WebSocket, HTTP-View, Dienst-Event
  `irrigation_plus_watering_calendar_generated`); der neue Wortlaut als eine Zeile erwähnen.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
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
**durch:**
```python
    async def test_each_month_notes_its_climate_comes_from_latitude(
        self, coordinator, mock_pyeto_module
    ):
        """Every month's note calls its climate an illustration from latitude."""
        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=mock_pyeto_module),
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        notes = [m["calculation_notes"] for m in calendar_data[1]["monthly_estimates"]]
        assert len(notes) == 12
        assert all("Illustrative" in n and "latitude" in n for n in notes), notes
```

### Task 7: Abweichungen

**Befunde (Review `4a0d0933`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R7-M1 übernommen: Der Test ließ (a) „…based on typical climate data for your latitude“ in en.json durch (behält
  „latitude“, keine „representative“ — gleiche Klasse wie R6-1/M32), (b) jede YAML-Umformulierung ohne die eine Phrase
  „representative climate data“, (c) jede der sieben Übersetzungen auf dem alten Wortlaut (7 von 9 geänderten Zeilen
  ohne Killer; die i18n-Tests prüfen nur Vorhandensein und „nicht Englisch“). → EN und YAML müssen „illustrative“ und
  „latitude“ tragen (YAML geparst, `yaml` ist in den Tests schon benutzt: `test_services.py`, `test_blueprints.py`);
  in allen 8 Katalogen ist der alte Stamm weg (sprachunabhängiger Ausschluss
  `repr[aäeé]sentati|rappresentati|reprezentat`, kein Wortlaut-Pin; trifft alle 8 alten, keinen der 8 neuen Texte).
  Docstring entsprechend. Mutanten M33 (EN), M34 (YAML), M35 (DE zurück).
- R7-M2 übernommen, umgekehrt: Slowakisch nutzte „ilustratívnej“ (Task 7, committet) und „Ilustračné“ (Task-8-Plan).
  Einheitlich „ilustratívny“ — der noch nicht gebaute Task-8-Text wird angeglichen (Abschnitt Task 8), Task 7 bleibt.
- R7-M3 nicht umgesetzt, dem User vorgelegt: „auf Basis eines veranschaulichenden Klimas allein aus dem Breitengrad“
  liest sich holprig; Vorschlag „…auf Basis eines allein aus dem Breitengrad abgeleiteten Beispielklimas erstellen“.
  Freigegebener Plantext, Sprache des Users → seine Entscheidung, zusammen mit der Frage „latitude only“.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
import json
import math
import pathlib
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.irrigation_plus import SmartIrrigationCoordinator
```
**durch:**
```python
import json
import math
import pathlib
import re
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from custom_components.irrigation_plus import SmartIrrigationCoordinator
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
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
**durch:**
```python
        """Not 'representative climate data': a climate derived from latitude alone.

        English and services.yaml say what the climate is; in every language the
        old claim is gone (its stem, matched across languages). NOT-TO-DO: do not
        pin the other seven languages word for word; key parity and the
        untranslated-string check in test_i18n_completeness keep them present
        and translated.
        """
        en = json.loads(
            (_ROOT / "translations" / "en.json").read_text(encoding="utf-8")
        )
        declared = yaml.safe_load((_ROOT / "services.yaml").read_text(encoding="utf-8"))

        for text in (
            en["services"]["generate_watering_calendar"]["description"],
            declared["generate_watering_calendar"]["description"],
        ):
            assert "illustrative" in text and "latitude" in text, text

        old_claim = re.compile(
            r"repr[aäeé]sentati|rappresentati|reprezentat", re.IGNORECASE
        )
        for catalogue in sorted((_ROOT / "translations").glob("*.json")):
            service = json.loads(catalogue.read_text(encoding="utf-8"))["services"]
            description = service["generate_watering_calendar"]["description"]
            assert not old_claim.search(description), (catalogue.name, description)
```

**Runde 2 (Nachprüfung `8cb8ce20`, „APPROVED WITH MINOR NOTES“):** Der Amend hat die frühere Negativ-Prüfung der YAML
verloren — eine YAML-Beschreibung mit altem Anspruch UND den neuen Wörtern („…representative climate data (an
illustrative climate derived from latitude only).“) bestand; die Stamm-Schleife liest nur `translations/*.json`. →
`old_claim` vor die erste Schleife, dort auch `not old_claim.search(text)` (deckt en.json und YAML). Mutant M37. Block 3
dieses Abschnitts; da Task 8 schon auf Task 7 aufbaut, als `git commit --fixup` + `git rebase --autosquash bbf2e151`.
Ergebnis: Task 7 `7c96ab50`, Task 8 `1a611375`, Tasks 1–6 unverändert. Nachprüfung: APPROVED.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        for text in (
            en["services"]["generate_watering_calendar"]["description"],
            declared["generate_watering_calendar"]["description"],
        ):
            assert "illustrative" in text and "latitude" in text, text

        old_claim = re.compile(
            r"repr[aäeé]sentati|rappresentati|reprezentat", re.IGNORECASE
        )
        for catalogue in sorted((_ROOT / "translations").glob("*.json")):
```
**durch:**
```python
        old_claim = re.compile(
            r"repr[aäeé]sentati|rappresentati|reprezentat", re.IGNORECASE
        )
        for text in (
            en["services"]["generate_watering_calendar"]["description"],
            declared["generate_watering_calendar"]["description"],
        ):
            assert "illustrative" in text and "latitude" in text, text
            assert not old_claim.search(text), text

        for catalogue in sorted((_ROOT / "translations").glob("*.json")):
```

### Task 8: Abweichungen

**Vorab aus dem Review von Task 7 (vor dem Bau von Task 8), geprüft am Plan:**
- R7-M2: Slowakisch einheitlich „ilustratívny“ (Dienstbeschreibung in Task 7: „ilustratívnej klímy“) → Karten-Hinweis
  „Ilustratívne hodnoty“ statt „Ilustračné hodnoty“.
- R7-Hinweis: Der Karten-Test pinnte nur „latitude“ im englischen Hinweis — dieselbe Schwäche wie R6-1/R7-M1 → auch
  „Illustrative“. Mutant M36.
- Aufzubringen nach `apply_plan_task.py 8 code` mit `apply_plan_task.py 8 deviations`, vor GREEN.

**Ersetze in `custom_components/irrigation_plus/frontend/localize/languages/sk.json`:**
```json
        "seasonal_note": "Ilustračné hodnoty odvodené iba zo zemepisnej šírky, nie namerané údaje o počasí."
```
**durch:**
```json
        "seasonal_note": "Ilustratívne hodnoty odvodené iba zo zemepisnej šírky, nie namerané údaje o počasí."
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        assert "panels.setup.weather_data.seasonal_note" in seasonal
        assert "latitude" in en["panels"]["setup"]["weather_data"]["seasonal_note"]
```
**durch:**
```python
        note = en["panels"]["setup"]["weather_data"]["seasonal_note"]
        assert "panels.setup.weather_data.seasonal_note" in seasonal
        assert "Illustrative" in note and "latitude" in note, note
```

**Runde 2 (Review `1a611375`, „APPROVED WITH MINOR NOTES“), geprüft am Code:**
- R8-1 übernommen: Der Test fand den Schlüssel nur als Teilstring irgendwo in `_renderSeasonal`. Es bestanden: der
  Hinweis über dem Ternär (stünde auch über „keine Daten“), nur im Leer-Zweig, und ein Tippfehler im View
  (`…seasonal_notes` enthält `…seasonal_note`; zur Laufzeit eine leere graue Box, die Katalog-Paritätstests sehen den
  View nicht). → Schlüssel zitiert und im Daten-Zweig (nach `calendar.no_data`, ab `: html\``); Docstring nennt, was
  geschützt wird. Mutanten M38 (Tippfehler), M39 (nur im Leer-Zweig). Blöcke 3–4 dieses Abschnitts, `--from 3`.
- R8-2 nicht umgesetzt, in die Sichtprüfung des Live-Tests gegeben: `.weather-note` hat keinen Außenabstand, die Box
  liegt direkt auf dem Tabellenkopf (Reviewer-Rendering `review-scratch\t8_note_gap.png`); Vorschlag
  `.weather-note + .seasonal-table { margin-top: 8px; }` — Optik, Entscheidung des Users nach Strg+F5 auf HA-Test.
  **Ergebnis 2026-10-05: User „Hinweis da, Abstand ok“ → keine Änderung.**

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        """A tripwire on the panel's source, kept here because CI runs pytest only."""
```
**durch:**
```python
        """The note stands above the table, not in the empty state.

        A tripwire on the panel's source, kept here because CI runs pytest only.
        """
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        seasonal = seasonal[: seasonal.index("private _renderForecast")]
        note = en["panels"]["setup"]["weather_data"]["seasonal_note"]
        assert "panels.setup.weather_data.seasonal_note" in seasonal
```
**durch:**
```python
        seasonal = seasonal[: seasonal.index("private _renderForecast")]
        no_data = seasonal.index("panels.zones.calendar.no_data")
        with_data = seasonal[seasonal.index(": html`", no_data) :]
        note = en["panels"]["setup"]["weather_data"]["seasonal_note"]
        assert '"panels.setup.weather_data.seasonal_note"' in with_data
```

**Runde 3 (Nachprüfung `88579e4e`, „APPROVED WITH MINOR NOTES“):** Der neue Docstring („above the table, not in the
empty state“) versprach mehr, als der Test erzwang — Hinweis UNTER der Tabelle oder in BEIDEN Zweigen bestand. Die Spec
fordert genau das („über der Tabelle, nur wenn Daten da sind“) → gepinnt statt Docstring abgeschwächt: Schlüssel genau
einmal in `_renderSeasonal`, im Daten-Zweig vor `seasonal-table`. Mutant M40 (beide Zweige). Block 5 dieses
Abschnitts; Task 9 liegt schon darauf → `git commit --fixup` + `git rebase --autosquash bbf2e151`.
Ergebnis: Task 8 `bbb50272`, Tasks 1–7 unverändert. Nachprüfung: APPROVED (10 falsche Varianten fallen, 3 legitime
Umformatierungen bestehen — nicht überpinnt).

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        with_data = seasonal[seasonal.index(": html`", no_data) :]
        note = en["panels"]["setup"]["weather_data"]["seasonal_note"]
        assert '"panels.setup.weather_data.seasonal_note"' in with_data
```
**durch:**
```python
        with_data = seasonal[seasonal.index(": html`", no_data) :]
        key = '"panels.setup.weather_data.seasonal_note"'
        note = en["panels"]["setup"]["weather_data"]["seasonal_note"]
        assert seasonal.count(key) == 1
        assert key in with_data
        assert with_data.index(key) < with_data.index("seasonal-table")
```

### Task 9: Abweichungen

**Befunde (Review `ca1bd89f`, „CHANGES REQUIRED“ wegen Punkt 1), geprüft am Code:**
- R9-1 übernommen (wichtig): „The monthly watering volume per zone is available through the
  `generate_watering_calendar` service“ führt in die Irre — der Dienst ist ohne `supports_response` registriert
  (`services.py:475`), liefert nichts zurück und feuert nur `irrigation_plus_watering_calendar_generated` mit
  `calendar_data` (`services.py:268`). Wer der Doku folgt und den Dienst in den Entwicklerwerkzeugen aufruft, sieht
  keine Zahlen. → Absatz und Dienst-Tabelle nennen das Event.
- R9-2 übernommen: „because it depends only on where you are“ — „it“ umfasst die ET-Spalte, die am Modul der ersten Zone
  hängt (Static ortsunabhängig) → „because the climate depends only on where you are“.
- R9-3 übernommen: zwei Nachbarstellen beschreiben den Ausblick noch als Wetter bzw. als Kalender:
  `configuration-weather-location.md:10` („what the weather looks like — … across the year“) und
  `configuration-my-zones.md:25` („the watering calendar“; Zeile 260 derselben Datei sagt schon „seasonal outlook“).
- R9-4 nicht hier: der Screenshot `docs/assets/images/configuration-weather-location-1.png` zeigt die alte Karte
  (ohne Hinweis, Regen in der ET-Spalte). Braucht die neue Oberfläche → Live-Test/PR-Text.
- Nicht umgesetzt (Folgeschritt, Vorbestand): das Event fehlt in `docs/usage-events.md`.
- Ergebnis `88d210a8` (nach Fixup-Rebase von Task 8 und Amend). Nachprüfung: APPROVED.

**Ersetze in `docs/configuration-weather-location.md`:**
```markdown
and what the weather looks like — now, the coming days, and across the year.
```
**durch:**
```markdown
and what the weather looks like now and in the coming days, plus a rough illustration of the year.
```

**Ersetze in `docs/configuration-weather-location.md`:**
```markdown
It replaces the old per-zone watering calendar and is shown once here, because it depends only on where you are. The monthly watering volume per zone is available through the `generate_watering_calendar` service.
```
**durch:**
```markdown
It replaces the old per-zone watering calendar and is shown once here, because the climate depends only on where you are. The monthly watering volume per zone is not shown here: the `generate_watering_calendar` service computes it and fires it as the `irrigation_plus_watering_calendar_generated` event.
```

**Ersetze in `docs/usage-services.md`:**
```markdown
based on an illustrative climate derived from latitude only (not measured weather).|
```
**durch:**
```markdown
based on an illustrative climate derived from latitude only (not measured weather). The result is fired as the `irrigation_plus_watering_calendar_generated` event.|
```

**Ersetze in `docs/configuration-my-zones.md`:**
```markdown
the forecast and the watering calendar are no longer per-zone — they live once on the [**Weather & Location**](configuration-weather-location.md) tab.) The sections below ("Adding a zone", "Configuring a zone") all live here.
```
**durch:**
```markdown
the forecast and the seasonal outlook are no longer per-zone — they live once on the [**Weather & Location**](configuration-weather-location.md) tab.) The sections below ("Adding a zone", "Configuring a zone") all live here.
```

## Abschluss-Review des ganzen Branches (Opus, `88d210a8`, „READY AFTER MINOR FIXES“)

Keine Verhaltensänderung nötig; nur Text. Jeder Fix gehört in den Task, der die Stelle geschrieben hat, und kommt als
`git commit --fixup=<sha>` bzw. `--fixup=reword:<sha>` + ein `git rebase --autosquash bbf2e151`.
- AR-1 übernommen (Task 1): „only where the calculation books it“ gilt je MODUL, nicht je Zone — eine PyETO-Zone, deren
  Sensorgruppe Niederschlag = keiner hat, bucht in der Rechnung 0 mm (`calculation.py:1209`), der Kalender zieht den
  Klima-Regen trotzdem ab. Die Regel selbst ist die freigegebene (A2/E3, `zone_module_models_weather`) → Wortlaut wie im
  Docstring der Mengenfunktion; die Grenze kommt als eine Zeile in den PR-Text.
- AR-2 übernommen (Tasks 1, 2): „projection“ heißt im Code sonst Live-Schätzung/Lauf-Projektion (`day_projection.py`,
  `live_estimate.py`) → „calendar“.
- AR-3 übernommen (Task 5): Testname `…mirrors_every_seasonal_curve` behauptet zu viel (tropischer Regen spiegelt bewusst
  nicht, R5-M1) → `…mirrors_every_temperate_curve`, Docstring auf 50° S bezogen.
- AR-4 übernommen (Tasks 4, 5): JustChr behält beim Squash die Commit-Bodies. Task 4: „February came out a day long“
  (liest sich als „einen Tag lang“, und die 31-Tage-Monate fehlen) → präzise. Task 5: zitierte „higher in winter“ auch
  für den Regen, dessen Kommentar „More in winter“ sagt → ohne Zitat.
- AR-5 zur Entscheidung des Users: neues Argument zur Frage „latitude only“ — ist die erste Zone Static, kommt die
  ET-Spalte der Karte gar nicht aus dem Breitengrad. Würde der Wortlaut ohnehin geändert, deckt „climate“ statt „values“
  beides (Höhe und Static) ab.

### Task 1: Abschluss-Review

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # subtracted once, in the volume, and only where the calculation books it.
```
**durch:**
```python
        # subtracted once, in the volume, and only for a module the calculation
        # books it for.
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
    """The projection prices a month the way the calculation prices its days.
```
**durch:**
```python
    """The calendar prices a month the way the calculation prices its days.
```

### Task 2: Abschluss-Review

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
            # calculation books no rain for them, so neither does the projection.
```
**durch:**
```python
            # calculation books no rain for them, so neither does the calendar.
```

### Task 4: Abschluss-Review

**Commit-Message:**
```text
fix(calendar): every branch scales a daily figure by the days of the month

The PyETO branch multiplies its daily ET by the month's days; the branch
for the other modules multiplied by 30, so February counted one day too
many and every 31-day month one too few.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Task 5: Abschluss-Review

**Ersetze in `tests/test_watering_calendar.py`:**
```python
    async def test_the_southern_hemisphere_mirrors_every_seasonal_curve(
        self, coordinator
    ):
        """South of the equator July is winter for every curve, not just the heat."""
```
**durch:**
```python
    async def test_the_southern_hemisphere_mirrors_every_temperate_curve(
        self, coordinator
    ):
        """At 50° S July is winter for every curve, not just the heat."""
```

**Commit-Message:**
```text
fix(calendar): each seasonal curve peaks where its comment says

Humidity, wind and temperate rain are commented as peaking in winter but
peaked in July, and the southern hemisphere mirrored only the
temperature. Every curve tied to a season now shares one sign, the
local summer; the tropical and subtropical rain names no season and
stays as it was. The constants of the synthetic climate are unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Task 7: Entscheidung des Users (2026-10-05, nach dem Abschluss-Review)

- R7-M3 entschieden: deutsche Dienstbeschreibung „…auf Basis eines allein aus dem Breitengrad abgeleiteten
  Beispielklimas erstellen“ (statt „veranschaulichenden Klimas allein aus dem Breitengrad“). Kartenhinweis und
  „latitude only“ bleiben wie freigegeben (User-Antwort: „So lassen“). Mutant M35 auf den neuen Text umgestellt.

**Ersetze in `custom_components/irrigation_plus/translations/de.json`:**
```json
      "description": "Einen 12-Monats-Bewässerungskalender für Bewässerungszonen auf Basis eines veranschaulichenden Klimas allein aus dem Breitengrad erstellen",
```
**durch:**
```json
      "description": "Einen 12-Monats-Bewässerungskalender für Bewässerungszonen auf Basis eines allein aus dem Breitengrad abgeleiteten Beispielklimas erstellen",
```
