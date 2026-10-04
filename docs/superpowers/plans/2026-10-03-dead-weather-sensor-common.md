# Stummer Wettersensor, PR 1 (Erkennung, Ausfall-Liste, Hinweis, Event) — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Integration Plus erkennt, wenn ein Wettersensor einer Sensorgruppe verstummt, schreibt jeden Ausfall
über 3 h an die Sensorgruppe und meldet ihn per Reparaturhinweis und Bus-Event, ohne eine Rechnung zu ändern.

**Architektur:** Neues Modul `sensor_liveness.py`: zuerst reine Funktionen (Lebenszeichen je HA-Gerät,
Ausfall-Liste fortschreiben, Hinweis- und Event-Inhalt), ohne Home Assistant testbar; dahinter
`SensorLivenessMixin` als Koordinator-Kleber (5-Minuten-Prüfung, Entity-Registry, Store, Reparaturhinweis,
Event). Die Liste und das letzte Lebenszeichen liegen als zwei neue Felder an `MappingEntry`, ohne
Store-Versionssprung. Keine Rechnung liest die Liste.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über
`pytest-homeassistant-custom-component`, `attrs`. Zeiten werden übergeben; nur JustChrs drei Hinweis-Tests nutzen das
`freezer`-Fixture (Tasks 9–11).

**Spec:** `docs/superpowers/specs/2026-10-03-dead-weather-sensor-design.md`, **Revision 2** (2026-10-04, angepasst an
JustChrs Antwort auf `JustChr#188`). Dieser Plan ist **PR 1** von dreien; PR 2 (Einstellung und Schnitt im Tagespfad)
und PR 3 (Stundenpfad und Live-Schätzung) bekommen eigene Pläne.

**Freigabe:** Spec Revision 2 und dieser Plan vom User freigegeben am 2026-10-04; Live-Test-Mittel Variante 1
(MQTT-YAML unter eigenem Topic-Präfix, Task 15).

**Revision 2 (2026-10-04)** gegenüber dem am 2026-10-03 freigegebenen Plan (Archiv `archive/design-history`
`1c197e36`):
- PR 1 wird allein ausgeliefert; die Liefer-Regel „Teil 1 nie allein“ entfällt. Deshalb verspricht kein Text mehr einen
  Schnitt: Konstanten-Kommentar (Task 1), Modul-Docstring (Task 2), Log-Warnung (Task 9), Hinweistext (Task 12).
- JustChrs drei Hinweis-Tests in `tests/test_sensor_liveness_repair.py`, gegen echten Store und echte Issue-Registry
  (Tasks 9, 10, 11).
- Doku-Abschnitt „When a sensor goes silent“ mit dem 6-h-Satz (Task 13).
- Neue Testdateien black-formatiert (Snippets in Tasks 1, 5, 9 und 11 angepasst).
- Mutationen 17–20 (Task 14); neu: Pre-Release und Live-Test auf HA-Test (Task 15), PR und Nachlauf (Task 16).

**Probelauf (2026-10-04, gegen `e9c79ec4`):** der getestete Stand vom 2026-10-03
(`D:\Entwicklung\HASI\issue8-work\probe-2026-10-03.patch`), darauf die Revision-2-Änderungen per Skript
(`probe_rev2.py`; jeder Anker passte genau einmal) und die neue Testdatei; geprüft in einem Wegwerf-Worktree:
- **75 neue Tests grün** (40 rein, 6 Store, 26 Koordinator, 3 Hinweis-Tests gegen die echte Registry); black und ruff
  sauber auf `custom_components/irrigation_plus/`, die vier Testdateien black-sauber; `test_i18n_completeness` 67 grün.
- **Volle Suite:** 7 failed / 3693 passed / 9 skipped / 415 errors gegen die frisch gemessene Baseline 7 / 3618 / 9 / 415
  (identisch mit der Baseline von `issue9-work` auf demselben Commit). Die 422 FAILED/ERROR-Namen sind per `diff`
  identisch, und 3618 + 75 = 3693.
- **20/20 Mutationen getötet** (`probe_mutate2.py`, jede gegen alle vier Testdateien, Ergebnis `mutate-1004.txt`); die
  Killer stehen in Task 14.
- Der Probelauf vom 2026-10-03 (72 Tests, 16/16 Mutationen, zwei eingearbeitete Befunde) bleibt im Archiv beschrieben.
- Der getestete Endstand liegt als Patch vor: `D:\Entwicklung\HASI\issue8-work\probe-2026-10-04.patch` (19 Dateien,
  +1769/−5). **Weicht ein Snippet dieses Plans vom Patch ab, gilt der Patch** (er ist der getestete Stand); die
  Abweichung dann im Plan berichtigen.

---

## Rahmen

- **Dieser Plan ist PR 1 von dreien** (Spec Revision 2): Erkennung, Ausfall-Liste, Reparaturhinweis, Event, Doku —
  **ohne Verhaltensänderung**. Keine Rechnung liest die Ausfall-Liste, und kein Text verspricht einen Schnitt; der
  Hinweis sagt, dass die zuletzt gemeldeten Werte weiter verwendet werden.
- **Nicht in diesem Plan:** die Einstellung „pausieren / letzten Wert behalten“ und der Schnitt im Tagespfad samt Satz
  in der Berechnungs-Erklärung (PR 2), der Schnitt im Stundenpfad und in der Live-Schätzung (PR 3). Beide bekommen
  eigene Pläne; PR 2 wird erst nach dem Feldtest dieses PRs gepostet (JustChrs Bedingung).
- **Liefer-Reihenfolge:** Tasks 0–14 im Worktree → Task 15 production-Pre-Release und Live-Test auf HA-Test → Task 16
  PR an JustChr und Nachlauf. Alles, was nach außen geht (Push, Release, PR, Kommentare, Issue-Änderungen), nur nach
  Freigabe im Chat; Texte vorher zeigen, deutsch, dann englisch.
- **Basis:** Alle Zeilenangaben beziehen sich auf `upstream/master` = `e9c79ec4`. Hat sich `master` beim Bau
  bewegt, vor Task 1 jede Anker-Stelle per `grep -n` neu suchen (die Anker sind zitiert).
- **Keine Verweise auf unsere Issues** in Code, Kommentaren, Commit-Messages (Memory
  `no-own-issue-refs-upstream`). JustChrs `#188` darf im Code-Kommentar stehen.
- **Testbefehl** (aus dem Worktree; es gibt dort kein eigenes `.venv`):
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **Uhr:** Jeder Stempel liegt im Rahmen des Puffers: HAs Uhr, naiv (`local_naive_now`). Zustands-Stempel
  (`last_reported`, `last_changed`) sind aware UTC und werden mit `dt_util.as_local(...).replace(tzinfo=None)`
  umgerechnet. In den Tests ist HAs Zone US/Pacific (autouse `hass`-Fixture), die Prozesszone per `TZ=UTC`
  UTC: Ein vergessenes `as_local` fällt dadurch auf (Task 8). JustChrs drei Hinweis-Tests laufen mit dem
  `freezer`-Fixture: `local_naive_now()` liest `dt_util.now()` und folgt ihm, ebenso die Zustands-Stempel.

## Dateien

| Datei | Verantwortung |
|---|---|
| neu: `custom_components/irrigation_plus/sensor_liveness.py` | Regeln (rein) + `SensorLivenessMixin` (Kleber) |
| `custom_components/irrigation_plus/const.py` | Grenzen, Schlüssel, Event- und Hinweis-Namen |
| `custom_components/irrigation_plus/store.py` | `MappingEntry.sensor_outages`, `.sensor_last_seen`, Laden, Setter ohne Speichern |
| `custom_components/irrigation_plus/__init__.py` | Mixin in die Basen, Setup/Unload, Quellwechsel und Löschen |
| `custom_components/irrigation_plus/calculation.py` | „Wetterdaten zurücksetzen“ leert die Liste; Docstring von `_prune_mapping_buffer` |
| `custom_components/irrigation_plus/translations/*.json` (8) | Reparaturhinweis `weather_sensor_stale` |
| `docs/configuration-sensor-groups.md` | Abschnitt „When a sensor goes silent“ (mit dem 6-h-Satz) |
| `docs/usage-events.md` | Event `irrigation_plus_weather_stale` |
| neu: `tests/test_sensor_liveness.py` | reine Regeln, Übersetzungen |
| neu: `tests/test_sensor_liveness_store.py` | echter Store (Laden, Speichern, Teilen) |
| neu: `tests/test_sensor_liveness_coordinator.py` | Kleber mit Mock-`hass`, echte Registry, Verdrahtung |
| neu: `tests/test_sensor_liveness_repair.py` | JustChrs drei Hinweis-Tests: echter Store, echte Issue-Registry, eingefrorene Uhr |

---

### Task 0: Arbeitsumgebung und Baseline

**Files:** keine Codeänderung.

- [ ] **Step 1: Worktree von `upstream/master` anlegen** (ohne Tracking auf upstream, Memory `hasi-pr-build-recipe`)

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git worktree add --no-track -b fix/stale-weather-sensor /d/Entwicklung/HASI/issue8-work/wt upstream/master
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue8-work/wt/
cd /d/Entwicklung/HASI/issue8-work/wt && git log --oneline -1
```

Erwartet: eine Zeile mit dem aktuellen `master`-Stand. Ist es nicht `e9c79ec4`, die Anker dieses Plans neu suchen
(z. B. `grep -n "radiation_calibration = attr.ib" custom_components/irrigation_plus/store.py`).

- [ ] **Step 2: Baseline der vollen Suite auf diesem Commit messen** (Memory `rebaseline-when-the-base-moves`)

```bash
cd /d/Entwicklung/HASI/issue8-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-baseline.txt 2>&1
tr '\r' '\n' < ../suite-baseline.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-baseline.txt
tail -c 400 ../suite-baseline.txt
```

Erwartet: Zusammenfassung wie `7 failed, 3618 passed, 9 skipped, … 415 errors` (die Windows-Altlasten). Die Datei
erst nach Laufende lesen.

---

### Task 1: Konstanten

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (nach `RADIATION_CALIBRATION_RATIO_BOUNDS = (0.5, 2.0)`, `const.py:690`, vor `MAPPING_MAPPINGS`; und nach `EVENT_ZONE_PROBLEM`, `const.py:1080`)
- Test: `tests/test_sensor_liveness.py` (neu)

- [ ] **Step 1: Failing test schreiben**

```python
"""Weather-sensor liveness: the pure rules, without Home Assistant."""

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import BUFFER_RETENTION


def test_closed_outages_are_kept_as_long_as_the_buffer_keeps_rows():
    """A window cannot reach back further than the reading buffer keeps rows, so an
    outage that ended before that can no longer touch any calculation."""
    assert (
        const.SENSOR_OUTAGE_RETENTION_DAYS * 86400 == BUFFER_RETENTION.total_seconds()
    )
```

- [ ] **Step 2: Test laufen lassen, RED prüfen**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness.py -p _local_socket_unblock -q`
Expected: FAIL mit `AttributeError: module 'custom_components.irrigation_plus.const' has no attribute 'SENSOR_OUTAGE_RETENTION_DAYS'`

- [ ] **Step 3: Konstanten einfügen** (nach `RADIATION_CALIBRATION_RATIO_BOUNDS = (0.5, 2.0)`)

```python
# --- Weather-sensor liveness (#188) -------------------------------------------
# A sensor field whose HA device has not reported for this long counts as
# silent: its outage is recorded on the sensor group and the user is told. Long
# enough for an HA restart and a quiet night on an integration that writes only
# on change. Fixed: an integration that updates less often than this raises the
# notice between its updates, which docs/configuration-sensor-groups.md says.
SENSOR_STALE_AFTER_SECONDS = 3 * 3600
# How often the check runs, and how long it waits after setup so that
# integrations have created their entities first.
SENSOR_LIVENESS_INTERVAL_SECONDS = 300
SENSOR_LIVENESS_STARTUP_GRACE_SECONDS = 600
# Closed outages are kept as long as the reading buffer keeps rows
# (calculation.BUFFER_RETENTION): no window reaches back further.
SENSOR_OUTAGE_RETENTION_DAYS = 7
# Values set by hand: no sign of life is expected, so they never go stale.
SENSOR_LIVENESS_EXEMPT_DOMAINS = ("input_number",)
# Stored on the sensor group (MappingEntry).
MAPPING_SENSOR_OUTAGES = "sensor_outages"
MAPPING_SENSOR_LAST_SEEN = "sensor_last_seen"
# One repair issue per sensor group: f"{ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}".
ISSUE_WEATHER_SENSOR_STALE = "weather_sensor_stale"
```

und direkt nach `EVENT_ZONE_PROBLEM = "zone_problem"`:

```python
# Fired when a weather sensor's outage starts and when it ends.
EVENT_WEATHER_STALE = "weather_stale"
```

- [ ] **Step 4: Test laufen lassen, GREEN prüfen**

Run: wie Step 2. Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/const.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): constants for weather-sensor outages

The limit after which a silent sensor is reported (3 h, fixed; an integration
that updates less often raises the notice between its updates), the check
cadence, the startup grace, the retention of closed outages (the reading
buffer's 7 days, pinned by a test), the exempt helper domain, the sensor-group
keys, the repair issue key and the bus event name.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Welche Entitäten eine Sensorgruppe beobachtet

**Files:**
- Create: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing tests anhängen** (Import oben ergänzen)

```python
from custom_components.irrigation_plus.sensor_liveness import sensor_fields_by_entity


def _cfg(source, entity=None):
    cfg = {const.MAPPING_CONF_SOURCE: source}
    if entity is not None:
        cfg[const.MAPPING_CONF_SENSOR] = entity
    return cfg


def test_only_sensor_fields_with_an_entity_are_watched():
    mappings = {
        const.MAPPING_TEMPERATURE: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, "sensor.t"),
        const.MAPPING_DEWPOINT: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, "sensor.t"),
        const.MAPPING_HUMIDITY: _cfg(const.MAPPING_CONF_SOURCE_WEATHER_SERVICE),
        const.MAPPING_PRESSURE: _cfg(const.MAPPING_CONF_SOURCE_STATIC_VALUE),
        const.MAPPING_WINDSPEED: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, ""),
        const.MAPPING_SOLRAD: "legacy bare string",
    }
    assert sensor_fields_by_entity(mappings) == {
        "sensor.t": (const.MAPPING_TEMPERATURE, const.MAPPING_DEWPOINT),
    }


def test_a_value_set_by_hand_is_never_watched():
    mappings = {
        const.MAPPING_PRESSURE: _cfg(
            const.MAPPING_CONF_SOURCE_SENSOR, "input_number.pressure"
        )
    }
    assert sensor_fields_by_entity(mappings) == {}
```

- [ ] **Step 2: RED prüfen**

Run: `TZ=UTC … -m pytest tests/test_sensor_liveness.py -p _local_socket_unblock -q`
Expected: FAIL (Sammelfehler) mit `ModuleNotFoundError: No module named 'custom_components.irrigation_plus.sensor_liveness'`

- [ ] **Step 3: Modul anlegen**

```python
"""When a weather sensor stops reporting: liveness, the outage ledger, the notice.

A sensor group carries a field's last value forward while nothing new arrives (the
per-field boundary row, ``last_entry``). That is right for a value that is merely
steady and wrong for a sensor that died. This module tells the two apart by the
sensor's HA *device* -- at a living station some value reports or changes within
``SENSOR_STALE_AFTER_SECONDS``, a quiet rain gauge included -- records every outage
longer than that on the sensor group, and tells the user: a repair issue per group
while an outage is open, and a bus event when one starts and when it ends (#188).

Nothing here changes a calculation: a silent sensor's last value is still used, as
before. The ledger records when it fell silent and the notice tells the user.

The rules are pure functions, testable without Home Assistant; the
``SensorLivenessMixin`` at the end is the coordinator glue.
"""

from __future__ import annotations

import logging

from . import const

_LOGGER = logging.getLogger(__name__)


def sensor_fields_by_entity(mappings_config: dict) -> dict[str, tuple[str, ...]]:
    """``{entity_id: fields}`` for every field this sensor group reads from an entity.

    Weather-service and static fields have no device to fall silent; a legacy bare
    string is not a field config. ``input_number`` is a value set by hand, which
    never reports on its own, so it is exempt.
    """
    found: dict[str, list[str]] = {}
    for field_name, cfg in mappings_config.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get(const.MAPPING_CONF_SOURCE) != const.MAPPING_CONF_SOURCE_SENSOR:
            continue
        entity_id = cfg.get(const.MAPPING_CONF_SENSOR)
        if not entity_id:
            continue
        if entity_id.split(".", 1)[0] in const.SENSOR_LIVENESS_EXEMPT_DOMAINS:
            continue
        found.setdefault(entity_id, []).append(field_name)
    return {entity_id: tuple(fields) for entity_id, fields in found.items()}
```

- [ ] **Step 4: GREEN prüfen** — Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): name the entities a sensor group depends on

Only fields read from a sensor entity can fall silent; weather-service and static
fields cannot, and an input_number is a value set by hand that never reports on
its own.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Das letzte Lebenszeichen und die Rückkehr

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing tests anhängen** (Importe oben ergänzen: `from datetime import datetime, timedelta`,
`Seen, first_report_after, last_sign_of_life` aus `sensor_liveness`)

```python
T0 = datetime(2026, 7, 1, 12, 0, 0)


def _seen(entity_id="sensor.t", *, valid=True, reported=T0, changed=T0):
    return Seen(entity_id=entity_id, valid=valid, reported=reported, changed=changed)


class TestLastSignOfLife:
    def test_the_device_vouches_for_a_quiet_field(self):
        rain = _seen("sensor.rain", reported=T0 - timedelta(hours=5))
        temp = _seen("sensor.temp", reported=T0 - timedelta(minutes=1))
        assert last_sign_of_life(rain, [temp], None) == T0 - timedelta(minutes=1)

    def test_without_a_device_the_entity_vouches_for_itself(self):
        own = _seen(reported=T0 - timedelta(hours=2))
        assert last_sign_of_life(own, [], None) == T0 - timedelta(hours=2)

    def test_an_unavailable_entity_is_silent_whatever_its_device_does(self):
        own = _seen(valid=False, reported=T0)
        sibling = _seen("sensor.temp", reported=T0)
        remembered = T0 - timedelta(hours=4)
        assert last_sign_of_life(own, [sibling], remembered) == remembered

    def test_an_unavailable_sibling_does_not_vouch(self):
        own = _seen(reported=T0 - timedelta(hours=5))
        sibling = _seen("sensor.temp", valid=False, reported=T0)
        assert last_sign_of_life(own, [sibling], None) == T0 - timedelta(hours=5)

    def test_a_missing_entity_with_nothing_remembered_has_no_sign(self):
        assert last_sign_of_life(None, [], None) is None

    def test_the_remembered_sign_never_moves_backwards(self):
        own = _seen(reported=T0 - timedelta(hours=1))
        assert last_sign_of_life(own, [], T0) == T0


class TestFirstReportAfter:
    def test_the_earliest_change_after_the_start_marks_the_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=T0 - timedelta(minutes=3))
        sibling = _seen("sensor.temp", changed=T0 - timedelta(minutes=4))
        quiet = _seen("sensor.rain", changed=start - timedelta(hours=1))
        assert first_report_after(own, [sibling, quiet], start) == T0 - timedelta(
            minutes=4
        )

    def test_nothing_changed_since_the_start(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=start - timedelta(minutes=1))
        assert first_report_after(own, [], start) is None

    def test_an_unavailable_state_is_not_a_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(valid=False, changed=T0)
        assert first_report_after(own, [], start) is None
```

- [ ] **Step 2: RED prüfen** — Expected: Sammelfehler `ImportError: cannot import name 'Seen'`

- [ ] **Step 3: Implementieren** (in `sensor_liveness.py`; Importe oben ergänzen:
`from dataclasses import dataclass` und `from datetime import datetime`)

```python
@dataclass(frozen=True)
class Seen:
    """One entity's state as liveness reads it, stamps naive on HA's clock."""

    entity_id: str
    valid: bool  # not unavailable/unknown
    reported: datetime  # State.last_reported
    changed: datetime  # State.last_changed


def last_sign_of_life(
    own: Seen | None, siblings: list[Seen], remembered: datetime | None
) -> datetime | None:
    """The newest report that vouches for a field, or None when there is none.

    ``own`` is the field's entity (None when it does not exist). While it is
    unavailable/unknown the field is silent whatever its device does, so only the
    remembered sign counts. Otherwise its device vouches for it: at a living station
    some value reports or changes within the limit, while a quiet rain gauge on the
    same device may not change for days. ``remembered`` is the sign stored at the
    previous check, so an outage that spans a restart keeps its start; a sign never
    moves backwards.
    """
    candidates = [remembered] if remembered is not None else []
    if own is not None and own.valid:
        candidates.append(own.reported)
        candidates.extend(s.reported for s in siblings if s.valid)
    return max(candidates) if candidates else None


def first_report_after(
    own: Seen | None, siblings: list[Seen], start: datetime
) -> datetime | None:
    """When the device spoke again after ``start``: its earliest change since then.

    A returning device's first report changes most of its values, so the earliest
    ``last_changed`` after the outage began is the closest record of its return that
    survives until the next check. None when nothing changed since ``start``.
    """
    states = ([own] if own is not None else []) + list(siblings)
    stamps = [s.changed for s in states if s.valid and s.changed > start]
    return min(stamps) if stamps else None
```

- [ ] **Step 4: GREEN prüfen** — Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): a field's last sign of life comes from its device

Integrations differ in whether they write unchanged values, so a field's own
report age cannot tell a steady value from a dead sensor. Its HA device can: at a
living station some value reports or changes within the limit. An unavailable or
unknown entity is silent whatever its device does. The earliest change after an
outage began marks the device's return.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Ein Ausfall als Store-Datensatz

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing tests anhängen** (Importe: `import pytest`, `Outage`)

```python
class TestOutageInTheStore:
    def test_round_trip(self):
        outage = Outage(
            "sensor.t", "dev1", ("Temperature",), T0 - timedelta(hours=4), T0
        )
        assert outage.to_store() == {
            "entity_id": "sensor.t",
            "device_id": "dev1",
            "fields": ["Temperature"],
            "start": "2026-07-01T08:00:00",
            "end": "2026-07-01T12:00:00",
        }
        assert Outage.from_store(outage.to_store()) == outage

    def test_an_open_outage_has_no_end(self):
        outage = Outage("sensor.t", None, ("Temperature",), T0)
        assert outage.to_store()["end"] is None
        assert Outage.from_store(outage.to_store()) == outage

    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "text",
            {},
            {"entity_id": "sensor.t"},
            {"entity_id": "sensor.t", "start": "garbage"},
            {"start": "2026-07-01T08:00:00"},
        ],
    )
    def test_an_unreadable_record_is_dropped_not_raised(self, raw):
        assert Outage.from_store(raw) is None
```

- [ ] **Step 2: RED prüfen** — Expected: `ImportError: cannot import name 'Outage'`

- [ ] **Step 3: Implementieren** (Import oben ergänzen: `from .helpers import STAMP_FROM_STORE, coerce_stamp`)

```python
@dataclass(frozen=True)
class Outage:
    """A sensor entity that stayed silent for longer than the limit.

    ``start`` is its last sign of life, ``end`` its first report afterwards (None
    while it is still silent). Stored as ISO strings on HA's clock, the frame of the
    reading buffer whose rows the outage is compared with.
    """

    entity_id: str
    device_id: str | None
    fields: tuple[str, ...]
    start: datetime
    end: datetime | None = None

    def to_store(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "device_id": self.device_id,
            "fields": list(self.fields),
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end is not None else None,
        }

    @classmethod
    def from_store(cls, raw) -> Outage | None:
        """Read one stored record; anything unreadable is dropped, never raised."""
        if not isinstance(raw, dict) or not raw.get("entity_id"):
            return None
        start = coerce_stamp(raw.get("start"), STAMP_FROM_STORE)
        if start is None:
            return None
        return cls(
            entity_id=str(raw["entity_id"]),
            device_id=raw.get("device_id"),
            fields=tuple(raw.get("fields") or ()),
            start=start,
            end=coerce_stamp(raw.get("end"), STAMP_FROM_STORE),
        )


def outages_of(mapping: dict) -> list[Outage]:
    """The readable outages stored on a sensor group."""
    return [
        outage
        for raw in (mapping.get(const.MAPPING_SENSOR_OUTAGES) or [])
        if (outage := Outage.from_store(raw)) is not None
    ]
```

- [ ] **Step 4: GREEN prüfen** — Expected: `20 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): an outage record and its stored form

ISO strings on HA's clock, the frame of the reading buffer the outage will be
compared with. An unreadable record is dropped rather than raised, so a damaged
store entry cannot stop the periodic check.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Die Ausfall-Liste fortschreiben

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing tests anhängen** (Importe: `Evidence, advance_outages`)

```python
STALE = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS)


def _evidence(last, *, fields=("Temperature",), device="dev1", recovered=None):
    return Evidence(fields=fields, device_id=device, last=last, recovered=recovered)


class TestAdvanceOutages:
    def test_silence_up_to_the_limit_is_bridged(self):
        assert advance_outages([], {"sensor.t": _evidence(T0 - STALE)}, T0) == (
            [],
            [],
            [],
        )

    def test_silence_past_the_limit_opens_an_outage_at_the_last_sign(self):
        last = T0 - STALE - timedelta(seconds=1)
        expected = Outage("sensor.t", "dev1", ("Temperature",), last)
        assert advance_outages([], {"sensor.t": _evidence(last)}, T0) == (
            [expected],
            [expected],
            [],
        )

    def test_an_open_outage_is_not_opened_twice(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        assert advance_outages([open_], {"sensor.t": _evidence(start)}, T0) == (
            [open_],
            [],
            [],
        )

    def test_a_new_sign_closes_it_at_the_first_report(self):
        start = T0 - timedelta(hours=5)
        back = T0 - timedelta(minutes=4)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        ended = Outage("sensor.t", "dev1", ("Temperature",), start, back)
        assert advance_outages(
            [open_], {"sensor.t": _evidence(T0, recovered=back)}, T0
        ) == ([ended], [], [ended])

    def test_without_a_recorded_change_the_newest_report_ends_it(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        _, _, closed = advance_outages(
            [open_], {"sensor.t": _evidence(T0 - timedelta(minutes=1))}, T0
        )
        assert closed[0].end == T0 - timedelta(minutes=1)

    def test_an_outage_of_an_entity_no_longer_watched_ends_now(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.gone", "dev1", ("Temperature",), start)
        ended = Outage("sensor.gone", "dev1", ("Temperature",), start, T0)
        assert advance_outages([open_], {}, T0) == ([ended], [], [ended])

    def test_no_evidence_opens_nothing(self):
        assert advance_outages([], {"sensor.t": _evidence(None)}, T0) == ([], [], [])

    def test_closed_outages_older_than_the_retention_are_dropped(self):
        edge = T0 - timedelta(days=const.SENSOR_OUTAGE_RETENTION_DAYS)
        old = Outage(
            "sensor.a",
            None,
            ("Temperature",),
            edge - timedelta(hours=5),
            edge - timedelta(seconds=1),
        )
        kept = Outage(
            "sensor.b", None, ("Temperature",), edge - timedelta(hours=5), edge
        )
        still_open = Outage("sensor.c", None, ("Temperature",), T0 - timedelta(days=30))
        evidence = {"sensor.c": _evidence(T0 - timedelta(days=30), device=None)}
        outages, _, _ = advance_outages([old, kept, still_open], evidence, T0)
        assert outages == [kept, still_open]
```

- [ ] **Step 2: RED prüfen** — Expected: `ImportError: cannot import name 'Evidence'`

- [ ] **Step 3: Implementieren** (Importe ergänzen: `from dataclasses import dataclass, replace`,
`from datetime import datetime, timedelta`)

```python
STALE_AFTER = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS)
RETENTION = timedelta(days=const.SENSOR_OUTAGE_RETENTION_DAYS)


@dataclass(frozen=True)
class Evidence:
    """What one check learned about one sensor-mapped entity."""

    fields: tuple[str, ...]
    device_id: str | None
    last: datetime | None  # its last sign of life; None: no evidence at all
    recovered: datetime | None = None  # first report after an open outage began


def advance_outages(
    outages: list[Outage],
    evidence: dict[str, Evidence],
    now: datetime,
    *,
    stale_after: timedelta = STALE_AFTER,
    retention: timedelta = RETENTION,
) -> tuple[list[Outage], list[Outage], list[Outage]]:
    """One check over one sensor group's ledger: ``(outages, opened, closed)``.

    Opens an outage for an entity whose last sign is older than ``stale_after``
    (strictly: a silence of exactly the limit is still bridged), starting AT that
    sign. Closes an open one once a sign newer than its start appears, at the
    device's first report after the start when that is known, and ends one whose
    entity the group no longer reads (its sensor was replaced or unmapped by a
    path that did not empty the ledger) at ``now``, so neither it nor its notice
    outlives the configuration. Drops closed outages that ended more than
    ``retention`` ago; open ones stay whatever their age.
    """
    kept: list[Outage] = []
    opened: list[Outage] = []
    closed: list[Outage] = []
    still_open: set[str] = set()
    for outage in outages:
        if outage.end is not None:
            if now - outage.end <= retention:
                kept.append(outage)
            continue
        seen = evidence.get(outage.entity_id)
        if seen is None:
            ended = replace(outage, end=now)
            kept.append(ended)
            closed.append(ended)
            continue
        if seen.last is not None and seen.last > outage.start:
            back = seen.recovered
            end = back if back is not None and back > outage.start else seen.last
            ended = replace(outage, end=end)
            kept.append(ended)
            closed.append(ended)
            continue
        kept.append(outage)
        still_open.add(outage.entity_id)
    for entity_id, seen in evidence.items():
        if entity_id in still_open or seen.last is None:
            continue
        if now - seen.last > stale_after:
            outage = Outage(entity_id, seen.device_id, seen.fields, seen.last)
            kept.append(outage)
            opened.append(outage)
    return kept, opened, closed
```

- [ ] **Step 4: GREEN prüfen** — Expected: `28 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): open, close and prune a sensor group's outages

An outage opens once a sensor's last sign of life is older than the limit and
starts at that sign; it closes at the device's first report afterwards. Closed
outages are kept as long as the reading buffer keeps rows; open ones stay.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Inhalt von Hinweis und Event

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing tests anhängen** (Importe: `outage_event_payload, stale_issue_placeholders`)

```python
class TestStaleIssuePlaceholders:
    def test_no_open_outage_means_no_notice(self):
        closed = Outage("sensor.t", None, ("Temperature",), T0 - timedelta(hours=5), T0)
        assert stale_issue_placeholders("Garden", [closed]) is None

    def test_the_notice_names_every_silent_entity_and_the_earliest_start(self):
        temp = Outage(
            "sensor.temp", "dev1", ("Temperature", "Dewpoint"), T0 - timedelta(hours=4)
        )
        wind = Outage("sensor.wind", "dev1", ("Windspeed",), T0 - timedelta(hours=6))
        assert stale_issue_placeholders("Garden", [temp, wind]) == {
            "group": "Garden",
            "entities": "sensor.wind (Windspeed), sensor.temp (Temperature, Dewpoint)",
            "since": "2026-07-01 06:00",
        }


class TestOutageEventPayload:
    def test_an_outage_starting(self):
        outage = Outage("sensor.t", "dev1", ("Temperature",), T0 - timedelta(hours=4))
        assert outage_event_payload(3, "Garden", outage) == {
            "mapping_id": 3,
            "mapping": "Garden",
            "entity_id": "sensor.t",
            "device_id": "dev1",
            "fields": ["Temperature"],
            "since": "2026-07-01T08:00:00",
            "until": None,
            "stale": True,
        }

    def test_an_outage_ending(self):
        outage = Outage("sensor.t", None, ("Temperature",), T0 - timedelta(hours=4), T0)
        payload = outage_event_payload(3, "Garden", outage)
        assert payload["stale"] is False
        assert payload["until"] == "2026-07-01T12:00:00"
        assert payload["device_id"] is None
```

- [ ] **Step 2: RED prüfen** — Expected: `ImportError: cannot import name 'outage_event_payload'`

- [ ] **Step 3: Implementieren**

```python
def stale_issue_placeholders(group_name: str, outages: list[Outage]) -> dict | None:
    """The repair issue's placeholders for a group's OPEN outages, or None."""
    silent = sorted(
        (o for o in outages if o.end is None), key=lambda o: (o.start, o.entity_id)
    )
    if not silent:
        return None
    return {
        "group": group_name,
        "entities": ", ".join(f"{o.entity_id} ({', '.join(o.fields)})" for o in silent),
        "since": silent[0].start.strftime("%Y-%m-%d %H:%M"),
    }


def outage_event_payload(mapping_id, group_name: str, outage: Outage) -> dict:
    """The bus event's data for an outage starting (no end yet) or ending."""
    return {
        "mapping_id": mapping_id,
        "mapping": group_name,
        "entity_id": outage.entity_id,
        "device_id": outage.device_id,
        "fields": list(outage.fields),
        "since": outage.start.isoformat(),
        "until": outage.end.isoformat() if outage.end is not None else None,
        "stale": outage.end is None,
    }
```

- [ ] **Step 4: GREEN prüfen** — Expected: `32 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): what the notice and the event say

The notice names the group, every silent entity with its fields, and the earliest
start; the event carries one outage, with "stale" true when it starts and false,
with an end, when the sensor reports again.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Zwei Felder an der Sensorgruppe

**Files:**
- Modify: `custom_components/irrigation_plus/store.py` — Import-Block (`store.py:130-142`, alphabetisch zu `MAPPING_RADIATION_CALIBRATION`), `MappingEntry` (nach `radiation_calibration`, `store.py:372`), Laden (`store.py:1361-1378`), neuer Setter nach `set_mapping_last_entry_value` (`store.py:2101-2133`)
- Test: `tests/test_sensor_liveness_store.py` (neu)

- [ ] **Step 1: Failing tests schreiben**

```python
"""The sensor group's outage ledger and signs of life in the real store."""

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.store import STORAGE_KEY, SmartIrrigationStorage

OUTAGE = {
    "entity_id": "sensor.t",
    "device_id": "dev1",
    "fields": ["Temperature"],
    "start": "2026-07-01T08:00:00",
    "end": None,
}


async def _store_with_two_groups(hass):
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    a = await store.async_create_mapping(
        {const.MAPPING_NAME: "A", const.MAPPING_MAPPINGS: {}}
    )
    b = await store.async_create_mapping(
        {const.MAPPING_NAME: "B", const.MAPPING_MAPPINGS: {}}
    )
    return store, a[const.MAPPING_ID], b[const.MAPPING_ID]


@pytest.mark.asyncio
async def test_a_new_group_has_no_outages_and_no_signs(hass) -> None:
    store, a, _ = await _store_with_two_groups(hass)
    assert store.get_mapping(a)[const.MAPPING_SENSOR_OUTAGES] == []
    assert store.get_mapping(a)[const.MAPPING_SENSOR_LAST_SEEN] == {}


@pytest.mark.asyncio
async def test_signs_of_life_are_not_shared_between_groups(hass) -> None:
    store, a, b = await _store_with_two_groups(hass)
    store.set_mapping_sensor_last_seen(a, {"sensor.t": "2026-07-01T12:00:00"})
    assert store.get_mapping(b)[const.MAPPING_SENSOR_LAST_SEEN] == {}


@pytest.mark.asyncio
async def test_refreshing_the_signs_schedules_no_write(hass) -> None:
    """Refreshed at every check; a write each time would cost a whole document every
    few minutes for a value that only matters across a restart. It rides along."""
    store, a, _ = await _store_with_two_groups(hass)
    writes = []
    store._store.async_delay_save = lambda func, delay=0: writes.append(func)

    store.set_mapping_sensor_last_seen(a, {"sensor.t": "2026-07-01T12:00:00"})

    assert writes == []
    routine = store._data_to_save()["mappings"]
    assert routine[0][const.MAPPING_SENSOR_LAST_SEEN] == {
        "sensor.t": "2026-07-01T12:00:00"
    }


@pytest.mark.asyncio
async def test_outages_and_signs_survive_a_restart(hass, hass_storage) -> None:
    store, a, _ = await _store_with_two_groups(hass)
    await store.async_update_mapping(a, {const.MAPPING_SENSOR_OUTAGES: [OUTAGE]})
    store.set_mapping_sensor_last_seen(a, {"sensor.t": "2026-07-01T08:00:00"})
    await store.async_save()

    reloaded = SmartIrrigationStorage(hass)
    await reloaded.async_load()

    assert reloaded.get_mapping(a)[const.MAPPING_SENSOR_OUTAGES] == [OUTAGE]
    assert reloaded.get_mapping(a)[const.MAPPING_SENSOR_LAST_SEEN] == {
        "sensor.t": "2026-07-01T08:00:00"
    }


@pytest.mark.asyncio
async def test_a_document_written_before_these_fields_still_loads(
    hass, hass_storage
) -> None:
    store, a, _ = await _store_with_two_groups(hass)
    await store.async_save()
    for mapping in hass_storage[STORAGE_KEY]["data"]["mappings"]:
        mapping.pop(const.MAPPING_SENSOR_OUTAGES, None)
        mapping.pop(const.MAPPING_SENSOR_LAST_SEEN, None)

    reloaded = SmartIrrigationStorage(hass)
    await reloaded.async_load()

    assert reloaded.get_mapping(a)[const.MAPPING_SENSOR_OUTAGES] == []
    assert reloaded.get_mapping(a)[const.MAPPING_SENSOR_LAST_SEEN] == {}


@pytest.mark.asyncio
async def test_a_panel_save_leaves_the_outages_alone(hass) -> None:
    """The panel sends id, name and mappings only (view-mappings.ts), and the
    mapping view's schema admits no other key; what it omits must survive."""
    store, a, _ = await _store_with_two_groups(hass)
    await store.async_update_mapping(a, {const.MAPPING_SENSOR_OUTAGES: [OUTAGE]})

    await store.async_update_mapping(
        a, {const.MAPPING_NAME: "renamed", const.MAPPING_MAPPINGS: {}}
    )

    assert store.get_mapping(a)[const.MAPPING_SENSOR_OUTAGES] == [OUTAGE]
```

- [ ] **Step 2: RED prüfen**

Run: `TZ=UTC … -m pytest tests/test_sensor_liveness_store.py -p _local_socket_unblock -q`
Expected: FAIL — `KeyError: 'sensor_outages'`, `AttributeError: 'SmartIrrigationStorage' object has no attribute
'set_mapping_sensor_last_seen'` und `TypeError` aus `attr.evolve` (unbekanntes Feld `sensor_outages`), je nach Test

- [ ] **Step 3: Implementieren**

Import-Block in `store.py` (alphabetisch einsortieren):

```python
    MAPPING_SENSOR_LAST_SEEN,
    MAPPING_SENSOR_OUTAGES,
```

`MappingEntry`, nach `radiation_calibration = attr.ib(type=list, factory=list)`:

```python
    # ``[{entity_id, device_id, fields, start, end}, ...]``: weather-sensor outages
    # longer than SENSOR_STALE_AFTER_SECONDS, ISO stamps on HA's clock, pruned to
    # SENSOR_OUTAGE_RETENTION_DAYS (sensor_liveness). Bounded like the two above.
    sensor_outages = attr.ib(type=list, factory=list)
    # ``{entity_id: ISO stamp}``: each sensor field's last sign of life, so an
    # outage that spans a restart keeps its start. Rides along on the next write.
    sensor_last_seen = attr.ib(type=dict, factory=dict)
```

Laden, im `MappingEntry(...)`-Aufruf nach `radiation_calibration=…`:

```python
                        sensor_outages=mapping.get(MAPPING_SENSOR_OUTAGES) or [],
                        sensor_last_seen=mapping.get(MAPPING_SENSOR_LAST_SEEN) or {},
```

Neuer Setter direkt nach `set_mapping_last_entry_value`:

```python
    @callback
    def set_mapping_sensor_last_seen(self, mapping_id: int, seen: dict) -> None:
        """Replace a sensor group's signs of life WITHOUT scheduling a save.

        Refreshed at every liveness check, every few minutes; a write each time
        would be a whole document for a value that only matters across a restart.
        It is a MappingEntry field, so it rides along on the next write, like
        ``data_last_entry`` (see ``set_mapping_last_entry_value``). A fresh dict, not
        an in-place update: the attrs factory gives every entry its own, and evolving
        keeps it that way.
        """
        if mapping_id is None:
            return
        mapping_id = int(mapping_id)
        entry = self.mappings.get(mapping_id)
        if entry is None:
            return
        self.mappings[mapping_id] = attr.evolve(entry, sensor_last_seen=dict(seen))
```

- [ ] **Step 4: GREEN prüfen** — Expected: `6 passed`. Zusätzlich die vorhandenen Store-Tests:
`TZ=UTC … -m pytest tests/test_store_buffers.py -p _local_socket_unblock -q` → wie in der Baseline.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/store.py tests/test_sensor_liveness_store.py
git commit -F - <<'EOF'
feat(liveness): store outages and signs of life on the sensor group

Two bounded fields on MappingEntry, read with defaults, so no storage version
change is needed and an older release simply ignores them. The signs of life are
refreshed without scheduling a write and ride along on the next one; a panel save,
which sends id, name and mappings only, leaves both alone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Zustände und Gerät lesen

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py`
- Test: `tests/test_sensor_liveness_coordinator.py` (neu)

- [ ] **Step 1: Failing tests schreiben**

```python
"""Weather-sensor liveness in the coordinator: states, registry, ledger, notice, event."""

import ast
import copy
import pathlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    const,
    sensor_liveness,
)
from custom_components.irrigation_plus.sensor_liveness import (
    Outage,
    _entities_of_device,
    seen_from_state,
)

T0 = datetime(2026, 7, 1, 12, 0, 0)  # naive, on HA's clock


def _aware(local_naive):
    """A naive HA-local wall time as Home Assistant stamps states: aware, in UTC."""
    return dt_util.as_utc(local_naive.replace(tzinfo=dt_util.get_default_time_zone()))


def _state(entity_id, value, reported, changed=None):
    return SimpleNamespace(
        entity_id=entity_id,
        state=value,
        last_reported=_aware(reported),
        last_changed=_aware(changed if changed is not None else reported),
    )


class TestSeenFromState:
    def test_state_stamps_land_on_has_clock(self):
        # Tripwire: the scene only proves the conversion if UTC differs from HA's
        # zone here (the autouse hass fixture puts HA on US/Pacific).
        assert _aware(T0).replace(tzinfo=None) != T0
        seen = seen_from_state(
            _state("sensor.t", "21.5", T0, changed=T0 - timedelta(hours=1))
        )
        assert seen.reported == T0
        assert seen.changed == T0 - timedelta(hours=1)
        assert seen.valid is True

    @pytest.mark.parametrize("value", ["unavailable", "unknown"])
    def test_unavailable_and_unknown_are_not_valid(self, value):
        assert seen_from_state(_state("sensor.t", value, T0)).valid is False

    def test_no_state_is_no_snapshot(self):
        assert seen_from_state(None) is None


async def test_the_device_is_read_from_the_entity_registry(hass):
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "station")}
    )
    registry = er.async_get(hass)
    temp = registry.async_get_or_create(
        "sensor", "test", "temp", device_id=device.id, config_entry=entry
    )
    rain = registry.async_get_or_create(
        "sensor", "test", "rain", device_id=device.id, config_entry=entry
    )
    loose = registry.async_get_or_create("sensor", "test", "loose", config_entry=entry)

    assert _entities_of_device(hass, temp.entity_id) == (device.id, [rain.entity_id])
    assert _entities_of_device(hass, loose.entity_id) == (None, [])
    assert _entities_of_device(hass, "sensor.not_registered") == (None, [])
```

- [ ] **Step 2: RED prüfen**

Run: `TZ=UTC … -m pytest tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name '_entities_of_device'`

- [ ] **Step 3: Implementieren** (Importe ergänzen: `from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN`,
`from homeassistant.util import dt as dt_util`)

```python
def _on_has_clock(stamp: datetime) -> datetime:
    """An HA state stamp (aware, UTC) in the buffer's frame: HA's wall time, naive."""
    return dt_util.as_local(stamp).replace(tzinfo=None)


def seen_from_state(state) -> Seen | None:
    """A liveness snapshot of one HA state, or None when the entity has no state."""
    if state is None:
        return None
    return Seen(
        entity_id=state.entity_id,
        valid=state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN),
        reported=_on_has_clock(state.last_reported),
        changed=_on_has_clock(state.last_changed),
    )


def _entities_of_device(hass, entity_id: str) -> tuple[str | None, list[str]]:
    """The entity's HA device and that device's other enabled entities.

    Reached through this one function so the tests can stand in for it: conftest
    may replace ``homeassistant.helpers`` with a mock (see repairs.py), hence the
    import inside.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    device_id = entry.device_id if entry is not None else None
    if not device_id:
        return None, []
    return device_id, [
        sibling.entity_id
        for sibling in er.async_entries_for_device(registry, device_id)
        if sibling.entity_id != entity_id
    ]
```

- [ ] **Step 4: GREEN prüfen** — Expected: `5 passed`. **Falls** der Registry-Test an einem Mock statt der echten
Registry scheitert (conftest-Ersatz greift): Befund festhalten, nicht umbauen; der Test bleibt der Beleg, dass die
echte API so aufgerufen wird, und läuft in JustChrs CI (HA ≥ 2025.5) ohnehin echt.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness_coordinator.py
git commit -F - <<'EOF'
feat(liveness): read a state's report times on HA's clock and find its device

State stamps are aware UTC; the reading buffer is naive on HA's clock, so they are
converted once, here. The device and its other enabled entities come from the
entity registry.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Die Prüfung im Koordinator

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (Mixin), `custom_components/irrigation_plus/__init__.py` (Import + Basisklasse, `__init__.py:518-544`)
- Test: `tests/test_sensor_liveness_coordinator.py`

- [ ] **Step 1: Failing tests anhängen**

```python
EVENT = f"{const.DOMAIN}_{const.EVENT_WEATHER_STALE}"
STALE = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS)


class _FakeStore:
    def __init__(self, *mappings):
        self.mappings = {int(m[const.MAPPING_ID]): copy.deepcopy(m) for m in mappings}
        self.updates = []

    def get_mapping(self, mapping_id):
        mapping = self.mappings.get(int(mapping_id))
        return copy.deepcopy(mapping) if mapping else None

    async def async_get_mappings(self):
        return [copy.deepcopy(m) for m in self.mappings.values()]

    async def async_update_mapping(self, mapping_id, changes):
        self.updates.append((int(mapping_id), copy.deepcopy(changes)))
        self.mappings[int(mapping_id)].update(copy.deepcopy(changes))

    def set_mapping_sensor_last_seen(self, mapping_id, seen):
        self.mappings[int(mapping_id)][const.MAPPING_SENSOR_LAST_SEEN] = dict(seen)

    def set_mapping_buffer(self, mapping_id, readings):
        pass

    async def async_get_zones(self):
        return []

    async def async_update_zone(self, zone_id, changes):
        pass


class _FakeIssues:
    IssueSeverity = SimpleNamespace(WARNING="warning")

    def __init__(self):
        self.open = {}

    def async_create_issue(self, hass, domain, issue_id, **kwargs):
        self.open[issue_id] = kwargs

    def async_delete_issue(self, hass, domain, issue_id):
        self.open.pop(issue_id, None)


def _group(mapping_id=1, name="Garden", fields=None, outages=None, last_seen=None):
    return {
        const.MAPPING_ID: mapping_id,
        const.MAPPING_NAME: name,
        const.MAPPING_MAPPINGS: {
            field: {
                const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                const.MAPPING_CONF_SENSOR: entity,
            }
            for field, entity in (fields or {}).items()
        },
        const.MAPPING_SENSOR_OUTAGES: outages or [],
        const.MAPPING_SENSOR_LAST_SEEN: last_seen or {},
    }


def _coord(monkeypatch, groups, states, devices):
    """A coordinator over a fake store, fake states and a fake device map."""
    store = _FakeStore(*groups)
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.hass = Mock()
    coord.hass.states.get = Mock(side_effect=states.get)
    coord.hass.bus.async_fire = Mock()
    coord.store = store
    device_of = {e: d for d, entities in devices.items() for e in entities}

    def entities_of_device(hass, entity_id):
        device_id = device_of.get(entity_id)
        siblings = [e for e in devices.get(device_id, []) if e != entity_id]
        return device_id, siblings

    monkeypatch.setattr(sensor_liveness, "_entities_of_device", entities_of_device)
    issues = _FakeIssues()
    monkeypatch.setattr(sensor_liveness, "_issue_registry", lambda: issues)
    return coord, store, issues


def _events(coord):
    return [c.args for c in coord.hass.bus.async_fire.call_args_list]


class TestTheCheck:
    async def test_a_silent_station_opens_its_outages_fires_and_raises_the_notice(
        self, monkeypatch
    ):
        last = T0 - STALE - timedelta(seconds=1)
        coord, store, issues = _coord(
            monkeypatch,
            [_group(fields={"Temperature": "sensor.temp", "Windspeed": "sensor.wind"})],
            {
                "sensor.temp": _state("sensor.temp", "21.5", last),
                "sensor.wind": _state("sensor.wind", "2.0", last),
                "sensor.battery": _state("sensor.battery", "80", last),
            },
            {"dev1": ["sensor.temp", "sensor.wind", "sensor.battery"]},
        )

        await coord.async_check_sensor_liveness(now=T0)

        temp = Outage("sensor.temp", "dev1", ("Temperature",), last)
        wind = Outage("sensor.wind", "dev1", ("Windspeed",), last)
        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [
            temp.to_store(),
            wind.to_store(),
        ]
        assert [args[0] for args in _events(coord)] == [EVENT, EVENT]
        assert [args[1]["stale"] for args in _events(coord)] == [True, True]
        notice = issues.open["weather_sensor_stale_1"]
        assert notice["translation_key"] == const.ISSUE_WEATHER_SENSOR_STALE
        assert notice["is_fixable"] is False
        assert notice["translation_placeholders"]["entities"] == (
            "sensor.temp (Temperature), sensor.wind (Windspeed)"
        )

    async def test_a_steady_rain_gauge_on_a_living_station_stays_quiet(
        self, monkeypatch
    ):
        coord, store, issues = _coord(
            monkeypatch,
            [_group(fields={"Precipitation": "sensor.rain"})],
            {
                "sensor.rain": _state("sensor.rain", "0.0", T0 - timedelta(hours=10)),
                "sensor.temp": _state("sensor.temp", "14.2", T0 - timedelta(minutes=1)),
            },
            {"dev1": ["sensor.rain", "sensor.temp"]},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert _events(coord) == []
        assert issues.open == {}

    async def test_the_return_closes_the_outage_at_the_first_report(self, monkeypatch):
        start = T0 - timedelta(hours=6)
        back = T0 - timedelta(minutes=4)
        open_ = Outage("sensor.temp", "dev1", ("Temperature",), start)
        coord, store, issues = _coord(
            monkeypatch,
            [
                _group(
                    fields={"Temperature": "sensor.temp"},
                    outages=[open_.to_store()],
                )
            ],
            {
                "sensor.temp": _state(
                    "sensor.temp", "18.0", T0 - timedelta(seconds=10), changed=back
                )
            },
            {"dev1": ["sensor.temp"]},
        )
        issues.open["weather_sensor_stale_1"] = {}

        await coord.async_check_sensor_liveness(now=T0)

        ended = Outage("sensor.temp", "dev1", ("Temperature",), start, back)
        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [ended.to_store()]
        assert _events(coord)[0][1]["stale"] is False
        assert _events(coord)[0][1]["until"] == back.isoformat()
        assert issues.open == {}

    async def test_the_signs_of_life_ride_along_without_a_write(self, monkeypatch):
        coord, store, _ = _coord(
            monkeypatch,
            [_group(fields={"Temperature": "sensor.temp"})],
            {"sensor.temp": _state("sensor.temp", "18.0", T0 - timedelta(minutes=1))},
            {"dev1": ["sensor.temp"]},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert store.updates == []
        assert store.mappings[1][const.MAPPING_SENSOR_LAST_SEEN] == {
            "sensor.temp": (T0 - timedelta(minutes=1)).isoformat()
        }

    async def test_an_outage_spanning_a_restart_keeps_its_start(self, monkeypatch):
        before = T0 - timedelta(hours=5)
        coord, store, _ = _coord(
            monkeypatch,
            [
                _group(
                    fields={"Temperature": "sensor.temp"},
                    last_seen={"sensor.temp": before.isoformat()},
                )
            ],
            {
                # Restored as unavailable at the restart; its device's battery
                # entity reports again, which must not vouch for the dead one.
                "sensor.temp": _state(
                    "sensor.temp", "unavailable", T0 - timedelta(minutes=2)
                ),
                "sensor.battery": _state(
                    "sensor.battery", "80", T0 - timedelta(minutes=1)
                ),
            },
            {"dev1": ["sensor.temp", "sensor.battery"]},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [
            Outage("sensor.temp", "dev1", ("Temperature",), before).to_store()
        ]

    async def test_home_assistants_own_downtime_is_not_an_outage(self, monkeypatch):
        """Down for four hours, the station pushes again right after the start: its
        fresh report vouches for it before the first check, so nothing opens."""
        coord, store, issues = _coord(
            monkeypatch,
            [
                _group(
                    fields={"Temperature": "sensor.temp"},
                    last_seen={"sensor.temp": (T0 - timedelta(hours=4)).isoformat()},
                )
            ],
            {"sensor.temp": _state("sensor.temp", "16.0", T0 - timedelta(minutes=8))},
            {"dev1": ["sensor.temp"]},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert _events(coord) == []
        assert issues.open == {}

    async def test_a_value_set_by_hand_never_goes_stale(self, monkeypatch):
        coord, store, issues = _coord(
            monkeypatch,
            [_group(fields={"Pressure": "input_number.pressure"})],
            {
                "input_number.pressure": _state(
                    "input_number.pressure", "1013", T0 - timedelta(days=30)
                )
            },
            {},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert store.mappings[1][const.MAPPING_SENSOR_LAST_SEEN] == {}
        assert issues.open == {}

    async def test_an_entity_never_seen_starts_its_bridge_at_the_first_look(
        self, monkeypatch
    ):
        coord, store, _ = _coord(
            monkeypatch, [_group(fields={"Temperature": "sensor.ghost"})], {}, {}
        )

        await coord.async_check_sensor_liveness(now=T0)
        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert store.mappings[1][const.MAPPING_SENSOR_LAST_SEEN] == {
            "sensor.ghost": T0.isoformat()
        }

        await coord.async_check_sensor_liveness(now=T0 + STALE + timedelta(seconds=1))
        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [
            Outage("sensor.ghost", None, ("Temperature",), T0).to_store()
        ]

    async def test_one_broken_group_does_not_stop_the_others(self, monkeypatch):
        last = T0 - STALE - timedelta(seconds=1)
        coord, store, _ = _coord(
            monkeypatch,
            [
                _group(1, "Broken", fields={"Temperature": "sensor.bad"}),
                _group(2, "Fine", fields={"Temperature": "sensor.t"}),
            ],
            {"sensor.t": _state("sensor.t", "18.0", last)},
            {},
        )
        real = sensor_liveness._entities_of_device

        def boom(hass, entity_id):
            if entity_id == "sensor.bad":
                raise RuntimeError("registry exploded")
            return real(hass, entity_id)

        monkeypatch.setattr(sensor_liveness, "_entities_of_device", boom)

        await coord.async_check_sensor_liveness(now=T0)

        assert len(store.mappings[2][const.MAPPING_SENSOR_OUTAGES]) == 1
```

Hinweis zum letzten Test: `real` ist hier schon die Fake-Funktion aus `_coord` (sie wurde vorher gesetzt); `boom`
reicht an sie weiter.

Dazu die Tauschfälle (User-Anforderung: ein neu beschafftes Gerät darf zu keinen Fehlern führen):

```python
class TestAReplacedDevice:
    async def test_a_new_device_under_the_same_entity_ids_closes_the_outage(
        self, monkeypatch
    ):
        """The old station died; the new one took over its entity ids. The entity
        now belongs to the new device, which reports: the outage ends there."""
        start = T0 - timedelta(hours=6)
        back = T0 - timedelta(minutes=2)
        open_ = Outage("sensor.temp", "old-station", ("Temperature",), start)
        coord, store, issues = _coord(
            monkeypatch,
            [_group(fields={"Temperature": "sensor.temp"}, outages=[open_.to_store()])],
            {
                "sensor.temp": _state(
                    "sensor.temp", "17.0", T0 - timedelta(seconds=30), changed=back
                ),
                "sensor.wind": _state("sensor.wind", "1.0", T0 - timedelta(seconds=30)),
            },
            {"new-station": ["sensor.temp", "sensor.wind"]},
        )
        issues.open["weather_sensor_stale_1"] = {}

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [
            Outage(
                "sensor.temp", "old-station", ("Temperature",), start, back
            ).to_store()
        ]
        assert issues.open == {}

    async def test_an_entity_deleted_with_the_old_device_raises_the_notice(
        self, monkeypatch
    ):
        """The sensor group still names an entity that no longer exists: no data
        arrives, so after the limit the notice asks for the new entities."""
        coord, store, issues = _coord(
            monkeypatch,
            [
                _group(
                    fields={"Temperature": "sensor.gone"},
                    last_seen={
                        "sensor.gone": (T0 - STALE - timedelta(seconds=1)).isoformat()
                    },
                )
            ],
            {},
            {},
        )

        await coord.async_check_sensor_liveness(now=T0)

        assert len(store.mappings[1][const.MAPPING_SENSOR_OUTAGES]) == 1
        assert "weather_sensor_stale_1" in issues.open

    async def test_an_outage_left_by_another_path_ends_with_its_event(
        self, monkeypatch
    ):
        """The ledger still holds an outage for an entity the group no longer reads
        (its mapping changed without emptying the ledger): it ends now, with its
        end event, and the notice goes."""
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.gone", "dev1", ("Temperature",), start)
        coord, store, issues = _coord(
            monkeypatch,
            [_group(fields={"Temperature": "sensor.new"}, outages=[open_.to_store()])],
            {"sensor.new": _state("sensor.new", "16.0", T0 - timedelta(minutes=1))},
            {"dev2": ["sensor.new"]},
        )
        issues.open["weather_sensor_stale_1"] = {}

        await coord.async_check_sensor_liveness(now=T0)

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == [
            Outage("sensor.gone", "dev1", ("Temperature",), start, T0).to_store()
        ]
        assert [(a[1]["entity_id"], a[1]["stale"]) for a in _events(coord)] == [
            ("sensor.gone", False)
        ]
        assert issues.open == {}
```

Die ersten zwei dieser Tests sind Charakterisierungen: Sie waren im Probelauf schon vor jeder Änderung grün und halten
fest, dass der Entwurf die Fälle trägt; der dritte braucht den Zweig aus Task 5.

Dazu JustChrs erster Hinweis-Test (`JustChr#188`: „the repair issue clearing on recovery“), in einer eigenen Datei
gegen den **echten** Store und die **echte** Issue-Registry von Home Assistant; die Uhr steht im `freezer`-Fixture
(`local_naive_now()` liest `dt_util.now()` und folgt ihm). Neue Datei `tests/test_sensor_liveness_repair.py`:

```python
"""The repair issue of a silent weather sensor, in Home Assistant's own issue
registry and over the integration's real store (#188): it clears when the sensor
reports again, it survives a restart in the middle of an outage, and it goes when
its sensor group is deleted."""

from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.store import SmartIrrigationStorage

ENTITY = "sensor.station_temperature"
EVENT = f"{const.DOMAIN}_{const.EVENT_WEATHER_STALE}"
# One minute past the limit: the outage opens at the next check.
SILENCE = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS + 60)


def _coordinator_over(hass, store):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.hass = hass
    coord.store = store
    return coord


async def _garden(hass):
    """A coordinator over a fresh real store with one sensor group reading ENTITY."""
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    group = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Garden",
            const.MAPPING_MAPPINGS: {
                const.MAPPING_TEMPERATURE: {
                    const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                    const.MAPPING_CONF_SENSOR: ENTITY,
                }
            },
        }
    )
    return _coordinator_over(hass, store), group[const.MAPPING_ID]


def _notice(hass, mapping_id):
    """The group's repair issue as Home Assistant shows it, or None."""
    issue = ir.async_get(hass).async_get_issue(
        const.DOMAIN, f"{const.ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}"
    )
    return issue if issue is not None and issue.active else None


def _listen(hass):
    """Every irrigation_plus_weather_stale event, as (entity_id, stale)."""
    heard = []

    @callback
    def _on(event):
        heard.append((event.data["entity_id"], event.data["stale"]))

    hass.bus.async_listen(EVENT, _on)
    return heard


async def _silent_past_the_limit(hass, freezer, coord):
    """ENTITY reports once, then nothing for longer than the limit; one check."""
    hass.states.async_set(ENTITY, "21.5")
    freezer.tick(SILENCE)
    await coord.async_check_sensor_liveness()


async def test_the_notice_clears_when_the_sensor_reports_again(hass, freezer):
    coord, mapping_id = await _garden(hass)
    heard = _listen(hass)
    await _silent_past_the_limit(hass, freezer, coord)
    assert _notice(hass, mapping_id) is not None

    hass.states.async_set(ENTITY, "18.0")
    await coord.async_check_sensor_liveness()
    await hass.async_block_till_done()

    assert _notice(hass, mapping_id) is None
    assert heard == [(ENTITY, True), (ENTITY, False)]
```

- [ ] **Step 2: RED prüfen** — Expected: `AttributeError: 'SmartIrrigationCoordinator' object has no attribute 'async_check_sensor_liveness'`,
in beiden Dateien (`tests/test_sensor_liveness_coordinator.py`, `tests/test_sensor_liveness_repair.py`)

- [ ] **Step 3: Implementieren**

In `sensor_liveness.py` (Importe ergänzen: `from .helpers import STAMP_FROM_STORE, coerce_stamp, local_naive_now`):

```python
def _issue_registry():
    """Home Assistant's issue registry module.

    Reached through this one function so the tests can stand in for it: conftest
    may replace ``homeassistant.helpers`` with a mock (see repairs.py).
    """
    from homeassistant.helpers import issue_registry as ir

    return ir


class SensorLivenessMixin:
    """Coordinator glue: the periodic check, the ledger, the notice and the event."""

    async def async_check_sensor_liveness(self, now: datetime | None = None) -> None:
        """Check every sensor group once."""
        now = now if now is not None else local_naive_now()
        for mapping in await self.store.async_get_mappings():
            try:
                await self._async_check_mapping_liveness(mapping, now)
            except Exception:
                # A periodic check: one broken group must not stop the others,
                # every five minutes, for good.
                _LOGGER.exception(
                    "Sensor liveness check failed for sensor group %s",
                    mapping.get(const.MAPPING_ID),
                )

    async def _async_check_mapping_liveness(self, mapping: dict, now: datetime) -> None:
        mapping_id = mapping[const.MAPPING_ID]
        name = mapping.get(const.MAPPING_NAME) or str(mapping_id)
        outages = outages_of(mapping)
        open_start = {o.entity_id: o.start for o in outages if o.end is None}
        remembered = mapping.get(const.MAPPING_SENSOR_LAST_SEEN) or {}
        evidence: dict[str, Evidence] = {}
        fields_by_entity = sensor_fields_by_entity(
            mapping.get(const.MAPPING_MAPPINGS) or {}
        )
        for entity_id, fields in fields_by_entity.items():
            own, siblings, device_id = self._sensor_liveness_snapshot(entity_id)
            last = last_sign_of_life(
                own, siblings, coerce_stamp(remembered.get(entity_id), STAMP_FROM_STORE)
            )
            if last is None:
                # Never seen and nothing remembered: count the limit from this first
                # look, not from never.
                last = now
            recovered = None
            if entity_id in open_start:
                recovered = first_report_after(own, siblings, open_start[entity_id])
            evidence[entity_id] = Evidence(fields, device_id, last, recovered)

        kept, opened, closed = advance_outages(outages, evidence, now)
        self.store.set_mapping_sensor_last_seen(
            mapping_id, {e: ev.last.isoformat() for e, ev in evidence.items()}
        )
        if kept != outages:
            await self.store.async_update_mapping(
                mapping_id,
                {const.MAPPING_SENSOR_OUTAGES: [o.to_store() for o in kept]},
            )
        for outage in opened:
            _LOGGER.warning(
                "Sensor group %s: %s (%s) has not reported since %s; its last "
                "value is still used",
                name,
                outage.entity_id,
                ", ".join(outage.fields),
                outage.start,
            )
            self._fire_weather_stale(mapping_id, name, outage)
        for outage in closed:
            _LOGGER.info(
                "Sensor group %s: %s reports again (silent from %s to %s)",
                name,
                outage.entity_id,
                outage.start,
                outage.end,
            )
            self._fire_weather_stale(mapping_id, name, outage)
        if opened or closed:
            self._sync_stale_issue(mapping_id, name, kept)

    def _sensor_liveness_snapshot(self, entity_id: str):
        """``(own, siblings, device_id)`` for one sensor-mapped entity."""
        device_id, sibling_ids = _entities_of_device(self.hass, entity_id)
        own = seen_from_state(self.hass.states.get(entity_id))
        siblings = [
            seen
            for sibling_id in sibling_ids
            if (seen := seen_from_state(self.hass.states.get(sibling_id))) is not None
        ]
        return own, siblings, device_id

    def _fire_weather_stale(self, mapping_id, name: str, outage: Outage) -> None:
        self.hass.bus.async_fire(
            f"{const.DOMAIN}_{const.EVENT_WEATHER_STALE}",
            outage_event_payload(mapping_id, name, outage),
        )

    def _sync_stale_issue(self, mapping_id, name: str, outages: list[Outage]) -> None:
        """Raise, update or clear the group's repair issue from its outages."""
        ir = _issue_registry()
        issue_id = f"{const.ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}"
        placeholders = stale_issue_placeholders(name, outages)
        if placeholders is None:
            ir.async_delete_issue(self.hass, const.DOMAIN, issue_id)
            return
        ir.async_create_issue(
            self.hass,
            const.DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=const.ISSUE_WEATHER_SENSOR_STALE,
            translation_placeholders=placeholders,
        )

    def _retire_outages(self, mapping: dict | None) -> None:
        """End a group's open outages because its ledger is being emptied.

        A source change (a sensor replaced), deleting the group or resetting the
        weather data empties the ledger. Every open outage still gets its end
        event, so an automation that reacted to the start hears that it is over,
        and the group's notice goes. Without an open outage there is no notice --
        it is raised from the ledger and, being non-persistent, does not outlive a
        restart -- so the issue registry is not asked.
        """
        silent = [o for o in outages_of(mapping or {}) if o.end is None]
        if not silent:
            return
        now = local_naive_now()
        mapping_id = mapping[const.MAPPING_ID]
        name = mapping.get(const.MAPPING_NAME) or str(mapping_id)
        for outage in silent:
            self._fire_weather_stale(mapping_id, name, replace(outage, end=now))
        _issue_registry().async_delete_issue(
            self.hass, const.DOMAIN, f"{const.ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}"
        )
```

**Probelauf-Befunde (2026-10-03):**
1. Die erste Fassung (`_delete_stale_issue(mapping_id)`) fragte die Registry bedingungslos. Damit wurden 11
   vorhandene Tests rot (`test_clear_all_weatherdata.py`, `test_clear_weatherdata_resets_deadband.py`,
   `test_continuous_update.py::TestClearWeatherData`, `test_mapping_source_change.py`): `ir.async_delete_issue` liest
   `hass.data`, dort ist `hass` ein Mock (`TypeError: argument of type 'Mock' is not iterable`). Die Prüfung auf
   einen offenen Ausfall ist die sachliche Antwort, kein Test-Trick: Ohne offenen Ausfall gibt es keinen Hinweis.
2. Gerätetausch (User): Leert ein Quellwechsel, Löschen oder Reset die Liste, endete ein offener Ausfall bisher ohne
   End-Event; eine Automation, die auf den Start reagiert hatte, wäre hängen geblieben. Deshalb feuert
   `_retire_outages` für jeden offenen Ausfall das End-Event (`until` = jetzt), und `advance_outages` beendet einen
   Ausfall, dessen Entität die Gruppe nicht mehr liest (Task 5), damit keine Liste und kein Hinweis die
   Konfiguration überleben.

In `__init__.py`: Import direkt nach `from .self_closing import SelfClosingMixin` (alphabetisch)

```python
from .sensor_liveness import SensorLivenessMixin
```

und in den Basen von `SmartIrrigationCoordinator` direkt nach `ContinuousUpdateMixin,`:

```python
    SensorLivenessMixin,
```

- [ ] **Step 4: GREEN prüfen** — Expected: `17 passed` in `tests/test_sensor_liveness_coordinator.py`, `1 passed` in
`tests/test_sensor_liveness_repair.py`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/__init__.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_repair.py
git commit -F - <<'EOF'
feat(liveness): the coordinator checks each sensor group's sensors

Per sensor-mapped entity: its state, its device's other states and the sign of
life remembered from the last check give the evidence; the ledger is advanced, the
signs ride along without a write, every outage start and end fires
irrigation_plus_weather_stale, and the group's repair issue follows the open
outages. One broken group does not stop the others.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Starten, Karenz, Beenden

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (Mixin), `custom_components/irrigation_plus/__init__.py` (`async_setup_timers` `__init__.py:763-789`, `async_unload` `__init__.py:2207-2249`)
- Test: `tests/test_sensor_liveness_coordinator.py`

- [ ] **Step 1: Failing tests anhängen**

```python
class TestTimer:
    async def test_setup_shows_a_still_open_outage_at_once(self, monkeypatch):
        open_ = Outage("sensor.temp", "dev1", ("Temperature",), T0 - timedelta(hours=5))
        coord, _, issues = _coord(
            monkeypatch,
            [_group(fields={"Temperature": "sensor.temp"}, outages=[open_.to_store()])],
            {},
            {},
        )
        unsub = Mock()
        monkeypatch.setattr(
            sensor_liveness, "async_track_time_interval", Mock(return_value=unsub)
        )

        await coord.async_setup_sensor_liveness()

        assert "weather_sensor_stale_1" in issues.open
        assert coord._sensor_liveness_unsub is unsub

    async def test_the_check_waits_out_the_startup_grace(self, monkeypatch):
        coord, _, _ = _coord(monkeypatch, [], {}, {})
        coord.async_check_sensor_liveness = AsyncMock()
        coord._sensor_liveness_armed_at = T0
        clock = {"now": T0 - timedelta(seconds=1)}
        monkeypatch.setattr(sensor_liveness, "local_naive_now", lambda: clock["now"])

        await coord._async_sensor_liveness_tick()
        coord.async_check_sensor_liveness.assert_not_awaited()

        clock["now"] = T0
        await coord._async_sensor_liveness_tick()
        coord.async_check_sensor_liveness.assert_awaited_once()

    def test_teardown_cancels_the_timer(self, monkeypatch):
        coord, _, _ = _coord(monkeypatch, [], {}, {})
        unsub = Mock()
        coord._sensor_liveness_unsub = unsub

        coord.async_teardown_sensor_liveness()

        unsub.assert_called_once()
        assert coord._sensor_liveness_unsub is None


INIT = (
    pathlib.Path(__file__).parent.parent
    / "custom_components"
    / "irrigation_plus"
    / "__init__.py"
)


def _attribute_calls_in(function_name):
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ):
            return {
                call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            }
    raise AssertionError(f"{function_name} not found in __init__.py")


def test_setup_arms_the_check_and_unload_disarms_it():
    assert "async_setup_sensor_liveness" in _attribute_calls_in("async_setup_timers")
    assert "async_teardown_sensor_liveness" in _attribute_calls_in("async_unload")
```

Dazu JustChrs zweiter Hinweis-Test („surviving a restart in the middle of an outage“), angehängt an
`tests/test_sensor_liveness_repair.py`. Der Neustart wird so nachgestellt, wie Home Assistant ihn erlebt: Ein nicht
dauerhafter Hinweis kommt nicht von selbst zurück, die Entität steht danach auf `unavailable`, und ein neuer Store
liest, was der alte geschrieben hat.

```python
async def test_the_notice_survives_a_restart_in_the_middle_of_an_outage(hass, freezer):
    coord, mapping_id = await _garden(hass)
    await _silent_past_the_limit(hass, freezer, coord)
    since = _notice(hass, mapping_id).translation_placeholders["since"]
    await coord.store.async_save()

    # The restart. Home Assistant does not put a non-persistent issue back on
    # screen by itself, the station's entity comes back unavailable, and a new
    # store reads what the old one wrote.
    ir.async_delete_issue(
        hass, const.DOMAIN, f"{const.ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}"
    )
    hass.states.async_set(ENTITY, "unavailable")
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    after = _coordinator_over(hass, store)

    await after.async_setup_sensor_liveness()
    try:
        notice = _notice(hass, mapping_id)
        assert notice is not None
        assert notice.translation_placeholders["since"] == since
        # Still silent at the first check after the grace: same outage, same start.
        freezer.tick(timedelta(seconds=const.SENSOR_LIVENESS_STARTUP_GRACE_SECONDS))
        await after.async_check_sensor_liveness()
        notice = _notice(hass, mapping_id)
        assert notice is not None
        assert notice.translation_placeholders["since"] == since
    finally:
        after.async_teardown_sensor_liveness()
```

`async_teardown_sensor_liveness` im `finally`: Der Test arbeitet mit dem echten `hass`, und ein stehengebliebener
Intervall-Timer würde die Aufräumprüfung des Fixtures rot machen.

- [ ] **Step 2: RED prüfen** — Expected: `AttributeError: … 'async_setup_sensor_liveness'` (auch im neuen Hinweis-Test)
bzw. die AST-Assertion schlägt fehl

- [ ] **Step 3: Implementieren**

In `sensor_liveness.py` (Importe ergänzen: `from homeassistant.core import callback`,
`from homeassistant.helpers.event import async_track_time_interval`), im Mixin:

```python
    async def async_setup_sensor_liveness(self) -> None:
        """Arm the periodic check; show at once what the ledger still holds open.

        The first checks wait out a grace after setup so integrations can create
        their entities first; an outage that was open before a restart is shown
        straight away, because the ledger already says the sensor is silent.
        """
        self.async_teardown_sensor_liveness()
        self._sensor_liveness_armed_at = local_naive_now() + timedelta(
            seconds=const.SENSOR_LIVENESS_STARTUP_GRACE_SECONDS
        )
        for mapping in await self.store.async_get_mappings():
            outages = outages_of(mapping)
            if not any(o.end is None for o in outages):
                continue  # nothing to show: a notice exists only for an open outage
            mapping_id = mapping[const.MAPPING_ID]
            self._sync_stale_issue(
                mapping_id, mapping.get(const.MAPPING_NAME) or str(mapping_id), outages
            )
        self._sensor_liveness_unsub = async_track_time_interval(
            self.hass,
            self._async_sensor_liveness_tick,
            timedelta(seconds=const.SENSOR_LIVENESS_INTERVAL_SECONDS),
        )

    @callback
    def async_teardown_sensor_liveness(self) -> None:
        """Cancel the periodic check (unload, reload)."""
        unsub = getattr(self, "_sensor_liveness_unsub", None)
        if unsub is not None:
            unsub()
        self._sensor_liveness_unsub = None

    async def _async_sensor_liveness_tick(self, _now=None) -> None:
        armed_at = getattr(self, "_sensor_liveness_armed_at", None)
        if armed_at is not None and local_naive_now() < armed_at:
            return
        await self.async_check_sensor_liveness()
```

In `__init__.py`, `async_setup_timers`, nach `await self.async_setup_continuous_updates()`:

```python
        # Weather-sensor liveness: notices a mapped sensor that has fallen silent.
        await self.async_setup_sensor_liveness()
```

In `__init__.py`, `async_unload`, nach `self.async_teardown_continuous_updates()`:

```python
        # The liveness check is a plain interval timer; a reload would otherwise
        # leave the old coordinator checking alongside the new one.
        self.async_teardown_sensor_liveness()
```

- [ ] **Step 4: GREEN prüfen** — Expected: `21 passed` in `tests/test_sensor_liveness_coordinator.py`, `2 passed` in
`tests/test_sensor_liveness_repair.py`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/__init__.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_repair.py
git commit -F - <<'EOF'
feat(liveness): run the check every five minutes, after a startup grace

The check starts ten minutes after setup so integrations can create their
entities first; an outage the ledger still holds open is shown again at once.
Unload cancels the timer, so a reload does not leave two coordinators checking.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 11: Quellwechsel, Löschen, Zurücksetzen

**Files:**
- Modify: `custom_components/irrigation_plus/__init__.py` (`async_update_mapping_config`, `__init__.py:1754-1817`), `custom_components/irrigation_plus/calculation.py` (`_async_clear_all_weatherdata`, `calculation.py:350-363`)
- Test: `tests/test_sensor_liveness_coordinator.py`

- [ ] **Step 1: Failing tests anhängen**

```python
OPEN_RECORD = Outage(
    "sensor.old", "dev1", ("Temperature",), T0 - timedelta(hours=5)
).to_store()


def _mock_store_coord(monkeypatch, mapping):
    """The harness of tests/test_mapping_source_change.py: a Mock store."""
    store = Mock()
    store.get_mapping = Mock(return_value=mapping)
    store.async_update_mapping = AsyncMock()
    store.async_update_zone = AsyncMock()
    store.async_delete_mapping = AsyncMock(return_value=True)
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.store = store
    coord.hass = Mock()
    coord._get_zones_that_use_this_mapping = AsyncMock(return_value=[])
    issues = _FakeIssues()
    issues.open["weather_sensor_stale_0"] = {}
    monkeypatch.setattr(sensor_liveness, "_issue_registry", lambda: issues)
    return coord, store, issues


def _sensor_group_zero(entity):
    group = _group(
        0,
        fields={"Temperature": entity},
        outages=[OPEN_RECORD],
        last_seen={"sensor.old": T0.isoformat()},
    )
    group[const.MAPPING_DATA_LAST_ENTRY] = {}
    return group


class TestTheLedgerFollowsTheConfiguration:
    async def test_a_source_change_empties_the_ledger_and_drops_the_notice(
        self, monkeypatch
    ):
        coord, store, issues = _mock_store_coord(
            monkeypatch, _sensor_group_zero("sensor.old")
        )
        new = {
            const.MAPPING_MAPPINGS: {
                "Temperature": {
                    const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                    const.MAPPING_CONF_SENSOR: "sensor.new",
                }
            }
        }
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_mapping_config(0, new)

        args, _ = store.async_update_mapping.call_args
        assert args[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert args[1][const.MAPPING_SENSOR_LAST_SEEN] == {}
        assert "weather_sensor_stale_0" not in issues.open
        # The replaced sensor's outage still ends, so an automation hears it.
        fired = [c.args for c in coord.hass.bus.async_fire.call_args_list]
        assert [(a[0], a[1]["entity_id"], a[1]["stale"]) for a in fired] == [
            (EVENT, "sensor.old", False)
        ]
        assert fired[0][1]["until"] is not None

    async def test_a_group_without_an_open_outage_leaves_the_registry_alone(
        self, monkeypatch
    ):
        """No open outage, no notice to clear: the issue registry is not asked."""
        group = _sensor_group_zero("sensor.old")
        group[const.MAPPING_SENSOR_OUTAGES] = []
        coord, _, _ = _mock_store_coord(monkeypatch, group)
        monkeypatch.setattr(
            sensor_liveness,
            "_issue_registry",
            Mock(side_effect=AssertionError("issue registry asked")),
        )
        new = {
            const.MAPPING_MAPPINGS: {
                "Temperature": {
                    const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                    const.MAPPING_CONF_SENSOR: "sensor.new",
                }
            }
        }
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_mapping_config(0, new)
        await coord.async_update_mapping_config(0, {const.ATTR_REMOVE: True})
        coord.hass.bus.async_fire.assert_not_called()

    async def test_a_rename_keeps_the_ledger_and_the_notice(self, monkeypatch):
        coord, store, issues = _mock_store_coord(
            monkeypatch, _sensor_group_zero("sensor.old")
        )
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_mapping_config(0, {const.MAPPING_NAME: "renamed"})

        args, _ = store.async_update_mapping.call_args
        assert const.MAPPING_SENSOR_OUTAGES not in args[1]
        assert "weather_sensor_stale_0" in issues.open

    async def test_deleting_a_group_drops_its_notice(self, monkeypatch):
        coord, store, issues = _mock_store_coord(
            monkeypatch, _sensor_group_zero("sensor.old")
        )
        await coord.async_update_mapping_config(0, {const.ATTR_REMOVE: True})

        store.async_delete_mapping.assert_awaited_once()
        assert "weather_sensor_stale_0" not in issues.open
        fired = [c.args for c in coord.hass.bus.async_fire.call_args_list]
        assert [(a[0], a[1]["stale"]) for a in fired] == [(EVENT, False)]

    async def test_reset_all_weather_data_empties_the_ledger(self, monkeypatch):
        coord, store, issues = _coord(
            monkeypatch,
            [
                _group(
                    fields={"Temperature": "sensor.old"},
                    outages=[OPEN_RECORD],
                    last_seen={"sensor.old": T0.isoformat()},
                )
            ],
            {},
            {},
        )
        issues.open["weather_sensor_stale_1"] = {}
        coord.clear_continuous_deadband_state = Mock()
        coord.invalidate_live_estimate_carry = Mock()
        monkeypatch.setattr(
            "custom_components.irrigation_plus.calculation.async_dispatcher_send",
            Mock(),
        )

        await coord._async_clear_all_weatherdata()

        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES] == []
        assert store.mappings[1][const.MAPPING_SENSOR_LAST_SEEN] == {}
        assert issues.open == {}
        assert [(a[0], a[1]["stale"]) for a in _events(coord)] == [(EVENT, False)]
```

Dazu JustChrs dritter Hinweis-Test („being removed when the group is deleted“), angehängt an
`tests/test_sensor_liveness_repair.py`:

```python
async def test_the_notice_goes_when_its_sensor_group_is_deleted(hass, freezer):
    coord, mapping_id = await _garden(hass)
    heard = _listen(hass)
    await _silent_past_the_limit(hass, freezer, coord)
    assert _notice(hass, mapping_id) is not None

    await coord.async_update_mapping_config(mapping_id, {const.ATTR_REMOVE: True})
    await hass.async_block_till_done()

    assert coord.store.get_mapping(mapping_id) is None
    assert _notice(hass, mapping_id) is None
    assert heard == [(ENTITY, True), (ENTITY, False)]
```

- [ ] **Step 2: RED prüfen** — Expected: 3 FAIL (`KeyError: 'sensor_outages'` in den `call_args`, Hinweis noch offen);
`test_a_group_without_an_open_outage_…` und `test_a_rename_keeps_…` PASS (schon vor der Änderung wahr; sie halten
die Abgrenzung fest und werden rot, wenn die Prüfung auf offene Ausfälle verloren geht). Im Hinweis-Test FAIL
`test_the_notice_goes_when_its_sensor_group_is_deleted` (Hinweis noch offen, kein End-Event).

- [ ] **Step 3: Implementieren**

`__init__.py`, Lösch-Zweig von `async_update_mapping_config`:

```python
            await self.store.async_delete_mapping(mapping_id)
            # Its notice would otherwise outlive it until the next restart.
            self._retire_outages(res)
```

(`res` ist das schon vorhandene `self.store.get_mapping(mapping_id)` vom Anfang des Zweigs, also der Stand vor dem
Löschen.)

`__init__.py`, Quellwechsel: die vorhandenen Zeilen

```python
                stale = (self.store.get_mapping(mapping_id) or {}).get(
                    const.MAPPING_DATA_LAST_ENTRY
                ) or {}
```

ersetzen durch

```python
                before = self.store.get_mapping(mapping_id) or {}
                stale = before.get(const.MAPPING_DATA_LAST_ENTRY) or {}
```

und im `data = {…}`-Block nach `const.MAPPING_DATA_LAST_ENTRY: dict.fromkeys(stale),`

```python
                    # A different sensor has no outage history: the old one's
                    # outages and signs of life describe a different device.
                    const.MAPPING_SENSOR_OUTAGES: [],
                    const.MAPPING_SENSOR_LAST_SEEN: {},
```

und direkt nach `await self.store.async_update_mapping(mapping_id, data)` am Anfang des
`if source_changed:`-Blocks:

```python
                self._retire_outages(before)
```

`calculation.py`, `_async_clear_all_weatherdata`, im `async_update_mapping`-Dict nach dem
`MAPPING_DATA_LAST_ENTRY`-Eintrag:

```python
                    # Outages describe readings that no longer exist.
                    const.MAPPING_SENSOR_OUTAGES: [],
                    const.MAPPING_SENSOR_LAST_SEEN: {},
```

und nach dem `await self.store.async_update_mapping(…)`-Aufruf, noch in der Schleife (`mapping` ist der Stand vor
dem Zurücksetzen):

```python
            self._retire_outages(mapping)
```

- [ ] **Step 4: GREEN prüfen** — Expected: `26 passed` in `tests/test_sensor_liveness_coordinator.py`, `3 passed` in
`tests/test_sensor_liveness_repair.py`; zusätzlich unverändert grün (die Tests mit Mock-`hass`, an denen der Probelauf
den Fehler fand):
`TZ=UTC … -m pytest tests/test_mapping_source_change.py tests/test_continuous_update.py tests/test_clear_all_weatherdata.py tests/test_clear_weatherdata_resets_deadband.py -p _local_socket_unblock -q`

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/__init__.py custom_components/irrigation_plus/calculation.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_repair.py
git commit -F - <<'EOF'
feat(liveness): the ledger follows source changes, deletion and reset

A source change empties the group's outages and signs of life, as it empties its
buffer and carry-forwards today; "reset all weather data" does the same; deleting
a group drops its notice. Every open outage still gets its end event, so an
automation that reacted to the start hears the end when a sensor is replaced. A
group without an open outage leaves the issue registry alone; a rename leaves
everything alone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 12: Der Hinweistext in 8 Sprachen

**Files:**
- Modify: `custom_components/irrigation_plus/translations/{en,de,es,fr,it,nl,no,sk}.json` (Block `"issues": {`, jeweils um Zeile 455)
- Test: `tests/test_sensor_liveness.py`

- [ ] **Step 1: Failing test anhängen** (Importe: `import json`, `import pathlib`)

```python
TRANSLATIONS = (
    pathlib.Path(__file__).parent.parent
    / "custom_components"
    / "irrigation_plus"
    / "translations"
)


@pytest.mark.parametrize("lang", ["de", "en", "es", "fr", "it", "nl", "no", "sk"])
def test_the_stale_notice_has_texts_with_their_placeholders(lang):
    issues = json.loads((TRANSLATIONS / f"{lang}.json").read_text(encoding="utf-8"))[
        "issues"
    ]
    notice = issues[const.ISSUE_WEATHER_SENSOR_STALE]
    # Not fixable, so a description and no fix_flow (Home Assistant allows one).
    assert set(notice) == {"title", "description"}
    assert "{group}" in notice["title"]
    assert "{entities}" in notice["description"]
    assert "{since}" in notice["description"]
```

- [ ] **Step 2: RED prüfen** — Expected: 8× FAIL mit `KeyError: 'weather_sensor_stale'`

- [ ] **Step 3: In jede Datei als ersten Eintrag nach `"issues": {` einfügen** (mit Komma dahinter; die Datei bleibt
gültiges JSON):

`en.json`
```json
    "weather_sensor_stale": {
      "title": "A weather sensor of {group} has stopped reporting",
      "description": "Irrigation Plus has not heard from {entities} since {since}. The last reported values are still used as if they were current, so zones that depend on them are calculated with those values until new ones arrive.\n\nCheck the device and its integration. If you replaced the device, select its new entities in the sensor group. If the value is meant to be fixed, use the \"Static value\" source instead. If the integration only updates every few hours, this notice appears between its updates and does not mean the sensor has failed.\n\nThis notice clears itself when the sensor reports again."
    },
```

`de.json`
```json
    "weather_sensor_stale": {
      "title": "Ein Wettersensor von {group} meldet nicht mehr",
      "description": "Irrigation Plus hat seit {since} nichts mehr von {entities} gehört. Die zuletzt gemeldeten Werte werden weiter verwendet, als wären sie aktuell; Zonen, die davon abhängen, werden damit berechnet, bis wieder Werte kommen.\n\nPrüfe das Gerät und seine Integration. Hast du das Gerät ersetzt, wähle seine neuen Entitäten in der Sensorgruppe. Soll der Wert fest sein, nutze stattdessen die Quelle „Fester Wert“. Aktualisiert die Integration nur alle paar Stunden, erscheint dieser Hinweis zwischen ihren Updates und bedeutet keinen Ausfall.\n\nDieser Hinweis verschwindet von selbst, sobald der Sensor wieder meldet."
    },
```

`es.json`
```json
    "weather_sensor_stale": {
      "title": "Un sensor meteorológico de {group} ha dejado de informar",
      "description": "Irrigation Plus no tiene noticias de {entities} desde {since}. Los últimos valores recibidos se siguen usando como si fueran actuales, así que las zonas que dependen de ellos se calculan con esos valores hasta que lleguen otros nuevos.\n\nRevisa el dispositivo y su integración. Si has sustituido el dispositivo, selecciona sus nuevas entidades en el grupo de sensores. Si el valor debe ser fijo, usa en su lugar la fuente «Valor estático». Si la integración solo se actualiza cada pocas horas, este aviso aparece entre sus actualizaciones y no significa que el sensor haya fallado.\n\nEste aviso desaparece solo cuando el sensor vuelve a informar."
    },
```

`fr.json`
```json
    "weather_sensor_stale": {
      "title": "Un capteur météo de {group} n’envoie plus de mesures",
      "description": "Irrigation Plus n’a plus de nouvelles de {entities} depuis {since}. Les dernières valeurs reçues restent utilisées comme si elles étaient actuelles : les zones qui en dépendent sont calculées avec ces valeurs jusqu’à l’arrivée de nouvelles mesures.\n\nVérifiez l’appareil et son intégration. Si vous avez remplacé l’appareil, sélectionnez ses nouvelles entités dans le groupe de capteurs. Si la valeur doit rester fixe, utilisez plutôt la source « Valeur statique ». Si l’intégration ne se met à jour qu’à quelques heures d’intervalle, cet avis apparaît entre ses mises à jour et ne signifie pas que le capteur est en panne.\n\nCet avis disparaît de lui-même dès que le capteur envoie de nouveau des mesures."
    },
```

`it.json`
```json
    "weather_sensor_stale": {
      "title": "Un sensore meteo di {group} ha smesso di inviare dati",
      "description": "Irrigation Plus non riceve notizie da {entities} dal {since}. Gli ultimi valori ricevuti continuano a essere usati come se fossero attuali, quindi le zone che ne dipendono vengono calcolate con questi valori finché non ne arrivano di nuovi.\n\nControlla il dispositivo e la sua integrazione. Se hai sostituito il dispositivo, seleziona le sue nuove entità nel gruppo di sensori. Se il valore deve restare fisso, usa invece la sorgente «Valore statico». Se l’integrazione si aggiorna solo ogni poche ore, questo avviso compare tra un aggiornamento e l’altro e non significa che il sensore sia guasto.\n\nQuesto avviso scompare da solo quando il sensore torna a inviare dati."
    },
```

`nl.json`
```json
    "weather_sensor_stale": {
      "title": "Een weersensor van {group} meldt niets meer",
      "description": "Irrigation Plus heeft sinds {since} niets meer van {entities} gehoord. De laatst gemelde waarden worden nog steeds gebruikt alsof ze actueel zijn, dus zones die ervan afhangen worden met die waarden berekend tot er nieuwe binnenkomen.\n\nControleer het apparaat en de integratie ervan. Heb je het apparaat vervangen, kies dan de nieuwe entiteiten ervan in de sensorgroep. Moet de waarde vast zijn, gebruik dan de bron ‘Vaste waarde’. Werkt de integratie maar om de paar uur bij, dan verschijnt deze melding tussen haar updates en betekent ze niet dat de sensor defect is.\n\nDeze melding verdwijnt vanzelf zodra de sensor weer meldt."
    },
```

`no.json`
```json
    "weather_sensor_stale": {
      "title": "En værsensor i {group} har sluttet å rapportere",
      "description": "Irrigation Plus har ikke hørt fra {entities} siden {since}. De sist rapporterte verdiene brukes fortsatt som om de var aktuelle, så soner som er avhengige av dem, beregnes med disse verdiene til nye kommer inn.\n\nSjekk enheten og integrasjonen. Har du byttet ut enheten, velg de nye entitetene i sensorgruppen. Hvis verdien skal være fast, bruk heller kilden «Statisk verdi». Oppdateres integrasjonen bare med noen timers mellomrom, vises denne meldingen mellom oppdateringene og betyr ikke at sensoren har sviktet.\n\nDenne meldingen forsvinner av seg selv når sensoren rapporterer igjen."
    },
```

`sk.json`
```json
    "weather_sensor_stale": {
      "title": "Meteorologický senzor skupiny {group} prestal hlásiť hodnoty",
      "description": "Irrigation Plus od {since} nedostal nič od {entities}. Naposledy nahlásené hodnoty sa naďalej používajú, akoby boli aktuálne, takže zóny, ktoré od nich závisia, sa počítajú s týmito hodnotami, kým neprídu nové.\n\nSkontroluj zariadenie a jeho integráciu. Ak si zariadenie vymenil, vyber jeho nové entity v skupine senzorov. Ak má byť hodnota pevná, použi namiesto toho zdroj „Statická hodnota“. Ak sa integrácia aktualizuje len raz za niekoľko hodín, toto upozornenie sa zobrazuje medzi jej aktualizáciami a neznamená poruchu senzora.\n\nToto upozornenie zmizne samo, keď senzor znova začne hlásiť hodnoty."
    },
```

Die Quellen-Namen sind die Panel-Beschriftungen aus
`frontend/localize/languages/*.json` → `panels.mappings.cards.mapping.sources.static`.

- [ ] **Step 4: GREEN prüfen**

Run: `TZ=UTC … -m pytest tests/test_sensor_liveness.py tests/test_i18n_completeness.py -p _local_socket_unblock -q`
Expected: alles grün (die i18n-Tests prüfen fehlende/verwaiste Schlüssel, gleiche Platzhalter, keine
unübersetzten Werte, keine URL, kein `fix_flow` neben `description`).

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/translations tests/test_sensor_liveness.py
git commit -F - <<'EOF'
feat(liveness): the repair notice in all eight languages

Names the group, the silent entities with their fields and since when; says that
the last reported values are still used as if they were current; points at the
device, its integration, the sensor group for a replaced device and the "Static
value" source; says that an integration updating only every few hours raises it
between its updates; clears itself when the sensor reports again.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 13: Doku-Abschnitt, Event-Doku und Docstring

**Files:**
- Modify: `docs/configuration-sensor-groups.md` (neuer Abschnitt vor `## Deleting a sensor group`, `docs/configuration-sensor-groups.md:54`), `docs/usage-events.md` (Tabelle, nach der Zeile `irrigation_plus_zone_problem`, `docs/usage-events.md:20`), `custom_components/irrigation_plus/calculation.py` (Docstring `_prune_mapping_buffer`, `calculation.py:432-446`)

Keine Verhaltensänderung, daher kein neuer Test; geprüft wird per Lesen und durch die volle Suite in Task 14.

- [ ] **Step 1: Abschnitt „When a sensor goes silent“** (JustChr: der Fehlalarm bei einer 6-h-Cloud-Abfrage gehört in
die Doku) — in `docs/configuration-sensor-groups.md` direkt vor der Zeile `## Deleting a sensor group` einfügen,
gefolgt von einer Leerzeile:

```markdown
## When a sensor goes silent
Irrigation Plus checks every five minutes whether the sensors of a sensor group still report. What counts is a sensor's Home Assistant device: as long as any entity of that device reports, a value that merely stays the same, such as a rain gauge on a dry day, counts as alive. A sensor without a device counts for itself. A sensor whose state is `unavailable` or `unknown` counts as silent whatever its device does. Values from an `input_number` helper never count as silent.

Once a sensor has not reported for three hours, Irrigation Plus shows a repair notice for its sensor group and fires the `irrigation_plus_weather_stale` event (see [Events](usage-events.md)). When the sensor reports again, the notice clears itself and a second event marks the end. Meanwhile the calculation keeps using the sensor's last value.

The three hours are fixed. An integration that updates less often, such as a cloud service polled every six hours, therefore raises the notice between its updates even though nothing has failed.

A template sensor without a device whose value never changes looks silent too. If a value is meant to be fixed, use the "Static value" source instead.
```

Die Absätze stehen je auf einer Zeile, wie im Rest der Datei.

- [ ] **Step 2: Event-Zeile einfügen** (nach der `zone_problem`-Zeile)

```markdown
|`irrigation_plus_weather_stale`|When a weather sensor of a sensor group has not reported for three hours, and again when it reports again. Its HA device counts: while any entity of that device reports, a quiet value such as a rain gauge on a dry day is not stale. Carries `mapping_id`, `mapping`, `entity_id`, `device_id` (null without a device), `fields`, `since` (its last sign of life), `until` (null while it is silent) and `stale` (true when the outage starts, false when it ends; also false when a silent sensor stops being tracked because it was replaced in its sensor group, the group was deleted or the weather data was reset). A repair issue is shown for as long as the sensor stays silent.|
```

- [ ] **Step 3: Docstring berichtigen** — in `_prune_mapping_buffer` die Sätze

```
        Keeps everything after the oldest enabled-zone watermark (so no zone
        loses unconsumed data) plus, PER FIELD, the boundary reading just before
        it (each field's delta/Riemann baseline), and hard-drops anything older
        than the retention cap. Disabled zones do not hold the buffer.
```

ersetzen durch

```
        Keeps everything after the oldest enabled-zone watermark (so no zone
        loses unconsumed data) plus, PER FIELD, the boundary reading just before
        it (each field's delta/Riemann baseline), whatever that reading's age:
        the retention cap only moves the cutoff, so a field that has been silent
        for longer than the cap keeps its last row. Whether that row is still a
        measurement is not this function's call; the sensor-liveness ledger
        (sensor_liveness) records when a sensor fell silent. Disabled zones do
        not hold the buffer.
```

- [ ] **Step 4: Commit**

```bash
git add docs/configuration-sensor-groups.md docs/usage-events.md custom_components/irrigation_plus/calculation.py
git commit -F - <<'EOF'
docs(liveness): when a sensor goes silent; the weather_stale event; the prune keeps a silent field's last row

The sensor-group page explains the check: the device counts, three hours,
the notice and the event, and that the last value is still used. The three
hours are fixed, so an integration that updates less often, such as a cloud
service polled every six hours, raises the notice between its updates; the
page says so. The event table gains irrigation_plus_weather_stale. The prune's
docstring said rows older than the retention cap are hard-dropped; a field's
boundary row is kept whatever its age, which the docstring now says, and why
that is the liveness ledger's concern.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 14: Lint, volle Suite, Mutationen, Review

**Files:** keine neuen.

- [ ] **Step 1: Lint** (CLAUDE.md, verbatim)

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black tests/test_sensor_liveness.py tests/test_sensor_liveness_store.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_repair.py
git status --short
```

Expected: `ruff` „All checks passed!“; hat `black` umformatiert, die Dateien prüfen und als
`style: black` committen. Die Testdateien prüft die CI nicht; die Snippets dieses Plans sind schon black-formatiert
(im Probelauf: „left unchanged“).

- [ ] **Step 2: Volle Suite, Namensvergleich gegen die Baseline aus Task 0**

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-after.txt 2>&1
tr '\r' '\n' < ../suite-after.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-after.txt
diff ../names-baseline.txt ../names-after.txt && echo "identical"
tail -c 400 ../suite-after.txt
```

Expected: `identical`; `passed` um genau die neuen Tests höher (zählen:
`TZ=UTC … -m pytest tests/test_sensor_liveness*.py -p _local_socket_unblock --collect-only -q | tail -1` → 75).
Im Probelauf auf `e9c79ec4`: 7 failed / 3618 → **3693** passed / 9 skipped / 415 errors, 422 Namen identisch.

- [ ] **Step 3: Mutationen auf die tragenden Wächter** — je Zeile die Änderung von Hand setzen, **alle vier**
Testdateien laufen lassen, Ergebnis notieren, mit `git checkout -- <datei>` zurücknehmen. Jede Mutation muss mindestens
einen Test rot machen, und der Lauf muss Tests gesammelt haben (Summenzeile „N failed, M passed“, kein Sammelfehler); ein
Überlebender heißt zuerst: Test zu schwach (Memory `mutation-survivor-suspects-the-test`). Automatisiert:
`python D:/Entwicklung/HASI/issue8-work/probe_mutate2.py <worktree>` (stellt jede Datei wieder her, auch nach einem Hänger).

| # | Mutation (in `sensor_liveness.py`, sofern nicht anders genannt) | Rot im Probelauf (2026-10-04) |
|---|---|---|
| 1 | `last_sign_of_life`: Zeile `candidates.extend(s.reported for s in siblings if s.valid)` löschen | `test_the_device_vouches_for_a_quiet_field`, `test_a_steady_rain_gauge_on_a_living_station_stays_quiet` |
| 2 | `last_sign_of_life`: `if own is not None and own.valid:` → `if own is not None:` | `test_an_unavailable_entity_is_silent_…`, `test_an_outage_spanning_a_restart_keeps_its_start`, `test_the_notice_survives_a_restart_…` |
| 3 | `advance_outages`: `now - seen.last > stale_after` → `>=` | `test_silence_up_to_the_limit_is_bridged` |
| 4 | `advance_outages`: `now - outage.end <= retention` → `<` | `test_closed_outages_older_than_the_retention_are_dropped` |
| 5 | `advance_outages`: `end = back if … else seen.last` → `end = seen.last` | `test_a_new_sign_closes_it_at_the_first_report` und zwei Koordinator-Tests |
| 6 | `const.SENSOR_LIVENESS_EXEMPT_DOMAINS = ()` (in `const.py`) | `test_a_value_set_by_hand_is_never_watched`, `test_a_value_set_by_hand_never_goes_stale` |
| 7 | `_on_has_clock`: `dt_util.as_local(stamp)` → `stamp` | `test_state_stamps_land_on_has_clock` und 8 weitere, darunter alle drei Hinweis-Tests |
| 8 | `_async_sensor_liveness_tick`: die Karenz-Rückkehr löschen | `test_the_check_waits_out_the_startup_grace` |
| 9 | `_async_check_mapping_liveness`: `if last is None: last = now` löschen | `test_an_entity_never_seen_starts_its_bridge_…` |
| 10 | `__init__.py`: `self._retire_outages(before)` im Quellwechsel löschen | `test_a_source_change_empties_the_ledger_…` |
| 11 | `calculation.py`: die zwei Ledger-Schlüssel im Reset löschen | `test_reset_all_weather_data_empties_the_ledger` |
| 12 | `store.py`: im Setter zusätzlich `self.async_schedule_save()` | `test_refreshing_the_signs_schedules_no_write` |
| 13 | `async_check_sensor_liveness`: `try/except` entfernen | `test_one_broken_group_does_not_stop_the_others` |
| 14 | `_retire_outages`: `if not silent: return` löschen | `test_a_group_without_an_open_outage_leaves_the_registry_alone` |
| 15 | `advance_outages`: den Zweig `if seen is None:` (Ende jetzt) löschen | `test_an_outage_of_an_entity_no_longer_watched_ends_now`, `test_an_outage_left_by_another_path_…` |
| 16 | `_retire_outages`: die Schleife mit `_fire_weather_stale` löschen | Quellwechsel-, Lösch- und Reset-Test, `test_the_notice_goes_when_its_sensor_group_is_deleted` |
| 17 | `_async_check_mapping_liveness`: `if opened or closed:` → `if opened:` (Erholung räumt den Hinweis nicht) | `test_the_notice_clears_when_the_sensor_reports_again` und drei Koordinator-Tests |
| 18 | `async_setup_sensor_liveness`: den `_sync_stale_issue`-Aufruf in der Schleife löschen (Neustart) | `test_the_notice_survives_a_restart_…`, `test_setup_shows_a_still_open_outage_at_once` |
| 19 | `__init__.py`: `self._retire_outages(res)` im Lösch-Zweig löschen | `test_the_notice_goes_when_its_sensor_group_is_deleted`, `test_deleting_a_group_drops_its_notice` |
| 20 | `store.py`: `sensor_outages=…` im Lade-Pfad löschen (Liste kommt nach dem Neustart nicht zurück) | `test_outages_and_signs_survive_a_restart`, `test_the_notice_survives_a_restart_…` |

Runner mit Zeitgrenze (eine Mutation kann einen Test hängen lassen): bei Bedarf
`timeout 300 TZ=UTC … -m pytest <datei> -p _local_socket_unblock -q -x`; hängt er, unter Windows
`taskkill /T /F /PID <pid>`.

- [ ] **Step 4: Review** — `superpowers:requesting-code-review` über den Diff `upstream/master..HEAD` mit Spec und
diesem Plan; Rückmeldungen über `superpowers:receiving-code-review` prüfen.

- [ ] **Step 5: Stand festhalten** — `docs/SESSION-STAND.md` ergänzen (Abschnitt mit Datum), Häkchen in diesem Plan
setzen. Weiter mit Task 15.

---

### Task 15: Pre-Release und Live-Test auf HA-Test

**Files:** keine Codeänderung. Belege nach `D:\Entwicklung\HASI\issue8-work\livetest\`.

Prüft das Ende-zu-Ende-Kriterium der Spec (*PR 1, HA-Test*, Schritte 1–5). **Mittel:** MQTT-Sensoren per YAML unter
dem eigenen Topic-Präfix `hasi_livetest/`, **ohne Discovery**. Hintergrund: Die MQTT-Integration von HA-Test hängt am
Broker von HA-Prod (Titel des Config-Entrys, gelesen 2026-10-04). Discovery-Nachrichten könnten deshalb auf HA-Prod
Geräte anlegen; Nachrichten unter `hasi_livetest/` abonniert HA-Prod dagegen nicht. HA-Test hat weder Packages noch
einen `mqtt:`-Schlüssel in der `configuration.yaml` (gelesen 2026-10-04); der Testblock lässt sich also sauber
hinzufügen und wieder entfernen. **Alles hier betrifft nur HA-Test; HA-Prod bleibt unberührt.** Mittel vom User
freigegeben am 2026-10-04 (Variante 1).

- [ ] **Step 1: Basis prüfen**

```bash
cd /d/Entwicklung/HASI/issue8-work/wt
git fetch upstream
git rev-list --count HEAD..upstream/master
```

Expected: `0`. Sonst: Upstream-Runde (Memory `upstream-sweep-first`), den noch nicht gepushten Branch auf
`upstream/master` rebasen und Task 14 Steps 1–3 wiederholen.

- [ ] **Step 2: production-Pre-Release** (Freigabe im Chat vorher; Rezept: CLAUDE.md *Produktiv-Rebuild/-Release* und
Memory `hasi-production-on-upstream`, Schnellweg per Cherry-Pick)

Delta = `upstream/master` + JustChr#189 (solange offen) + die Commits dieses Branches + Branding-Commit + Build-Commit.
Version `vJJJJ.MM.TTb1` (Datum des Baus) in `manifest.json` und `const.py` (mit `v`), in `frontend/package.json`
ohne; dist mit Node 24 bauen, mit `git add -f` stagen, Dateizahl prüfen. Prüfen, bevor etwas nach außen geht:

```bash
git rev-list --count HEAD..upstream/master                                         # 0
grep -c "https://github.com" custom_components/irrigation_plus/translations/en.json  # 0
```

Suite mit Namensvergleich gegen die Baseline des Rebuild-Basis-Commits. Release `--prerelease`, `--target production`,
Titel mit Beschreibung, englische Kurznotiz ohne IP und ohne Issue-Verweise. ZIP aus dem **SHA**, nie aus dem Tag-Namen;
vor dem Upload:

```bash
unzip -p irrigation_plus.zip sensor_liveness.py | grep -c "class SensorLivenessMixin"   # 1
```

Installation auf **HA-Test** per HACS (`update_information`, dann `download` mit `version`; `repository_id` als
`"Eifel-Joe/HAsmartirrigation"`), Neustart von HA-Test ankündigen und ausführen. Danach: Integration `loaded`,
Version = Pre-Release, Log ohne Fehler von `irrigation_plus`.

- [ ] **Step 3: Testaufbau auf HA-Test** (ankündigen; HA-Test ist Wegwerf)

Drei MQTT-Geräte in der `configuration.yaml` von HA-Test (`ha_config_set_yaml`, `yaml_path: mqtt`, `action: add`,
Vorschau prüfen, dann mit Token anwenden; danach Dienst `mqtt.reload`):

```yaml
sensor:
  - name: Livetest A Temperature
    unique_id: hasi_livetest_a_temperature
    state_topic: hasi_livetest/a/temperature
    unit_of_measurement: "°C"
    device_class: temperature
    device:
      identifiers: [hasi_livetest_a]
      name: HASI Livetest A
  - name: Livetest B Temperature
    unique_id: hasi_livetest_b_temperature
    state_topic: hasi_livetest/b/temperature
    unit_of_measurement: "°C"
    device_class: temperature
    device:
      identifiers: [hasi_livetest_b]
      name: HASI Livetest B
  - name: Livetest C Temperature
    unique_id: hasi_livetest_c_temperature
    state_topic: hasi_livetest/c/temperature
    unit_of_measurement: "°C"
    device_class: temperature
    device:
      identifiers: [hasi_livetest_c]
      name: HASI Livetest C
  - name: Livetest C Humidity
    unique_id: hasi_livetest_c_humidity
    state_topic: hasi_livetest/c/humidity
    unit_of_measurement: "%"
    device_class: humidity
    device:
      identifiers: [hasi_livetest_c]
      name: HASI Livetest C
```

Rollen: **A** schweigt und kehrt zurück (Erholung, Neustart). **B** schweigt, seine Gruppe wird gelöscht. **C** meldet
durchgehend denselben Wert (MQTT schreibt bei jeder Nachricht, `last_reported` rückt vor), und seine Feuchte meldet nur
einmal: ein ruhiges Feld an einem lebenden Gerät. Damit sind beide Schreibweisen aus Schritt 1 der Spec abgedeckt.

Sender als Automationen (`ha_config_set_automation`, HA-Test):
- `HASI Livetest A`: Auslöser `time_pattern` mit `minutes: "/1"`, Aktion `mqtt.publish` auf
  `hasi_livetest/a/temperature`, Nutzlast `"18.5"`.
- `HASI Livetest B`: dasselbe für `hasi_livetest/b/temperature`, Nutzlast `"17.0"`.
- `HASI Livetest C`: dasselbe für `hasi_livetest/c/temperature`, Nutzlast `"16.0"`.
- `HASI Livetest Event`: Auslöser Event `irrigation_plus_weather_stale`; Aktion `system_log.write` mit `level: warning`,
  `logger: hasi_livetest`, `message: "{{ trigger.event.data | tojson }}"`.

Einmalig: `mqtt.publish` auf `hasi_livetest/c/humidity`, Nutzlast `"80"`, `retain: true`. Retained, damit der Wert den
Neustart übersteht; danach wird nicht mehr gesendet.

Drei Sensorgruppen auf HA-Test über dieselbe HTTP-View, die das Panel beim Speichern nutzt
(`/api/irrigation_plus/mappings`, `websockets.py:229-272`). Der User meldet sich im Browser-Bereich bei HA-Test an
(Passwort nie selbst eingeben); dann in der Seite (bewährt, Memory `hasi-livetest-capability-boundary`):

```js
const hass = document.querySelector("home-assistant").hass;
const field = (entity, unit) => ({source: "sensor", sensorentity: entity, unit, aggregate: "average"});
await hass.callApi("POST", "irrigation_plus/mappings", {name: "Livetest A", mappings: {Temperature: field("sensor.livetest_a_temperature", "°C")}});
await hass.callApi("POST", "irrigation_plus/mappings", {name: "Livetest B", mappings: {Temperature: field("sensor.livetest_b_temperature", "°C")}});
await hass.callApi("POST", "irrigation_plus/mappings", {name: "Livetest C", mappings: {Temperature: field("sensor.livetest_c_temperature", "°C"), Humidity: field("sensor.livetest_c_humidity", "%")}});
```

Jede Antwort trägt die `id` der neuen Gruppe; die drei IDs notieren. Entity-IDs vorher per `ha_search` bestätigen. Keine
Zone nutzt diese Gruppen.

- [ ] **Step 4: Ablauf** (Zeiten in UTC notieren; Report-Zeiten nur per `ha_eval_template`, Memory
`mcp-last-reported-is-wrong`)

1. Nach mindestens 15 min Lauf (Karenz 10 min abgewartet) die Automationen **A und B ausschalten** (`automation.turn_off`).
   Zeitpunkt t1 und die letzten Report-Zeiten von A und B notieren.
2. **t1 + 3 h + bis zu 5 min:** Reparaturhinweise für „Livetest A“ und „Livetest B“ vorhanden (Einstellungen →
   Reparaturen; Wortlaut wie in Task 12), für „Livetest C“ keiner. Log: zwei `hasi_livetest`-Zeilen mit `stale: true` und
   `since` = letzte Report-Zeit, dazu die WARNING der Integration. Diagnose der Integration: zwei offene Einträge in
   `sensor_outages`. Dann `irrigation_plus.calculate_all_zones` → kein Fehler im Log (die Berechnung liest die Liste nicht).
3. **t1 + 3 h 10 min:** Neustart von HA-Test (ankündigen). Gleich nach dem Start, vor Ablauf der Karenz: beide Hinweise
   wieder da, `since` unverändert; die Diagnose zeigt dieselben Anfänge. „Livetest C“ bleibt ohne Hinweis, auch nach den
   ersten Prüfungen.
4. **t1 + 3 h 30 min:** Automation **A einschalten**. Spätestens 5 min nach der ersten Meldung: Hinweis „Livetest A“
   weg; Log-Zeile mit `stale: false` und `until` = erste Meldung; Diagnose: Eintrag mit diesem Ende.
5. **Danach:** Gruppe „Livetest B“ löschen — `await hass.callApi("POST", "irrigation_plus/mappings", {id: <B>, remove:
   true})`, derselbe Weg wie der Lösch-Knopf → ihr Hinweis ist weg; Log-Zeile mit `stale: false` für B.

Jede Abweichung stoppt den Test: erst `superpowers:systematic-debugging`, dann ein Fix nach TDD, dann Task 14 Steps 1–3
und dieser Task von vorn.

- [ ] **Step 5: Aufräumen** (HA-Test)

Gruppen „Livetest A“ und „Livetest C“ löschen (wie in Step 4.5); die vier Automationen löschen; den Schlüssel `mqtt` aus der
`configuration.yaml` entfernen (`ha_config_set_yaml`, `action: remove`) und `mqtt.reload`; retained Nachricht
leeren (`mqtt.publish` auf `hasi_livetest/c/humidity`, leere Nutzlast, `retain: true`). Danach `ha_search` nach
`livetest` → keine Entität und keine Automation mehr.

- [ ] **Step 6: Beleg** — `D:\Entwicklung\HASI\issue8-work\livetest\L-pr1.md`: Version, Zeiten, je Schritt die
beobachteten Hinweise, Log-Zeilen und Diagnose-Ausschnitte. Keine IP, kein Schlüssel.

---

### Task 16: PR an JustChr und Nachlauf

**Files:** Texte unter `D:\Entwicklung\HASI\issue8-work\texts\` (`pr1-de.md`, `pr1-en.md`, `comment-8-pr1.md`,
`issue42-pr1.md`).

- [ ] **Step 1: Upstream-Runde wiederholen** (lange Sitzungen überholen die eigene Runde; Memory `upstream-sweep-first`):
`gh api "repos/JustChr/HAsmartirrigation/issues?state=all&since=<letzter Blick>"` und
`gh api "repos/JustChr/HAsmartirrigation/issues/comments?since=<letzter Blick>"`; JustChr#188 neu lesen (nur das Konto
`JustChr` zählt, Memory `justchr-watchtower-bot-unreviewed`); Doppelarbeit ausschließen:
`gh pr list --repo JustChr/HAsmartirrigation --state all --search "sensor stale"`.

- [ ] **Step 2: Greps vor dem Push, gegated** (Memory `no-own-issue-refs-upstream`; erst das `!` hält die Kette an)

```bash
cd /d/Entwicklung/HASI/issue8-work/wt
! git diff upstream/master..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b" \
  && ! git log upstream/master..HEAD --format='%H%n%B' | grep -n "Eifel-Joe#" \
  && ! git grep -n "Eifel-Joe#" HEAD -- custom_components tests \
  && ! git diff upstream/master..HEAD | grep -nE "192\.168\.|api_key|apikey" \
  && echo "sauber"
```

Expected: `sauber`.

- [ ] **Step 3: PR-Text zur Freigabe** — erst deutsch, dann englisch im Chat zeigen. Aufbau `## Problem` / `## Fix` /
`## Testing`, Footer „🤖 Generated with [Claude Code](https://claude.com/claude-code)“. Inhalt: der Defekt in zwei Sätzen;
dieser PR ist der erste der drei, um die JustChr auf #188 gebeten hat (Erkennung, Ausfall-Liste, Reparaturhinweis, Event,
keine Änderung an der Rechnung); Erkennung über das Gerät; fest 3 h mit dem Doku-Satz zur 6-h-Abfrage; die drei
erbetenen Hinweis-Tests mit Namen; Live-Test auf einer Testinstanz; lokale Suite namensgleich mit `master`. Keine
Verweise auf unsere Issues, keine Branch-SHAs, keine IP. Keine Liste dessen, was nicht drin ist.

- [ ] **Step 4: Push und PR** (nach Freigabe)

```bash
git push -u origin fix/stale-weather-sensor
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/stale-weather-sensor \
  --title "feat(liveness): notice when a weather sensor stops reporting" \
  --body-file /d/Entwicklung/HASI/issue8-work/texts/pr1-en.md
```

Danach den PR binden (`get_status`, sonst `bind_pr`) und die CI lesen; kein eigenes Polling.

- [ ] **Step 5: P2** (Texte vorher zur Freigabe) — Kommentar auf Eifel-Joe#8 mit Link auf den PR, ein Satz zum Stand;
Label bleibt `upstream:freigegeben`. `Eifel-Joe#42` nachziehen. Der Feldtest auf HA-Prod beginnt erst mit dem Update auf
das Pre-Release, und das nur auf Zuruf des Users.

- [ ] **Step 6: P1** — Spec, dieser Plan und die Belege (`probe-2026-10-04.patch`, `probe_rev2.py`, `probe_mutate2.py`,
`mutate-1004.txt`, Namenslisten, `livetest/L-pr1.md`) nach `archive/design-history` (CLAUDE.md *Design-Historie
archivieren*).

- [ ] **Step 7: Übergabe** — `docs/SESSION-STAND.md` und Memory `hasi-dead-weather-sensor` nachziehen.

---

## Selbstprüfung gegen die Spec (Revision 2)

| Spec-Punkt | Task |
|---|---|
| R1 Erkennung je Gerät, eigene `unavailable`-Entität stumm, ohne Gerät eigene Entität, `input_number` nie tot | 2, 3, 8, 9 |
| R2 Grenze fest 3 h, bis dahin überbrückt | 1, 5 |
| R3 Ausfälle mitschreiben (Beginn/Ende), Lebenszeichen über Neustart | 4, 5, 7, 9 |
| Prüfung alle 5 min, 10 min Karenz, Abmelden beim Entladen | 10 |
| Liste begrenzt auf 7 Tage, ohne Store-Versionssprung | 1, 5, 7 |
| Leeren bei Quellwechsel, Reset; Hinweis weg beim Löschen | 11 |
| Panel-Speichern lässt die Liste stehen | 7 |
| R6 Hinweis (Laufzeit, Neustart), Event, Log, 8 Sprachen; kein Schnitt-Versprechen | 1, 2, 6, 9, 10, 12 |
| J4 drei Hinweis-Tests: Erholung, Neustart mitten im Ausfall, Löschen der Gruppe (echter Store, echte Registry) | 9, 10, 11 |
| J5 Doku: fest 3 h, Fehlalarm bei 6-h-Abfrage | 13 |
| Event-Doku, Docstring `_prune_mapping_buffer` | 13 |
| R7 nur Sensorfelder | 2 |
| R8 PR 1 ohne Verhaltensänderung | Rahmen; 14 (Suite namensgleich); 15 (Berechnung ohne Fehler) |
| Ende-zu-Ende PR 1 auf HA-Test, Schritte 1–5 | 15 |
| R4, R5 Einstellung, Schnitt, Erklärungssatz | **PR 2 und PR 3**, eigene Pläne |
| R9 Schnitt erst nach dem Feldtest | 16 (Feldtest nur auf Zuruf); Plan PR 2 |
