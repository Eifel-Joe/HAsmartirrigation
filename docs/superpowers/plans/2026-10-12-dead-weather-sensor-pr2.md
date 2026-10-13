# Stummer Wettersensor, PR 2 (Einstellung und Schnitt im Tagespfad) — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Eine Sensorgruppe auf *pausieren* bucht für die Zeit, in der ein Sensor stumm war, nichts mehr — im Commit
des Tagespfads, nur ohne Stundenrechnung; jede Gruppe auf *behalten* rechnet und erklärt byte-identisch wie heute.

**Architektur:** Zwei reine Funktionen in `sensor_liveness.py` machen aus der Ausfall-Liste von PR 1 die gesperrte Zeit
je Feld (`blocked_spans`) und den buchbaren Anteil (`valid_share`). Eine Gate-Methode im Rechen-Mixin entscheidet je
Zone, ob geschnitten wird, und reicht die Sperren als optionales Schlüsselwort `blocked=` an Aggregat, Modulrechnung und
die zwei Aufzeichnungen. Das Aggregat bleibt das flache Dict. Dazu: die Einstellung `on_silent_sensor` an der
Sensorgruppe (Store, View, Panel), eine Hinweis-Variante und zwei Sätze in der Berechnungs-Erklärung.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über `pytest-homeassistant-custom-component`,
`attrs`; Frontend TypeScript/Lit, vitest, rollup (Node 24).

**Spec:** `docs/superpowers/specs/2026-10-11-dead-weather-sensor-pr2-design.md` (freigegeben 2026-10-12) und, für
alles, was sie nicht neu entscheidet, `docs/superpowers/specs/2026-10-03-dead-weather-sensor-design.md` (Revision 3).
Zitiert als „Spec PR 2 §N“ bzw. „Rev. 3“.

**Freigabe:** Plan und die Wortlaute (Panel Task 8, Hinweis Task 7, Erklärung Task 6, Doku Task 9) vom User
freigegeben am 2026-10-12, nach dem Probelauf; Ausführung **subagent-driven** in einer frischen Sitzung.

**Probelauf (2026-10-12, gegen `6a40e083`):** Tasks 0–9 und Task 10 Steps 1–4 und 6, wörtlich nach diesem Plan, in
einem Wegwerf-Worktree (Sonnet-Agent; Zahlen von mir an den Ergebnisdateien nachgeprüft):
- **Alle Code-Snippets liefen ohne inhaltliche Korrektur**; jede RED- und GREEN-Erwartung traf. Einzige Korrektur:
  eine Testzeile in Task 8 musste für prettier umbrochen werden (hier schon berichtigt).
- **Volle Suite:** 7 failed / 3903 passed / 9 skipped / 458 errors gegen die Baseline 7 / 3819 / 9 / 430 desselben
  Commits; +84 passed = die berechneten 84 neuen Python-Fälle. FAILED-Namen identisch, kein Baseline-Name entfällt; die
  28 neuen ERROR-Namen sind alle Teardown-Fehler „Lingering timer“ aus `tests/test_silent_sensor_commit.py` (echter
  Koordinator, Test selbst grün; dasselbe lokale Muster wie bei `test_per_zone_consumption.py` in der Baseline).
- **22/22 Mutationen getötet**, jede vom in Task 10 genannten Killer. vitest: 2 neue Fälle grün; nach dem Bau ist
  `dist/` gleich dem committeten Stand. Greps auf eigene Bezüge leer.
- Berichtigt nach dem Probelauf: RED-Beschreibung Task 2, Testzeile und Bundle-Zahl Task 8, Kriterium Task 9,
  Vergleichskriterien Task 10 (Lingering timer, ruff-Version).
- Getesteter Stand: `D:\Entwicklung\HASI\issue8-pr2-work\probe\probe-2026-10-12.patch` (36 Dateien, +2612/−935),
  Protokolle `steps.md`, `deviations.md`, `mutate-pr2.txt` daneben. **Weicht ein Snippet dieses Plans vom Patch ab,
  gilt der Patch**; die Abweichung dann im Plan berichtigen.

## Global Constraints

- Basis `upstream/master` = `6a40e083`; alle Zeilenangaben dort, in `custom_components/irrigation_plus/`.
- Kein Store-Versionssprung (`STORAGE_VERSION = 14`, `STORAGE_MINOR_VERSION = 2` bleiben).
- Werte der Einstellung: genau `"keep"` und `"pause"`; Schlüssel `"on_silent_sensor"`; Hinweis-Schlüssel
  `"weather_sensor_stale_paused"`; Erklärungsschlüssel `module.calculation.explanation.sensor-outage` und
  `module.calculation.explanation.sensor-outage-share`.
- Sperre = `[start + 3 h, end)`, halboffen; offener Eintrag bis `now` des Commits.
- Mit `blocked=None` läuft in `aggregate_window`, `calculate_module` und den Aufzeichnungen kein neuer Code.
- Zeiten im Erklärungssatz `%Y-%m-%d %H:%M` auf HAs Uhr; Anteil in ganzen Prozent (`f"{share * 100:.0f}"`).
- Neue UI-Strings in allen 8 Sprachen (`de en es fr it nl no sk`), Platzhalter je Sprache gleich.
- Keine Verweise auf Fork-Issues, Spec-/Plan-Kürzel oder „PR 2/PR 3“ in Code, Tests, Doku, Commit-Messages.
- Lint nur `uvx black` + `uvx ruff check` auf `custom_components/irrigation_plus/` (ruff prüft auch die
  Import-Reihenfolge, Regel `I`).

## Review Focus

- **Ausfall-Liste mit Offset-Stempeln** (von Hand editiert oder von einem anderen Build): Der Commit darf nicht mit
  „can't compare offset-naive and offset-aware“ abbrechen; erwartet wird derselbe Schnitt wie mit naiven Stempeln
  (Test in Task 4).
- **Pufferzeilen hinter `now`** (Uhrversatz): `_window_bounds` verlängert das Fenster; die Zeit hinter `now` zählt
  als gültig, nichts wirft (Test in Task 3).
- **Static-Zone in einer pausierenden Gruppe:** Ihre Buchung ändert sich nicht, Satz 2 erscheint nicht (Test in
  Task 5).
- **Zone ohne Sensorgruppe oder mit gelöschter Gruppe:** Das Gate liefert `None`, die Rechnung läuft wie heute
  (Test in Task 4).
- **Ausfall eines Feldes ohne Zeilen im Fenster** (Feld nicht mehr gemappt, oder nie gemeldet): kein Fehler, kein
  erfundener Wert (Test in Task 3).

---

## Rahmen

- **Dieser Plan ist PR 2 von dreien.** PR 1 (Erkennung, Ausfall-Liste, Hinweis, Event) ist gemergt (`7001c754`) und
  auf HA-Prod feldgetestet; PR 3 (Stundenpfad, Live-Schätzung) bekommt einen eigenen Plan.
- **Liefer-Reihenfolge:** Tasks 0–9 im Worktree → Task 10 Lint, volle Suite, Mutationen, Review → Task 11
  production-Pre-Release und Live-Test auf HA-Test → Task 12 PR an JustChr und Nachlauf. Alles, was nach außen geht
  (Push, Release, PR, Kommentare, Issue-Änderungen), nur nach Freigabe im Chat; Texte vorher zeigen, deutsch, dann
  englisch. Vor jedem Außen-Schritt eine Upstream-Runde (Memory `upstream-sweep-first`).
- **Basis:** Hat sich `upstream/master` bis Task 0 bewegt, jede Anker-Stelle per `grep -n` neu suchen (die Anker sind
  zitiert) und die Baseline auf dem neuen Commit messen.
- **Testbefehl** (aus dem Worktree; dort gibt es kein eigenes `.venv`):
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **„Grün“ lokal:** Tests mit einem echten `SmartIrrigationCoordinator` enden in der lokalen Env mit einem
  Teardown-ERROR „Lingering timer“, auch wenn der Test bestanden hat (Vorbestand, z. B. `test_per_zone_consumption.py`,
  `test_window_amplitude.py`; Memory `hasi-local-test-env-rebuild`). Das trifft auch `tests/test_silent_sensor_commit.py`.
  „Alle grün“ heißt in den Schritten dieses Plans: kein FAILED, ERRORs nur dieser Art, jede neue Testfunktion
  `passed`.
- **Frontend:** `cd custom_components/irrigation_plus/frontend && npm ci` einmal; Tests `npx vitest run <datei>`;
  Bau `npm run build` (Lint + Rollup). Die 4 Bundles in `dist/` sind getrackt, `dist/` ist ignoriert → `git add -f`,
  danach die Dateizahl prüfen (Projekt-`CLAUDE.md`).
- **Uhr:** Puffer-Stempel, Ausfall-Stempel, Wasserzeichen und `now` sind naiv auf HAs Uhr. In den Tests ist HAs Zone
  US/Pacific (autouse `hass`), die Prozesszone per `TZ=UTC` UTC. Die neuen Tests übergeben naive Zeiten direkt.
- **Commit-Messages** englisch, WAS und WARUM, Schluss `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`;
  mehrzeilig per `git commit -F - <<'EOF' … EOF`.

## Dateien

| Datei | Verantwortung |
|---|---|
| `custom_components/irrigation_plus/const.py` | Schlüssel und Werte der Einstellung, Hinweis-Variante |
| `custom_components/irrigation_plus/sensor_liveness.py` | `group_pauses`, `blocked_spans`, `valid_share`; Hinweis-Variante, Log-Text, Re-Sync |
| `custom_components/irrigation_plus/store.py` | `MappingEntry.on_silent_sensor`, Laden mit Rückfall `keep` |
| `custom_components/irrigation_plus/weather_aggregate.py` | `aggregate_window(…, blocked=)`: Felder nur in gültiger Zeit |
| `custom_components/irrigation_plus/calculation.py` | Gate `_blocked_spans_for_zone`, Transport, Anteil, `s = 0`, Aufzeichnungen, Erklärungssätze |
| `custom_components/irrigation_plus/__init__.py` | Re-Sync des Hinweises bei Wechsel der Einstellung und der Stundenrechnung |
| `custom_components/irrigation_plus/websockets.py` | Mapping-View nimmt `on_silent_sensor` an |
| `custom_components/irrigation_plus/live_estimate.py` | nur Kommentare („exactly as“) |
| `custom_components/irrigation_plus/translations/*.json` (8) | Hinweis `weather_sensor_stale_paused` |
| `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) | Erklärungssätze, Panel-Auswahl |
| `custom_components/irrigation_plus/frontend/src/types.ts` | `SmartIrrigationMapping.on_silent_sensor` |
| `custom_components/irrigation_plus/frontend/src/views/mappings/view-mappings.ts` | Auswahl in der Gruppenkarte, Speichern |
| `custom_components/irrigation_plus/frontend/dist/*.js` (4) | neu gebaut |
| `docs/configuration-sensor-groups.md` | Abschnitt „When a sensor goes silent“ |
| neu: `tests/test_sensor_liveness_blocked.py` | reine Funktionen |
| neu: `tests/test_silent_sensor_setting.py` | Einstellung im echten Store |
| neu: `tests/test_weather_aggregate_blocked.py` | Aggregation unter Masken |
| neu: `tests/test_silent_sensor_commit.py` | Gate, Transport, Aufzeichnungen, Buchen, Erklärung, Byte-Identität |
| `tests/test_sensor_liveness_coordinator.py` | neue Klasse für Hinweis-Variante, Log, Re-Sync |
| `tests/test_run_in_flight.py` | Fake-Store bekommt `get_mapping` (Task 4) |
| `frontend/src/views/mappings/view-mappings-save.test.ts` | Speichern trägt die Einstellung |

---

### Task 0: Arbeitsumgebung und Baseline

**Files:** keine Codeänderung.

- [x] **Step 1: Upstream-Runde und Basis prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git rev-parse --short=8 upstream/master
```

Erwartet: `6a40e083`. Sonst: Upstream-Runde nach Memory `upstream-sweep-first`, dem User melden, die Anker dieses Plans
auf dem neuen Commit neu suchen.

- [x] **Step 2: Worktree von `upstream/master` anlegen** (ohne Tracking, Memory `hasi-pr-build-recipe`)

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree add --no-track -b feat/pause-silent-weather-sensor /d/Entwicklung/HASI/issue8-pr2-work/wt upstream/master
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue8-pr2-work/wt/
cd /d/Entwicklung/HASI/issue8-pr2-work/wt && git log --oneline -1
```

- [x] **Step 3: Baseline der vollen Suite** (Memory `rebaseline-when-the-base-moves`)

```bash
cd /d/Entwicklung/HASI/issue8-pr2-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-baseline.txt 2>&1
tr '\r' '\n' < ../suite-baseline.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-baseline.txt
tail -c 400 ../suite-baseline.txt
```

Erwartet: Zusammenfassung mit `failed`/`passed`/`skipped`/`errors` (die Windows-Altlasten: Tests, die ein neueres HA
brauchen). Die Datei erst nach Laufende lesen. Zahlen in `../baseline.txt` notieren.

- [x] **Step 4: Frontend-Abhängigkeiten**

```bash
cd /d/Entwicklung/HASI/issue8-pr2-work/wt/custom_components/irrigation_plus/frontend && npm ci && npx vitest run src/views/mappings/view-mappings-save.test.ts
```

Erwartet: `7 passed`.

---

### Task 1: Konstanten und die reinen Funktionen

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (nach `ISSUE_WEATHER_SENSOR_STALE = "weather_sensor_stale"`, `:714`)
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (Modul-Docstring `:1-16`; neue Funktionen nach `outages_of`, `:166-171`)
- Test: `tests/test_sensor_liveness_blocked.py` (neu)

**Interfaces:**
- Produces: `const.MAPPING_ON_SILENT_SENSOR = "on_silent_sensor"`, `const.ON_SILENT_SENSOR_KEEP = "keep"`,
  `const.ON_SILENT_SENSOR_PAUSE = "pause"`, `const.ON_SILENT_SENSOR_OPTIONS`,
  `const.ISSUE_WEATHER_SENSOR_STALE_PAUSED = "weather_sensor_stale_paused"`;
  `group_pauses(mapping: dict) -> bool`;
  `blocked_spans(outages: list[Outage], start: datetime, end: datetime) -> dict[str, tuple[tuple[datetime, datetime], ...]]`;
  `valid_share(blocked: dict, fields, start: datetime, end: datetime) -> float`.

- [x] **Step 1: Failing test schreiben** — `tests/test_sensor_liveness_blocked.py`

```python
"""The time a pausing sensor group does not book: blocked spans and the share left."""

from datetime import datetime, timedelta

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.sensor_liveness import (
    Outage,
    blocked_spans,
    group_pauses,
    valid_share,
)

T0 = datetime(2026, 7, 1, 0, 0, 0)  # window start, naive on HA's clock
END = T0 + timedelta(hours=24)
H = timedelta(hours=1)


def _outage(start_h, end_h=None, fields=("Temperature",), entity="sensor.t"):
    return Outage(
        entity,
        "dev1",
        tuple(fields),
        T0 + start_h * H,
        None if end_h is None else T0 + end_h * H,
    )


class TestBlockedSpans:
    def test_the_first_three_hours_are_bridged(self):
        spans = blocked_spans([_outage(2, 10)], T0, END)
        assert spans == {"Temperature": ((T0 + 5 * H, T0 + 10 * H),)}

    def test_an_outage_of_three_hours_or_less_blocks_nothing(self):
        assert blocked_spans([_outage(2, 5)], T0, END) == {}
        assert blocked_spans([_outage(2, 4)], T0, END) == {}

    def test_an_open_outage_blocks_up_to_the_window_end(self):
        spans = blocked_spans([_outage(20)], T0, END)
        assert spans == {"Temperature": ((T0 + 23 * H, END),)}

    def test_spans_are_cut_to_the_window(self):
        assert blocked_spans([_outage(-10, 4)], T0, END) == {
            "Temperature": ((T0, T0 + 4 * H),)
        }
        assert blocked_spans([_outage(-10, -1)], T0, END) == {}
        assert blocked_spans([_outage(30)], T0, END) == {}

    def test_overlapping_outages_of_one_field_merge(self):
        spans = blocked_spans(
            [_outage(0, 10, entity="sensor.a"), _outage(6, 14, entity="sensor.b")],
            T0,
            END,
        )
        assert spans == {"Temperature": ((T0 + 3 * H, T0 + 14 * H),)}

    def test_separate_outages_stay_separate_and_sorted(self):
        spans = blocked_spans([_outage(10, 15), _outage(0, 5)], T0, END)
        assert spans == {
            "Temperature": ((T0 + 3 * H, T0 + 5 * H), (T0 + 13 * H, T0 + 15 * H))
        }

    def test_only_the_fields_the_outage_recorded_are_blocked(self):
        spans = blocked_spans(
            [_outage(0, 10, fields=("Dewpoint", "Humidity"))], T0, END
        )
        assert set(spans) == {"Dewpoint", "Humidity"}


class TestValidShare:
    def test_a_field_without_spans_is_valid_throughout(self):
        assert valid_share({}, ("Temperature",), T0, END) == 1.0

    def test_the_share_is_the_window_minus_the_span(self):
        blocked = {"Temperature": ((T0 + 6 * H, T0 + 12 * H),)}
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.75

    def test_two_fields_silent_at_different_hours_leave_their_intersection(self):
        blocked = {
            "Temperature": ((T0, T0 + 6 * H),),
            "Dewpoint": ((T0 + 12 * H, T0 + 18 * H),),
        }
        # Not min(0.75, 0.75): together they leave 12 of 24 hours.
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.5

    def test_overlapping_spans_count_once(self):
        blocked = {
            "Temperature": ((T0, T0 + 12 * H),),
            "Dewpoint": ((T0 + 6 * H, T0 + 12 * H),),
        }
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.5

    def test_fields_that_are_not_asked_for_do_not_count(self):
        blocked = {"Solar Radiation": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), T0, END) == 1.0

    def test_a_field_blocked_throughout_leaves_nothing(self):
        blocked = {"Temperature": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), T0, END) == 0.0

    def test_an_empty_window_is_not_cut(self):
        blocked = {"Temperature": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), END, END) == 1.0


class TestGroupPauses:
    def test_only_a_stored_pause_pauses(self):
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "pause"}) is True
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "keep"}) is False
        assert group_pauses({}) is False
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "PAUSE"}) is False
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_blocked.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'blocked_spans'`.

- [x] **Step 3: Konstanten** — in `const.py` direkt nach `ISSUE_WEATHER_SENSOR_STALE = "weather_sensor_stale"` einfügen:

```python
# The same notice for a group that pauses a silent sensor: its values are no
# longer used. Chosen while the daily form of the calculation is the one that
# cuts (see calculation._blocked_spans_for_zone).
ISSUE_WEATHER_SENSOR_STALE_PAUSED = "weather_sensor_stale_paused"
# What a sensor group does with a silent sensor (MappingEntry.on_silent_sensor):
# keep using its last value, as before, or pause it so that the silent time books
# nothing. A group stored without the key keeps; a new group pauses.
MAPPING_ON_SILENT_SENSOR = "on_silent_sensor"
ON_SILENT_SENSOR_KEEP = "keep"
ON_SILENT_SENSOR_PAUSE = "pause"
ON_SILENT_SENSOR_OPTIONS = (ON_SILENT_SENSOR_KEEP, ON_SILENT_SENSOR_PAUSE)
```

- [x] **Step 4: Reine Funktionen** — in `sensor_liveness.py` direkt nach `outages_of` (`:166-171`) einfügen:

```python
def group_pauses(mapping: dict) -> bool:
    """Whether a sensor group pauses a silent sensor rather than keep its last value.

    Anything but a stored ``pause`` keeps: a group written before the setting
    existed, a test double without it, or a value edited by hand.
    """
    return mapping.get(const.MAPPING_ON_SILENT_SENSOR) == const.ON_SILENT_SENSOR_PAUSE


def blocked_spans(
    outages: list[Outage], start: datetime, end: datetime
) -> dict[str, tuple[tuple[datetime, datetime], ...]]:
    """Each field's blocked time inside ``[start, end)``: where it is not measured.

    An outage blocks from its start plus ``STALE_AFTER`` -- the first hours are
    bridged with the last value, as they are for the notice -- up to its end,
    half-open so that the reading of the return counts. An open outage blocks up
    to ``end``. A field's spans are merged and cut to the window; a field left
    without a span is not listed, and only the fields an outage recorded are.
    """
    found: dict[str, list[tuple[datetime, datetime]]] = {}
    for outage in outages:
        lo = max(outage.start + STALE_AFTER, start)
        hi = min(outage.end if outage.end is not None else end, end)
        if hi <= lo:
            continue
        for field in outage.fields:
            found.setdefault(field, []).append((lo, hi))
    return {field: _merged(spans) for field, spans in found.items()}


def valid_share(blocked: dict, fields, start: datetime, end: datetime) -> float:
    """The part of ``[start, end)`` in which all ``fields`` are unblocked at once.

    The intersection of their valid times, not the smallest single share: two
    fields silent at different hours leave less than either alone. A field
    without spans is valid throughout; an empty window has nothing to cut.
    """
    length = (end - start).total_seconds()
    if length <= 0:
        return 1.0
    spans = _merged([span for field in fields for span in blocked.get(field, ())])
    gone = sum((hi - lo).total_seconds() for lo, hi in spans)
    return max(0.0, (length - gone) / length)


def _merged(spans) -> tuple[tuple[datetime, datetime], ...]:
    """Sorted spans with every overlap or touch joined into one."""
    merged: list[tuple[datetime, datetime]] = []
    for lo, hi in sorted(spans):
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return tuple(merged)
```

- [x] **Step 5: Modul-Docstring berichtigen** — in `sensor_liveness.py` den Absatz

```
Nothing here changes a calculation: a silent sensor's last value is still used, as
before. The outage record says when it fell silent and the notice tells the user.
```

ersetzen durch:

```
The outage record says when a sensor fell silent and the notice tells the user. A
group that keeps a silent sensor's last value calculates as before; for a group
that pauses it, ``blocked_spans`` turns the record into the time its daily
calculation does not book (calculation._blocked_spans_for_zone).
```

- [x] **Step 6: Test laufen lassen, er muss grün sein**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_blocked.py tests/test_sensor_liveness.py -p _local_socket_unblock -q`
Expected: alle grün (15 neue plus die bestehenden von `test_sensor_liveness.py`).

- [x] **Step 7: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_sensor_liveness_blocked.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness_blocked.py
git commit -F - <<'EOF'
feat(liveness): blocked time per field and the share left to book

A sensor group that pauses a silent sensor books nothing for the time the
sensor was not measured. These pure functions turn the outage record into
that time: blocked from three hours after the last sign of life up to the
return, half-open so the reading of the return counts, merged per field
and cut to the window; and the share of the window in which a set of
fields is measured at once, which is their intersection rather than the
smallest single share. Nothing calls them yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Die Einstellung an der Sensorgruppe

**Files:**
- Modify: `custom_components/irrigation_plus/store.py` (Import-Block `from .const import (` um `:130-142`; `MappingEntry` `:352-383`; Lade-Pfad `:1385-1405`; neue Funktion nach `_as_last_seen`, `:967-974`)
- Test: `tests/test_silent_sensor_setting.py` (neu)

**Interfaces:**
- Consumes: `const.MAPPING_ON_SILENT_SENSOR`, `ON_SILENT_SENSOR_*` (Task 1).
- Produces: `MappingEntry.on_silent_sensor: str` (Standard `"pause"`); jeder Mapping-Dict aus dem Store
  (`get_mapping`, `async_get_mappings`, Diagnose, WS-Lesepfad) trägt `"on_silent_sensor"`.

- [x] **Step 1: Failing test schreiben** — `tests/test_silent_sensor_setting.py`

```python
"""The sensor group's setting for a silent sensor: keep its last value or pause it."""

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.store import STORAGE_KEY, SmartIrrigationStorage

KEY = const.MAPPING_ON_SILENT_SENSOR


async def _store(hass):
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    return store


async def _group(store):
    created = await store.async_create_mapping(
        {const.MAPPING_NAME: "Garden", const.MAPPING_MAPPINGS: {}}
    )
    return created[const.MAPPING_ID]


@pytest.mark.asyncio
async def test_a_group_created_now_pauses(hass) -> None:
    store = await _store(hass)
    assert store.get_mapping(await _group(store))[KEY] == "pause"


@pytest.mark.asyncio
async def test_the_group_of_the_first_setup_pauses(hass) -> None:
    store = await _store(hass)
    await store.set_up_factory_defaults()
    assert store.get_mapping(0)[KEY] == "pause"


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [None, "sometimes", 1, ["pause"]])
async def test_a_stored_group_without_a_valid_setting_keeps(
    hass, hass_storage, stored
) -> None:
    """An existing install must not change its calculation by itself, and a value
    edited by hand must not start cutting either."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_save()
    for mapping in hass_storage[STORAGE_KEY]["data"]["mappings"]:
        if stored is None:
            mapping.pop(KEY, None)
        else:
            mapping[KEY] = stored

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == "keep"


@pytest.mark.asyncio
async def test_a_group_carried_over_from_smart_irrigation_keeps(
    hass, hass_storage
) -> None:
    """The domain migration copies the old store byte for byte and reads it through
    this load path (test_migrate_domain::test_imports_the_legacy_store_verbatim).
    Smart Irrigation never wrote the setting, so its groups keep their last value."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_save()
    legacy = hass_storage[STORAGE_KEY]["data"]["mappings"][0]
    for key in (KEY, const.MAPPING_SENSOR_OUTAGES, const.MAPPING_SENSOR_LAST_SEEN):
        legacy.pop(key, None)

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == "keep"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["keep", "pause"])
async def test_a_stored_setting_survives_a_reload(hass, value) -> None:
    store = await _store(hass)
    group = await _group(store)
    await store.async_update_mapping(group, {KEY: value})
    await store.async_save()

    reloaded = await _store(hass)

    assert reloaded.get_mapping(group)[KEY] == value


@pytest.mark.asyncio
async def test_a_save_without_the_setting_leaves_it_alone(hass) -> None:
    """An older panel sends id, name and mappings only; what it omits stays."""
    store = await _store(hass)
    group = await _group(store)
    await store.async_update_mapping(group, {KEY: "keep"})

    await store.async_update_mapping(
        group, {const.MAPPING_NAME: "renamed", const.MAPPING_MAPPINGS: {}}
    )

    assert store.get_mapping(group)[KEY] == "keep"
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_setting.py -p _local_socket_unblock -q`
Expected: 10 FAIL — `KeyError: 'on_silent_sensor'` (das Feld gibt es noch nicht), bei den Tests, die es über
`async_update_mapping` setzen, `TypeError: MappingEntry.__init__() got an unexpected keyword argument
'on_silent_sensor'` (`attr.evolve`).

- [x] **Step 3: Import** — im Block `from .const import (` von `store.py` alphabetisch ergänzen: `MAPPING_ON_SILENT_SENSOR`
  (nach `MAPPING_NAME`), `ON_SILENT_SENSOR_KEEP`, `ON_SILENT_SENSOR_OPTIONS`, `ON_SILENT_SENSOR_PAUSE` (an ihrer
  alphabetischen Stelle). `uvx ruff check --fix custom_components/irrigation_plus/store.py` sortiert nach, falls nötig.

- [x] **Step 4: Feld** — in `MappingEntry` direkt nach `sensor_last_seen = attr.ib(type=dict, factory=dict)`:

```python
    # What the group does with a silent sensor: keep its last value or pause it
    # (const.ON_SILENT_SENSOR_*). A group created now pauses; a stored group
    # without the key keeps, which the load path sets (_as_on_silent_sensor).
    on_silent_sensor = attr.ib(type=str, default=ON_SILENT_SENSOR_PAUSE)
```

- [x] **Step 5: Laden** — im Lade-Pfad direkt nach

```python
                        sensor_last_seen=_as_last_seen(
                            mapping.get(MAPPING_SENSOR_LAST_SEEN)
                        ),
```

einfügen:

```python
                        on_silent_sensor=_as_on_silent_sensor(
                            mapping.get(MAPPING_ON_SILENT_SENSOR)
                        ),
```

und nach `_as_last_seen` die Funktion:

```python
def _as_on_silent_sensor(value) -> str:
    """Coerce a stored ``on_silent_sensor``; anything unknown keeps the last value.

    A group stored before the setting existed belongs to an existing install,
    whose calculation must not change by itself; a value edited by hand must not
    start cutting either. Only a group created now pauses (the attribute default).
    """
    return value if value in ON_SILENT_SENSOR_OPTIONS else ON_SILENT_SENSOR_KEEP
```

- [x] **Step 6: Test laufen lassen, er muss grün sein**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_setting.py tests/test_sensor_liveness_store.py tests/test_store.py -p _local_socket_unblock -q`
Expected: alle grün (10 neue Fälle).

- [x] **Step 7: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_silent_sensor_setting.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/store.py tests/test_silent_sensor_setting.py
git commit -F - <<'EOF'
feat(store): a sensor group says what to do with a silent sensor

The new field is either keep, the behaviour so far, or pause, which the
calculation will use to book nothing for a silent sensor's time. A group
created now pauses; a stored group without the field, a group carried
over from Smart Irrigation, and any value that is not one of the two
keep, so an existing install does not change its calculation by itself.
No storage version change, as with the outage record.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---
### Task 3: Aggregation unter Masken

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (Imports `:31-35`; `aggregate_window` `:321-409`; `_aggregate` `:501-575`; neue Funktionen direkt nach `_aggregate`, vor `class WaterStep`)
- Test: `tests/test_weather_aggregate_blocked.py` (neu)

**Interfaces:**
- Produces: `aggregate_window(readings, watermark, mappings_config, *, now=None, last_entry=None, time_weighted=False, blocked=None)`;
  `blocked` hat die Form von `blocked_spans(...)` (Task 1). Rückgabe unverändert ein flaches Dict; ein Feld ohne
  gültige Zeit fehlt.

- [x] **Step 1: Failing test schreiben** — `tests/test_weather_aggregate_blocked.py`

```python
"""A pausing group's window: each blocked field reduced over its valid time only."""

from datetime import datetime, timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.weather_aggregate import aggregate_window

W = datetime(2026, 7, 1, 0, 0, 0)  # the zone's watermark: the window starts here
NOW = W + timedelta(hours=24)
H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE
WIND = const.MAPPING_WINDSPEED
PRECIP = const.MAPPING_PRECIPITATION


def _hourly(field=T, values=None):
    """One row per hour; the row AT the watermark becomes the boundary reading."""
    return [
        {const.RETRIEVED_AT: W + h * H, field: values[h] if values else float(h)}
        for h in range(24)
    ]


def _span(a, b):
    return (W + a * H, W + b * H)


def _config(aggregate, field=WIND):
    return {
        field: {
            const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
            const.MAPPING_CONF_AGGREGATE: aggregate,
        }
    }


def _agg(readings, blocked=None, config=None, **kw):
    return aggregate_window(readings, W, config or {}, now=NOW, blocked=blocked, **kw)


class TestUnblockedFieldsAreUntouched:
    def test_no_spans_empty_spans_and_foreign_spans_change_nothing(self):
        rows = _hourly() + _hourly(const.MAPPING_DEWPOINT)
        base = _agg(rows)
        assert _agg(rows, blocked={}) == base
        assert _agg(rows, blocked={WIND: (_span(3, 9),)}) == base

    def test_a_field_without_spans_is_reduced_as_before(self):
        rows = [
            {const.RETRIEVED_AT: W + h * H, T: float(h), const.MAPPING_DEWPOINT: 2.0 * h}
            for h in range(24)
        ]
        base = _agg(rows)
        cut = _agg(rows, blocked={T: (_span(6, 12),)})
        assert cut[const.MAPPING_DEWPOINT] == base[const.MAPPING_DEWPOINT]
        assert cut[const.MAPPING_DATA_MULTIPLIER] == base[const.MAPPING_DATA_MULTIPLIER]
        assert cut[T] != base[T]


class TestThePlainMean:
    def test_rows_inside_a_span_are_dropped(self):
        assert _agg(_hourly())[T] == 11.5
        # Without hours 6..11: (0+...+5 + 12+...+23) / 18.
        assert _agg(_hourly(), blocked={T: (_span(6, 12),)})[T] == pytest.approx(12.5)

    def test_the_reading_of_the_return_counts(self):
        rows = [{const.RETRIEVED_AT: W, T: 0.0}, {const.RETRIEVED_AT: W + 12 * H, T: 100.0}]
        # The span is half-open: the row at its end is the return, and measured.
        assert _agg(rows, blocked={T: (_span(6, 12),)})[T] == 50.0

    def test_a_span_at_the_window_start_drops_the_boundary_as_a_sample(self):
        cut = _agg(_hourly(), blocked={T: (_span(0, 6),)})
        assert cut[T] == pytest.approx(sum(range(6, 24)) / 18)
        assert cut[const.MAPPING_MIN_TEMP] == 6.0
        assert cut[const.MAPPING_MAX_TEMP] == 23.0

    def test_a_span_at_the_window_end_drops_the_last_rows(self):
        cut = _agg(_hourly(), blocked={T: (_span(18, 24),)})
        assert cut[T] == pytest.approx(sum(range(18)) / 18)
        assert cut[const.MAPPING_MAX_TEMP] == 17.0
        assert cut[const.MAPPING_MIN_TEMP] == 0.0


class TestTheTimeWeightedMean:
    def test_a_value_is_not_held_into_a_span_and_holds_again_after_it(self):
        """A sensor that returns with the value it had writes no row (deadband,
        state_reported): after the span the value from before it holds again."""
        rows = [{const.RETRIEVED_AT: W, T: 10.0}, {const.RETRIEVED_AT: W + 2 * H, T: 14.0}]
        cut = _agg(rows, blocked={T: (_span(5, 15),)}, time_weighted=True)
        # 10 for 2 h and 14 for 3 h before the span, 14 again for the 9 h after it.
        assert cut[T] == pytest.approx((10 * 2 + 14 * 3 + 14 * 9) / 14)
        assert cut[const.MAPPING_MIN_TEMP] == 10.0
        assert cut[const.MAPPING_MAX_TEMP] == 14.0
        # Without the span the hold runs through: (10 * 2 + 14 * 22) / 24.
        assert _agg(rows, time_weighted=True)[T] == pytest.approx(328 / 24)

    def test_frozen_rows_inside_the_span_do_not_count(self):
        cut = _agg(_hourly(), blocked={T: (_span(6, 12),)}, time_weighted=True)
        assert cut[T] == pytest.approx(225 / 18)

    def test_a_window_that_starts_blocked_holds_the_boundary_after_the_span(self):
        """The boundary is the value from before the span: it holds from the span's
        end until the next reading, though it is no sample of the valid time."""
        rows = [{const.RETRIEVED_AT: W, T: 10.0}, {const.RETRIEVED_AT: W + 9 * H, T: 20.0}]
        cut = _agg(rows, blocked={T: (_span(0, 6),)}, time_weighted=True)
        assert cut[T] == pytest.approx((10 * 3 + 20 * 15) / 18)
        assert cut[const.MAPPING_MIN_TEMP] == 10.0


class TestFieldsWithoutValidTime:
    def test_a_field_blocked_throughout_is_left_out_and_not_filled(self):
        cut = _agg(_hourly(), blocked={T: (_span(0, 24),)}, last_entry={T: 20.0})
        assert T not in cut
        assert const.MAPPING_MAX_TEMP not in cut
        assert const.MAPPING_MIN_TEMP not in cut

    def test_a_field_with_no_value_to_hold_is_left_out(self):
        """No boundary and every row inside the span: nothing measured to hold."""
        rows = [{const.RETRIEVED_AT: W + h * H, T: 5.0} for h in range(7, 11)]
        assert T not in _agg(rows, blocked={T: (_span(6, 12),)})

    def test_the_carry_forward_fills_a_field_with_valid_time(self):
        cut = _agg(
            _hourly(const.MAPPING_DEWPOINT),
            blocked={T: (_span(6, 12),)},
            last_entry={T: 20.0},
        )
        assert cut[T] == 20.0
        assert cut[const.MAPPING_MAX_TEMP] == 20.0

    def test_a_blocked_field_without_readings_changes_nothing(self):
        rows = _hourly(const.MAPPING_DEWPOINT)
        assert _agg(rows, blocked={T: (_span(6, 12),)}) == _agg(rows)

    def test_a_single_value_is_used_verbatim(self):
        cut = _agg([{const.RETRIEVED_AT: W, T: 7.0}], blocked={T: (_span(10, 14),)})
        assert cut[T] == 7.0
        assert cut[const.MAPPING_MAX_TEMP] == cut[const.MAPPING_MIN_TEMP] == 7.0


@pytest.mark.parametrize(
    ("aggregate", "span", "expected"),
    [
        (const.MAPPING_CONF_AGGREGATE_FIRST, (0, 6), 6.0),
        (const.MAPPING_CONF_AGGREGATE_LAST, (18, 24), 17.0),
        (const.MAPPING_CONF_AGGREGATE_MAXIMUM, (18, 24), 17.0),
        (const.MAPPING_CONF_AGGREGATE_MINIMUM, (0, 6), 6.0),
        (const.MAPPING_CONF_AGGREGATE_MEDIAN, (6, 12), 14.5),
        (const.MAPPING_CONF_AGGREGATE_SUM, (6, 12), 225.0),
    ],
)
def test_each_aggregate_reads_only_the_valid_samples(aggregate, span, expected):
    rows = _hourly(WIND)
    assert _agg(rows, config=_config(aggregate))[WIND] != expected
    cut = _agg(rows, blocked={WIND: (_span(*span),)}, config=_config(aggregate))
    assert cut[WIND] == expected


class TestRain:
    RATE = _config(const.MAPPING_CONF_AGGREGATE_RIEMANNSUM, PRECIP)

    def test_a_rain_rate_is_integrated_over_its_valid_time_only(self):
        rows = _hourly(PRECIP, values=[2.0] * 24)
        assert _agg(rows, config=self.RATE)[PRECIP] == pytest.approx(46.0)
        # Six blocked hours at 2 mm/h book nothing; the pair across the span counts
        # only its one measured hour (5..6).
        cut = _agg(rows, blocked={PRECIP: (_span(6, 12),)}, config=self.RATE)
        assert cut[PRECIP] == pytest.approx(34.0)

    def test_a_rain_gauge_is_never_cut_even_if_asked(self):
        rows = [{const.RETRIEVED_AT: W + h * H, PRECIP: float(h)} for h in range(24)]
        assert _agg(rows, blocked={PRECIP: (_span(6, 12),)}) == _agg(rows)


def test_a_row_stamped_after_now_counts_as_measured():
    """Clock skew: the window runs to the late row, and the span ends long before."""
    rows = _hourly() + [{const.RETRIEVED_AT: NOW + 2 * H, T: 100.0}]
    cut = _agg(rows, blocked={T: (_span(6, 12),)})
    assert cut[T] == pytest.approx((225 + 100) / 19)
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate_blocked.py -p _local_socket_unblock -q`
Expected: FAIL mit `TypeError: aggregate_window() got an unexpected keyword argument 'blocked'`.

- [x] **Step 3: Import** — in `weather_aggregate.py` `import itertools` zwischen `import datetime` und `import logging`.

- [x] **Step 4: Parameter durchreichen** — `aggregate_window` bekommt nach `time_weighted=False,` den Parameter
  `blocked=None,`; im Docstring nach dem Absatz zu `time_weighted` ergänzen:

```
        blocked: ``{field: ((from, to), ...)}``, each field's blocked time
            inside the window (sensor_liveness.blocked_spans). Only a pausing
            sensor group's daily commit passes it. A blocked field is reduced
            over its valid time and left out when it has none; a field without
            spans is reduced exactly as without the argument.
```

  Der Aufruf von `_aggregate` am Ende bekommt `blocked=blocked,` nach `time_weighted=time_weighted,`.

- [x] **Step 5: `_aggregate` verzweigt** — Signatur um `blocked=None,` nach `time_weighted=False,` erweitern; im
  Schleifenkörper direkt nach

```python
        if key == const.RETRIEVED_AT:
            continue
```

  einfügen:

```python
        spans = blocked.get(key) if blocked else None
        if spans and window_start is not None and window_end is not None:
            aggregate = effective_aggregate(key, mappings_config)
            if aggregate != const.MAPPING_CONF_AGGREGATE_DELTA:
                # A pausing group's blocked field, reduced over its valid time
                # only. A rain gauge is never cut -- its reading after the
                # return is a measurement, delivered late -- and every field
                # without spans takes the path below, untouched.
                _aggregate_blocked(
                    key,
                    raw,
                    spans,
                    aggregate,
                    resultdata,
                    window_start,
                    window_end,
                    time_weighted=time_weighted,
                )
                continue
```

- [x] **Step 6: Die Regeln** — direkt nach `_aggregate` (vor `class WaterStep`) einfügen:

```python
def _aggregate_blocked(
    key, raw, spans, aggregate, resultdata, start, end, *, time_weighted
):
    """Reduce one field of a pausing group over its valid time: the window minus ``spans``.

    The rules of ``_aggregate``, restricted to where the field was measured. A
    row stamped inside a span is dropped: it is the frozen value a poll keeps
    stamping fresh. The boundary reading stays as a value but counts as a
    sample only where the window does not start blocked. A value is held to the
    next reading but never into a span, and after one the value from before it
    holds again: a sensor that returns with the value it had writes no row
    (deadband, ``state_reported``). Without valid time, or without a value to
    hold, the field is left out.
    """
    segments = _valid_segments(spans, start, end)
    if not segments:
        return
    stamped = sorted(
        ((t, float(v)) for t, v in raw if t is not None), key=lambda sample: sample[0]
    )
    if not stamped:
        # Only the unstamped carry-forward (last_entry): it holds for the valid time.
        unstamped = [float(v) for t, v in raw if t is None]
        if unstamped:
            _single_value(key, unstamped[-1], resultdata)
        return
    kept = [(t, v) for t, v in stamped if t <= start or not _blocked_at(t, spans)]
    if not kept:
        return
    if len(kept) < 2:
        _single_value(key, kept[0][1], resultdata)
        return
    values = [v for t, v in kept if not _blocked_at(t, spans)]
    held = [_held(kept, a) for a, _ in segments]
    if key == const.MAPPING_TEMPERATURE:
        resultdata[const.MAPPING_MAX_TEMP] = max(values + held)
        resultdata[const.MAPPING_MIN_TEMP] = min(values + held)
    if aggregate == const.MAPPING_CONF_AGGREGATE_AVERAGE:
        if time_weighted:
            resultdata[key] = _segment_weighted_mean(kept, segments)
        else:
            resultdata[key] = statistics.mean(values) if values else held[0]
    elif aggregate == const.MAPPING_CONF_AGGREGATE_RIEMANNSUM:
        resultdata[key] = _riemann_over(kept, segments)
    elif not values:
        resultdata[key] = held[0]
    elif aggregate == const.MAPPING_CONF_AGGREGATE_FIRST:
        resultdata[key] = values[0]
    elif aggregate == const.MAPPING_CONF_AGGREGATE_LAST:
        resultdata[key] = values[-1]
    elif aggregate == const.MAPPING_CONF_AGGREGATE_MAXIMUM:
        resultdata[key] = max(values)
    elif aggregate == const.MAPPING_CONF_AGGREGATE_MINIMUM:
        resultdata[key] = min(values)
    elif aggregate == const.MAPPING_CONF_AGGREGATE_MEDIAN:
        resultdata[key] = statistics.median(values)
    elif aggregate == const.MAPPING_CONF_AGGREGATE_SUM:
        resultdata[key] = sum(values)


def _valid_segments(spans, start, end):
    """``[start, end)`` minus the sorted, merged ``spans``: where a field was measured."""
    segments = []
    cursor = start
    for lo, hi in spans:
        if lo > cursor:
            segments.append((cursor, min(lo, end)))
        cursor = max(cursor, hi)
    if cursor < end:
        segments.append((cursor, end))
    return [(a, b) for a, b in segments if b > a]


def _blocked_at(stamp, spans):
    """Whether ``stamp`` lies in a span; half-open, so the reading of a return counts."""
    return any(lo <= stamp < hi for lo, hi in spans)


def _held(kept, at):
    """The value held at ``at``: the last kept reading at or before it, else the first."""
    value = kept[0][1]
    for stamp, reading in kept:
        if stamp > at:
            break
        value = reading
    return value


def _segment_weighted_mean(kept, segments):
    """The time-weighted mean over the valid segments, each opened with its held value."""
    total = 0.0
    width = 0.0
    for a, b in segments:
        inner = [(t, v) for t, v in kept if a < t < b]
        times = [a] + [t for t, _ in inner]
        values = [_held(kept, a)] + [v for _, v in inner]
        seconds = (b - a).total_seconds()
        total += _time_weighted_mean(times, values, a, b) * seconds
        width += seconds
    return total / width


def _riemann_over(kept, segments):
    """Trapezoids between consecutive kept readings, each counted for its valid part.

    A pair across a span stands for the hours on both sides of it; only the
    measured ones book rain, so nothing is interpolated through the silence.
    """
    total = 0.0
    for (t0, v0), (t1, v1) in itertools.pairwise(kept):
        valid = sum(
            max(0.0, (min(b, t1) - max(a, t0)).total_seconds()) for a, b in segments
        )
        total += (v0 + v1) / 2 * valid / 3600
    return total


def _single_value(key, value, resultdata):
    """One value for the whole valid time, as ``_aggregate``'s single-sample branch."""
    if key == const.MAPPING_TEMPERATURE:
        resultdata[const.MAPPING_MAX_TEMP] = value
        resultdata[const.MAPPING_MIN_TEMP] = value
    resultdata[key] = value
```

- [x] **Step 7: Test laufen lassen, er muss grün sein; die Nachbarn bleiben grün**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate_blocked.py tests/test_weather_aggregate.py tests/test_aggregate_time_weighting_is_opt_in.py tests/test_continuous_update.py -p _local_socket_unblock -q`
Expected: alle grün (23 neue Fälle).

- [x] **Step 8: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_weather_aggregate_blocked.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/weather_aggregate.py tests/test_weather_aggregate_blocked.py
git commit -F - <<'EOF'
feat(aggregate): reduce a blocked field over its valid time only

The aggregate takes each field's blocked time as an optional argument.
A blocked field drops the rows stamped inside a span (the frozen value a
poll keeps stamping fresh), holds a value up to a span but never into it,
and after the span holds the value from before it again, because a
sensor that returns with the value it had writes no row. A field without
valid time is left out rather than filled from the carry-forward. A rain
rate integrates its measured hours only; a rain gauge is never cut.
Fields without spans, and every caller that passes nothing, are reduced
exactly as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Das Gate und der Weg der Sperren durch den Commit

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (Imports `:20`, `:34-41`, `:43-49`; neue Methode vor `_aggregate_for_zone` `:393`; `_aggregate_for_zone` `:393-434`; `async_calculate_zone` `:606`, `:625-626`; `_record_window_amplitude` `:644`; `_record_window_radiation` `:694`)
- Modify: `tests/test_run_in_flight.py` (`_FakeStore`, `:37-66`)
- Test: `tests/test_silent_sensor_commit.py` (neu)

**Interfaces:**
- Consumes: `blocked_spans`, `group_pauses`, `outages_of` (Task 1, `sensor_liveness`); `aggregate_window(…, blocked=)` (Task 3);
  `effective_aggregate` (`weather_aggregate.py:412`); `hourly_calculation_enabled(store)` (`calculation.py:87`).
- Produces: `SmartIrrigationCoordinator._blocked_spans_for_zone(zone: dict, *, now) -> dict | None`;
  `_aggregate_for_zone(zone, *, now, blocked=None)`; `_record_window_amplitude(zone, weatherdata, *, now, blocked=None)`;
  `_record_window_radiation(zone, weatherdata, *, now, blocked=None)`. In `async_calculate_zone` heißt der Wert `blocked`.

- [x] **Step 1: Failing test schreiben** — `tests/test_silent_sensor_commit.py` (die Tasks 5 und 6 hängen weitere
  Klassen an diese Datei an)

```python
"""A pausing sensor group's commit: the gate, the cut, the booking and its explanation."""

import datetime
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.sensor_liveness import Outage
from custom_components.irrigation_plus.store import SmartIrrigationStorage

W = datetime.datetime(2026, 7, 1, 0, 0, 0)  # the zone's watermark, naive on HA's clock
NOW = W + timedelta(hours=24)
H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE
PRECIP = const.MAPPING_PRECIPITATION


def _sensor(entity, aggregate=None):
    field = {
        const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
        const.MAPPING_CONF_SENSOR: entity,
    }
    if aggregate is not None:
        field[const.MAPPING_CONF_AGGREGATE] = aggregate
    return field


def _outage(start_h, end_h=None, fields=(T,)):
    return Outage(
        "sensor.t",
        "dev1",
        tuple(fields),
        W + start_h * H,
        None if end_h is None else W + end_h * H,
    ).to_store()


@pytest.fixture
async def coord(hass):
    """A real coordinator and store; the module is stubbed unless a test wires one."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    c.calculate_module = AsyncMock(
        return_value={const.ZONE_BUCKET: -1.0, const.ZONE_DURATION: 0}
    )
    return c, store


async def _group(store, *, setting="pause", outages=(), mappings=None, readings=None):
    created = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Garden",
            const.MAPPING_MAPPINGS: (
                mappings if mappings is not None else {T: _sensor("sensor.t")}
            ),
            const.MAPPING_DATA: (
                readings
                if readings is not None
                else [{const.RETRIEVED_AT: W + h * H, T: float(h)} for h in range(24)]
            ),
            const.MAPPING_ON_SILENT_SENSOR: setting,
            const.MAPPING_SENSOR_OUTAGES: list(outages),
        }
    )
    return created[const.MAPPING_ID]


async def _zone(store, mapping_id, *, module_id=1, watermark=W):
    created = await store.async_create_zone(
        {
            const.ZONE_NAME: "z",
            const.ZONE_MAPPING: mapping_id,
            const.ZONE_MODULE: module_id,
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0.0,
            const.ZONE_MAXIMUM_BUCKET: 50.0,
            const.ZONE_DRAINAGE_RATE: 0.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 3600,
            const.ZONE_LEAD_TIME: 0,
            const.ZONE_LAST_CONSUMED: watermark,
        }
    )
    return created[const.ZONE_ID]


def _gate(c, store, zone_id):
    return c._blocked_spans_for_zone(store.get_zone(zone_id), now=NOW)


class TestTheGate:
    async def test_a_pausing_group_is_cut_where_its_outage_blocks(self, coord):
        c, store = coord
        zone = await _zone(store, await _group(store, outages=[_outage(2, 10)]))
        assert _gate(c, store, zone) == {T: ((W + 5 * H, W + 10 * H),)}

    async def test_a_group_that_keeps_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, setting="keep", outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_with_the_hourly_calculation_nothing_is_cut(self, coord):
        c, store = coord
        await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
        mid = await _group(store, outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_a_window_no_outage_reaches_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, outages=[_outage(-30, -20), _outage(2, 4)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_a_zone_that_never_consumed_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid, watermark=None)) is None

    async def test_a_zone_without_its_group_is_not_cut(self, coord):
        c, store = coord
        assert _gate(c, store, await _zone(store, 99)) is None
        assert c._blocked_spans_for_zone({const.ZONE_MAPPING: None}, now=NOW) is None

    async def test_a_rain_gauge_is_never_cut_and_a_rain_rate_is(self, coord):
        c, store = coord
        both = (T, PRECIP)
        gauge = await _group(
            store,
            mappings={T: _sensor("sensor.t"), PRECIP: _sensor("sensor.rain")},
            outages=[_outage(2, 10, fields=both)],
        )
        rate = await _group(
            store,
            mappings={
                T: _sensor("sensor.t"),
                PRECIP: _sensor("sensor.rain", const.MAPPING_CONF_AGGREGATE_RIEMANNSUM),
            },
            outages=[_outage(2, 10, fields=both)],
        )
        assert set(_gate(c, store, await _zone(store, gauge))) == {T}
        assert set(_gate(c, store, await _zone(store, rate))) == {T, PRECIP}

    async def test_outage_stamps_with_an_offset_are_read_on_has_clock(self, coord):
        """A record edited by hand, or written by another build, may carry offsets."""
        c, store = coord
        local = W.replace(tzinfo=dt_util.get_default_time_zone())
        record = {
            "entity_id": "sensor.t",
            "device_id": "dev1",
            "fields": [T],
            "start": (local + 2 * H).isoformat(),
            "end": (local + 10 * H).isoformat(),
        }
        zone = await _zone(store, await _group(store, outages=[record]))
        assert _gate(c, store, zone) == {T: ((W + 5 * H, W + 10 * H),)}


class TestTheCommitCarriesTheSpans:
    async def test_the_aggregate_and_both_records_are_cut(self, coord):
        c, store = coord
        zone = await _zone(store, await _group(store, outages=[_outage(2, 10)]))
        c._record_window_amplitude = AsyncMock()
        c._record_window_radiation = AsyncMock()

        await c.async_calculate_zone(zone, now=NOW)

        expected = {T: ((W + 5 * H, W + 10 * H),)}
        assert c._record_window_amplitude.call_args.kwargs["blocked"] == expected
        assert c._record_window_radiation.call_args.kwargs["blocked"] == expected
        weatherdata = c.calculate_module.call_args.args[1]
        # 0..23 without the frozen rows of hours 5..9.
        assert weatherdata[T] == pytest.approx((sum(range(24)) - sum(range(5, 10))) / 19)

    async def test_a_group_that_keeps_aggregates_as_before(self, coord):
        c, store = coord
        mid = await _group(store, setting="keep", outages=[_outage(2, 10)])
        c._record_window_amplitude = AsyncMock()

        await c.async_calculate_zone(await _zone(store, mid), now=NOW)

        assert c._record_window_amplitude.call_args.kwargs["blocked"] is None
        assert c.calculate_module.call_args.args[1][T] == 11.5


class TestTheRecordsSkipABlockedWindow:
    async def test_no_amplitude_is_recorded_when_the_temperature_was_blocked(
        self, coord
    ):
        c, store = coord
        mid = await _group(store)
        zone = store.get_zone(await _zone(store, mid))
        data = {
            const.MAPPING_DATA_MULTIPLIER: 1.0,
            const.MAPPING_MIN_TEMP: 5.0,
            const.MAPPING_MAX_TEMP: 15.0,
        }

        await c._record_window_amplitude(zone, data, now=NOW, blocked={T: ((W, W + H),)})
        assert store.get_mapping(mid)[const.MAPPING_TEMPERATURE_AMPLITUDES] == []

        other = {const.MAPPING_DEWPOINT: ((W, W + H),)}
        await c._record_window_amplitude(zone, data, now=NOW, blocked=other)
        assert store.get_mapping(mid)[const.MAPPING_TEMPERATURE_AMPLITUDES] == [
            [NOW.date().isoformat(), 10.0]
        ]

    async def test_no_radiation_pair_is_recorded_when_the_sun_was_blocked(self, coord):
        c, store = coord
        mid = await _group(store)
        zone = store.get_zone(await _zone(store, mid))
        c._effective_latitude = 40.0
        c._effective_longitude = 0.0
        data = {const.MAPPING_SOLRAD: 15.0}
        sun = {const.MAPPING_SOLRAD: ((W, W + H),)}

        await c._record_window_radiation(zone, data, now=NOW, blocked=sun)
        assert store.get_mapping(mid)[const.MAPPING_RADIATION_CALIBRATION] == []

        await c._record_window_radiation(zone, data, now=NOW, blocked={T: ((W, W + H),)})
        assert len(store.get_mapping(mid)[const.MAPPING_RADIATION_CALIBRATION]) == 1
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py -p _local_socket_unblock -q`
Expected: FAIL — `AttributeError: … has no attribute '_blocked_spans_for_zone'` bzw. `TypeError: … unexpected keyword argument 'blocked'`.

- [x] **Step 3: Imports** in `calculation.py`:
  - `from .helpers import (` um `STAMP_FROM_STORE,` nach `STAMP_FROM_CLIENT,` ergänzen;
  - neue Zeile `from .sensor_liveness import blocked_spans, group_pauses, outages_of` (ruff `I`: zwischen
    `.localize` und `.weather_aggregate`);
  - `from .weather_aggregate import (` um `effective_aggregate,` nach `build_substeps,` ergänzen.

- [x] **Step 4: Das Gate** — direkt vor `async def _aggregate_for_zone` einfügen:

```python
    def _blocked_spans_for_zone(self, zone, *, now):
        """The time this zone's window may not book from its sensor group, or None.

        Only a group that pauses a silent sensor is cut, and only in the daily
        form: with the hourly calculation the replayed balance checks itself
        against this aggregate's precipitation, so cutting one and not the
        other would fail that check; that form cuts together with the live
        estimate. None leaves the commit as it always was, and so does a window
        no outage reaches, or a zone that has never consumed (its first commit
        anchors it). A cumulative rain gauge is never blocked: what it reads
        after the return is a measurement, only delivered late.
        """
        mapping_id = zone.get(const.ZONE_MAPPING)
        if mapping_id is None:
            return None
        mapping = self.store.get_mapping(mapping_id)
        if not mapping or not group_pauses(mapping):
            return None
        if hourly_calculation_enabled(self.store):
            return None
        watermark = coerce_stamp(zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE)
        now = coerce_stamp(now, STAMP_FROM_STORE)
        if watermark is None or now is None or watermark >= now:
            return None
        config = mapping.get(const.MAPPING_MAPPINGS) or {}
        blocked = {
            field: spans
            for field, spans in blocked_spans(
                outages_of(mapping), watermark, now
            ).items()
            if effective_aggregate(field, config) != const.MAPPING_CONF_AGGREGATE_DELTA
        }
        return blocked or None
```

- [x] **Step 5: `_aggregate_for_zone`** — Signatur `async def _aggregate_for_zone(self, zone, *, now, blocked=None):`;
  im Docstring direkt nach der Titelzeile (vor dem bisherigen ersten Absatz) als eigenen Absatz ergänzen: ``` ``blocked`` is a pausing group's blocked time
  (_blocked_spans_for_zone), passed to the aggregate as is.``` ; im `aggregate_window(...)`-Aufruf nach dem
  `time_weighted=(...)`-Argument `blocked=blocked,` anfügen.

- [x] **Step 6: `async_calculate_zone`** — die Zeile

```python
        weatherdata, n_points = await self._aggregate_for_zone(zone, now=now)
```

  ersetzen durch

```python
        # A pausing sensor group books nothing for a silent sensor's time; None
        # for every other zone, whose commit stays exactly as it was.
        blocked = self._blocked_spans_for_zone(zone, now=now)
        weatherdata, n_points = await self._aggregate_for_zone(
            zone, now=now, blocked=blocked
        )
```

  und die beiden Aufzeichnungen durch

```python
        await self._record_window_amplitude(zone, weatherdata, now=now, blocked=blocked)
        await self._record_window_radiation(zone, weatherdata, now=now, blocked=blocked)
```

- [x] **Step 7: Die Aufzeichnungen** — Signaturen `async def _record_window_amplitude(self, zone, weatherdata, *, now, blocked=None):`
  und `async def _record_window_radiation(self, zone, weatherdata, *, now, blocked=None):`.
  In `_record_window_amplitude` den Docstring-Absatz „Skipped for a window materially shorter …“ ergänzen um
  ``` Skipped, too, when the temperature was blocked in the window: its spread then covers part of the day only.```
  und direkt nach `if mapping_id is None:\n            return` einfügen:

```python
        if blocked and const.MAPPING_TEMPERATURE in blocked:
            return
```

  In `_record_window_radiation` im Docstring ergänzen ``` Not when the sun was blocked in the window: its mean
  then covers part of the day only.``` und direkt vor `mean = weatherdata.get(const.MAPPING_SOLRAD)` einfügen:

```python
        if blocked and const.MAPPING_SOLRAD in blocked:
            return
```

- [x] **Step 8: Den Fake-Store eines bestehenden Tests ergänzen** — `tests/test_run_in_flight.py`, Klasse `_FakeStore`,
  nach `get_distributor` einfügen (das Gate fragt den Store jetzt nach der Sensorgruppe; der echte Store hat die
  Methode immer):

```python
    def get_mapping(self, mapping_id):
        return None
```

- [x] **Step 9: Test laufen lassen, er muss grün sein; die Nachbarn bleiben grün**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_run_in_flight.py tests/test_per_zone_consumption.py tests/test_window_amplitude.py tests/test_live_estimate_measured_radiation.py tests/test_coordinator_mixins.py -p _local_socket_unblock -q`
Expected: alle grün (12 neue Fälle).

- [x] **Step 10: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_silent_sensor_commit.py tests/test_run_in_flight.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/calculation.py tests/test_silent_sensor_commit.py tests/test_run_in_flight.py
git commit -F - <<'EOF'
feat(calculation): a pausing sensor group's commit cuts its silent time

The commit asks once per zone which time it may not book: only for a
group set to pause, only without the hourly calculation (whose replayed
balance checks itself against this aggregate), only for a zone that has
consumed before. A rain gauge is never cut. The blocked time goes to the
aggregate and to the two window records, which skip a window whose
temperature or sun was blocked so a part of a day is not filed as a day.
Every other zone passes nothing and calculates as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---
### Task 5: Buchen nur für den gemessenen Anteil

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (Import `:20`; neue Konstante nach `BUFFER_RETENTION`, `:55`; `async_calculate_zone`, Aufruf von `calculate_module` `:614-616`; `calculate_module` `:1140-1255`)
- Test: `tests/test_silent_sensor_commit.py` (Klassen anhängen)

**Interfaces:**
- Consumes: `valid_share` (Task 1); `blocked` aus `async_calculate_zone` (Task 4); `DAILY_FORM_FIELDS`
  (`calcmodules/pyeto/__init__.py:114-120`).
- Produces: `calculate_module(zone, weatherdata, forecastdata, *, now=None, run_start=None, blocked=None)`;
  Modul-Konstante `_REQUIRED_SENSOR_FIELDS: dict[str, tuple[str, ...]]`; innerhalb von `calculate_module` die
  lokale Variable `share: float | None` (Task 6 liest sie).

- [x] **Step 1: Failing test schreiben** — an `tests/test_silent_sensor_commit.py` anhängen:

```python
ET = const.MAPPING_EVAPOTRANSPIRATION
DEW = const.MAPPING_DEWPOINT
SUN = const.MAPPING_SOLRAD


async def _module(c, store, name, *, returns, forecast_days=0):
    """A module of this name whose instance is a stub returning ``returns``; from
    here on the coordinator runs its real calculate_module."""
    module = await store.async_create_module(
        {const.MODULE_NAME: name, "description": "", "config": {}}
    )
    instance = Mock()
    instance.calculate = Mock(return_value=returns)
    instance.forecast_days = forecast_days
    c.getModuleInstanceByID = AsyncMock(return_value=instance)
    if "calculate_module" in vars(c):
        del c.calculate_module
    return module[const.MODULE_ID], instance


def _hours(**fields):
    """24 hourly rows carrying ``fields`` (a value or a callable of the hour)."""
    return [
        {
            const.RETRIEVED_AT: W + h * H,
            **{k: (v(h) if callable(v) else v) for k, v in fields.items()},
        }
        for h in range(24)
    ]


class TestTheBooking:
    async def test_the_module_is_handed_the_spans(self, coord):
        c, store = coord
        zone = await _zone(store, await _group(store, outages=[_outage(2, 10)]))

        await c.async_calculate_zone(zone, now=NOW)

        assert c.calculate_module.call_args.kwargs["blocked"] == {
            T: ((W + 5 * H, W + 10 * H),)
        }

    def test_pyeto_needs_dewpoint_temperature_wind_and_pressure(self):
        from custom_components.irrigation_plus.calculation import (
            _REQUIRED_SENSOR_FIELDS,
        )

        assert _REQUIRED_SENSOR_FIELDS["PyETO"] == (
            DEW,
            T,
            const.MAPPING_WINDSPEED,
            const.MAPPING_PRESSURE,
        )
        assert _REQUIRED_SENSOR_FIELDS["Passthrough"] == (ET,)

    async def test_pyeto_books_the_share_in_which_its_fields_were_measured(
        self, coord
    ):
        c, store = coord
        module_id, instance = await _module(c, store, "PyETO", returns=-4.0)
        mid = await _group(store, outages=[_outage(2, 10)])
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        instance.calculate.assert_called_once()
        assert store.get_zone(zone)[const.ZONE_DELTA] == pytest.approx(-4.0 * 19 / 24)

    async def test_with_forecast_days_the_whole_mean_is_scaled(self, coord):
        """The module returns the mean of the weather day and its forecast days; the
        blocked time books none of it, the forecast part included."""
        c, store = coord
        module_id, _ = await _module(
            c, store, "PyETO", returns=-4.0, forecast_days=2
        )
        mid = await _group(store, outages=[_outage(2, 10)])
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        assert store.get_zone(zone)[const.ZONE_DELTA] == pytest.approx(-4.0 * 19 / 24)

    async def test_a_field_pyeto_does_without_does_not_reduce_the_share(self, coord):
        c, store = coord
        module_id, _ = await _module(c, store, "PyETO", returns=-4.0)
        mid = await _group(
            store,
            mappings={T: _sensor("sensor.t"), SUN: _sensor("sensor.sun")},
            readings=_hours(**{T: 20.0, SUN: 10.0}),
            outages=[_outage(2, 10, fields=(SUN,))],
        )
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        assert store.get_zone(zone)[const.ZONE_DELTA] == -4.0

    async def test_pyeto_without_a_measured_required_field_books_the_rain_only(
        self, coord
    ):
        c, store = coord
        module_id, instance = await _module(c, store, "PyETO", returns=-4.0)
        mid = await _group(
            store,
            mappings={
                T: _sensor("sensor.t"),
                DEW: _sensor("sensor.dew"),
                PRECIP: _sensor("sensor.rain"),
            },
            readings=_hours(**{T: 20.0, PRECIP: lambda h: 0.0 if h < 12 else 3.0}),
            outages=[_outage(-10, fields=(DEW,))],
        )
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        instance.calculate.assert_not_called()
        assert store.get_zone(zone)[const.ZONE_DELTA] == pytest.approx(3.0)
        assert store.get_zone(zone)[const.ZONE_LAST_CONSUMED] == NOW

    async def test_passthrough_books_the_measured_share_of_its_et(self, coord):
        c, store = coord
        module_id, _ = await _module(c, store, "Passthrough", returns=4.0)
        mid = await _group(
            store,
            mappings={ET: _sensor("sensor.et")},
            readings=_hours(**{ET: 4.0}),
            outages=[_outage(2, 10, fields=(ET,))],
        )
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        assert store.get_zone(zone)[const.ZONE_DELTA] == pytest.approx(-4.0 * 19 / 24)

    async def test_passthrough_with_its_et_blocked_throughout_consumes_quietly(
        self, coord, caplog
    ):
        c, store = coord
        module_id, instance = await _module(c, store, "Passthrough", returns=4.0)
        mid = await _group(
            store,
            mappings={ET: _sensor("sensor.et")},
            readings=_hours(**{ET: 4.0}),
            outages=[_outage(-10, fields=(ET,))],
        )
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        instance.calculate.assert_not_called()
        assert store.get_zone(zone)[const.ZONE_DELTA] == 0.0
        assert store.get_zone(zone)[const.ZONE_LAST_CONSUMED] == NOW
        assert "No evapotranspiration value provided" not in caplog.text
        assert "calculation returned no result" not in caplog.text

    async def test_passthrough_without_its_et_for_another_reason_still_says_so(
        self, coord, caplog
    ):
        """Not a silent ET sensor: the field never arrived. Today's error, and the
        window stays where it was."""
        c, store = coord
        module_id, _ = await _module(c, store, "Passthrough", returns=4.0)
        mid = await _group(
            store,
            mappings={ET: _sensor("sensor.et")},
            readings=_hours(**{T: 1.0}),
            outages=[_outage(2, 10)],
        )
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        assert "No evapotranspiration value provided" in caplog.text
        assert store.get_zone(zone)[const.ZONE_LAST_CONSUMED] == W

    async def test_a_static_zone_in_a_pausing_group_books_as_before(self, coord):
        c, store = coord
        module_id, _ = await _module(c, store, "Static", returns=-2.0)
        mid = await _group(store, outages=[_outage(2, 10)])
        zone = await _zone(store, mid, module_id=module_id)

        await c.async_calculate_zone(zone, now=NOW)

        assert store.get_zone(zone)[const.ZONE_DELTA] == -2.0


class TestAGroupThatIsNotCutCalculatesAsBefore:
    FIELDS = (
        const.ZONE_DELTA,
        const.ZONE_BUCKET,
        const.ZONE_DURATION,
        const.ZONE_EXPLANATION,
    )

    async def _results(self, c, store, module_id, *groups):
        zones = [await _zone(store, mid, module_id=module_id) for mid in groups]
        for zone in zones:
            await c.async_calculate_zone(zone, now=NOW)
        return [{f: store.get_zone(zone)[f] for f in self.FIELDS} for zone in zones]

    async def test_keep_with_outages_and_pause_without_one_match_a_plain_group(
        self, coord
    ):
        c, store = coord
        module_id, _ = await _module(c, store, "PyETO", returns=-4.0)
        plain, keep, quiet = await self._results(
            c,
            store,
            module_id,
            await _group(store, setting="keep"),
            await _group(store, setting="keep", outages=[_outage(2, 10)]),
            await _group(store, outages=[_outage(-30, -20)]),
        )
        assert keep == plain
        assert quiet == plain

    async def test_a_pausing_group_under_the_hourly_calculation_matches_too(
        self, coord
    ):
        c, store = coord
        await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
        module_id, _ = await _module(c, store, "PyETO", returns=-4.0)
        plain, paused = await self._results(
            c,
            store,
            module_id,
            await _group(store, setting="keep"),
            await _group(store, outages=[_outage(2, 10)]),
        )
        assert paused == plain
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py -p _local_socket_unblock -q`
Expected: FAIL — `KeyError: 'blocked'` (der Commit reicht die Sperren noch nicht an das Modul),
`ImportError … _REQUIRED_SENSOR_FIELDS`, die Buchungs-Tests mit der ungekürzten Zahl (`-4.0` statt `-3.1666…`), PyETO
ruft das Modul trotz ganz gesperrtem Taupunkt, Passthrough meldet den ERROR. Schon grün (sie halten fest, was sich
nicht ändern darf): die zwei Byte-Identitäts-Tests, der Static-Test, `test_a_field_pyeto_does_without…` und
`test_passthrough_without_its_et_for_another_reason…`.

- [x] **Step 3: Imports** — `from .calcmodules.pyeto import SOLRAD_behavior` wird
  `from .calcmodules.pyeto import DAILY_FORM_FIELDS, SOLRAD_behavior`; die `sensor_liveness`-Zeile aus Task 4 wird
  `from .sensor_liveness import blocked_spans, group_pauses, outages_of, valid_share`.

- [x] **Step 4: Pflichtfelder** — direkt nach `BUFFER_RETENTION = timedelta(days=7)`:

```python
# The sensor-group fields each module cannot book without: a pausing group books
# only the part of a window in which all of them were measured. PyETO's daily
# form refuses a day without the fields of DAILY_FORM_FIELDS, whose minimum and
# maximum temperature are derived from the mapped Temperature; a missing Solar
# Radiation it estimates instead. Passthrough books its ET field.
_REQUIRED_SENSOR_FIELDS = {
    "PyETO": tuple(
        dict.fromkeys(
            (
                const.MAPPING_TEMPERATURE
                if field in (const.MAPPING_MIN_TEMP, const.MAPPING_MAX_TEMP)
                else field
            )
            for field in DAILY_FORM_FIELDS
        )
    ),
    "Passthrough": (const.MAPPING_EVAPOTRANSPIRATION,),
}
```

- [x] **Step 5: Durchreichen** — in `async_calculate_zone` den Aufruf

```python
        calc_data = await self.calculate_module(
            zone, weatherdata, forecastdata, now=now, run_start=run_start
        )
```

  ersetzen durch

```python
        calc_data = await self.calculate_module(
            zone,
            weatherdata,
            forecastdata,
            now=now,
            run_start=run_start,
            blocked=blocked,
        )
```

- [x] **Step 6: `calculate_module`** —
  1. Signatur: `self, zone, weatherdata, forecastdata, *, now=None, run_start=None, blocked=None`. Im Docstring unter
     `forecastdata:` ergänzen:
     ```
                 blocked: a pausing sensor group's blocked time per field
                     (_blocked_spans_for_zone); None books as always.
     ```
  2. Direkt nach

```python
        if now is None:
            now = local_naive_now()
```

     einfügen:

```python
        # A pausing group books only the part of the window in which every field
        # the module cannot do without was measured; None for every other commit,
        # which books exactly as it always has.
        share = None
        if blocked is not None:
            required = _REQUIRED_SENSOR_FIELDS.get(m[const.MODULE_NAME])
            watermark = coerce_stamp(
                zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE
            )
            if required is not None and watermark is not None:
                share = valid_share(
                    blocked, required, watermark, coerce_stamp(now, STAMP_FROM_STORE)
                )
```

  3. Im PyETO-Zweig `if hourly is None:` ersetzen durch

```python
            # share 0: a field the equation cannot do without was silent for the
            # whole window. Nothing is booked, so the equation is not asked (it
            # would warn about the missing field); the rain still counts.
            if hourly is None and share != 0:
```

  4. Im Passthrough-Zweig `if const.MAPPING_EVAPOTRANSPIRATION in weatherdata:` ersetzen durch

```python
            if share == 0:
                # Its ET sensor was silent for the whole window: nothing to book,
                # and nothing is misconfigured. The window is consumed as PyETO's
                # is, rather than left to grow with an error at every run.
                delta = 0.0
            elif const.MAPPING_EVAPOTRANSPIRATION in weatherdata:
```

  5. Im Tagesform-Zweig direkt nach `et_delta = delta * kc * hour_multiplier` einfügen:

```python
            if share is not None:
                # Only the measured part of the window books; the forecast days
                # the module averaged in are part of that mean.
                et_delta *= share
```

- [x] **Step 7: Test laufen lassen, er muss grün sein; die Nachbarn bleiben grün**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_calculate_module.py tests/test_manual_bucket_assertion.py tests/test_mid_window_bucket_credit.py tests/test_summed_hourly_eto.py -p _local_socket_unblock -q`
Expected: alle grün (12 neue Fälle in diesem Task).

- [x] **Step 8: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_silent_sensor_commit.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/calculation.py tests/test_silent_sensor_commit.py
git commit -F - <<'EOF'
feat(calculation): a pausing group books only the measured share

The module books evapotranspiration only for the part of the window in
which all the fields it cannot do without were measured at once: for
PyETO's daily form dewpoint, temperature, wind and pressure, for
Passthrough its ET field. The share scales the module's result as a
whole, forecast days included. When it is zero the module is not asked;
the window is consumed and rain still counts, so Passthrough no longer
reports a configuration error for a sensor that is only silent. Groups
that keep, and pausing groups under the hourly calculation, book exactly
as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Zwei Sätze in der Berechnungs-Erklärung

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (`calculate_module`, nach dem Kc-Satz `:1419-1428`; neue Methode direkt nach `calculate_module`)
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json` (Block `module.calculation.explanation`, nach `"crop-coefficient-applied"`)
- Test: `tests/test_silent_sensor_commit.py` (Klasse anhängen)

**Interfaces:**
- Consumes: `blocked`, `share` in `calculate_module` (Task 5).
- Produces: `SmartIrrigationCoordinator._silent_sensor_explanation(blocked: dict, share: float | None) -> str`;
  Schlüssel `module.calculation.explanation.sensor-outage` (Platzhalter `{fields}`, `{start}`, `{end}`) und
  `module.calculation.explanation.sensor-outage-share` (Platzhalter `{share}`).

- [x] **Step 1: Failing test schreiben** — an `tests/test_silent_sensor_commit.py` anhängen:

```python
class TestTheExplanation:
    async def _explain(self, c, store, module="PyETO", **group):
        module_id, _ = await _module(c, store, module, returns=-2.0)
        zone = await _zone(store, await _group(store, **group), module_id=module_id)
        await c.async_calculate_zone(zone, now=NOW)
        return store.get_zone(zone)[const.ZONE_EXPLANATION]

    async def test_it_names_the_silent_time_and_the_share_booked(self, coord):
        c, store = coord
        text = await self._explain(
            c,
            store,
            mappings={T: _sensor("sensor.t"), DEW: _sensor("sensor.dew")},
            outages=[_outage(2, 10, fields=(T, DEW))],
        )
        assert (
            "No values from Dewpoint, Temperature from 2026-07-01 05:00 to "
            "2026-07-01 10:00 (sensor silent)." in text
        )
        assert "Evapotranspiration booked for 79 % of the period." in text
        assert text.index("(sensor silent)") < text.index("Bucket was")

    async def test_each_span_gets_its_own_sentence(self, coord):
        c, store = coord
        text = await self._explain(c, store, outages=[_outage(0, 5), _outage(10, 16)])
        assert text.count("(sensor silent)") == 2
        assert "2026-07-01 13:00 to 2026-07-01 16:00" in text

    async def test_a_field_the_module_does_without_gets_no_share_sentence(self, coord):
        c, store = coord
        text = await self._explain(
            c,
            store,
            mappings={T: _sensor("sensor.t"), SUN: _sensor("sensor.sun")},
            readings=_hours(**{T: 20.0, SUN: 10.0}),
            outages=[_outage(2, 10, fields=(SUN,))],
        )
        assert "No values from Solar radiation" in text
        assert "% of the period" not in text

    async def test_a_static_zone_names_the_time_but_no_share(self, coord):
        c, store = coord
        text = await self._explain(c, store, module="Static", outages=[_outage(2, 10)])
        assert "(sensor silent)" in text
        assert "% of the period" not in text

    async def test_a_group_that_keeps_gets_no_sentence(self, coord):
        c, store = coord
        text = await self._explain(c, store, setting="keep", outages=[_outage(2, 10)])
        assert "(sensor silent)" not in text
```

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py -k TestTheExplanation -p _local_socket_unblock -q`
Expected: 4 FAIL (`assert '... (sensor silent).' in '...'`), `test_a_group_that_keeps_gets_no_sentence` grün.

- [x] **Step 3: Die Sätze** — in `calculate_module` direkt nach dem Kc-Block (dem `if kc != const.CONF_DEFAULT_KC:`
  mit `crop-coefficient-applied`) und vor `explanation += (await localize("module.calculation.explanation.bucket-was", …`
  einfügen:

```python
        if blocked:
            explanation += await self._silent_sensor_explanation(blocked, share)
```

  und direkt nach `calculate_module` (auf `6a40e083` das letzte Mitglied, also ans Dateiende) die Methode:

```python
    async def _silent_sensor_explanation(self, blocked, share) -> str:
        """The sentences that say what a pausing group did not book, and how much it did.

        One per blocked span, the fields silent over the same span named
        together; the share only where the module's own fields were cut. Times
        are on HA's clock, the frame of the buffer stamps.
        """
        language = self.hass.config.language
        sentence = await localize(
            "module.calculation.explanation.sensor-outage", language
        )
        fields_by_span: dict = {}
        for field, spans in blocked.items():
            for span in spans:
                fields_by_span.setdefault(span, []).append(field)
        text = ""
        for (start, end), fields in sorted(fields_by_span.items()):
            names = [
                await localize(
                    f"panels.mappings.cards.mapping.items.{field.lower()}", language
                )
                for field in sorted(fields)
            ]
            text += " " + (
                sentence.replace("{fields}", ", ".join(names))
                .replace("{start}", start.strftime("%Y-%m-%d %H:%M"))
                .replace("{end}", end.strftime("%Y-%m-%d %H:%M"))
            )
        if share is not None and share < 1:
            booked = await localize(
                "module.calculation.explanation.sensor-outage-share", language
            )
            text += " " + booked.replace("{share}", f"{share * 100:.0f}")
        return text
```

- [x] **Step 4: Übersetzungen** — in jeder der 8 Dateien `frontend/localize/languages/<lang>.json` bekommt die Zeile
  `"crop-coefficient-applied": "…"` ein Komma, und direkt danach (gleiche Einrückung) folgen die zwei Zeilen:

| Sprache | `sensor-outage` | `sensor-outage-share` |
|---|---|---|
| en | `No values from {fields} from {start} to {end} (sensor silent).` | `Evapotranspiration booked for {share} % of the period.` |
| de | `Keine Werte von {fields} von {start} bis {end} (Sensor stumm).` | `Verdunstung für {share} % des Zeitraums gebucht.` |
| es | `Sin valores de {fields} desde {start} hasta {end} (sensor sin informar).` | `Evapotranspiración contabilizada para el {share} % del periodo.` |
| fr | `Aucune valeur de {fields} du {start} au {end} (capteur muet).` | `Évapotranspiration comptée pour {share} % de la période.` |
| it | `Nessun valore da {fields} dal {start} al {end} (sensore muto).` | `Evapotraspirazione conteggiata per il {share} % del periodo.` |
| nl | `Geen waarden van {fields} van {start} tot {end} (sensor stil).` | `Verdamping geboekt voor {share} % van de periode.` |
| no | `Ingen verdier fra {fields} fra {start} til {end} (sensoren er stille).` | `Fordampning bokført for {share} % av perioden.` |
| sk | `Žiadne hodnoty z {fields} od {start} do {end} (senzor nehlási).` | `Evapotranspirácia započítaná za {share} % obdobia.` |

  Beispiel `en.json`:

```json
        "crop-coefficient-applied": "Scaled by the crop coefficient",
        "sensor-outage": "No values from {fields} from {start} to {end} (sensor silent).",
        "sensor-outage-share": "Evapotranspiration booked for {share} % of the period."
```

- [x] **Step 5: Test laufen lassen, er muss grün sein; i18n bleibt grün**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_i18n_completeness.py -p _local_socket_unblock -q`
Expected: alle grün.

- [x] **Step 6: Lint und Commit** (das Bundle wird in Task 8 neu gebaut, zusammen mit den Panel-Texten)

```bash
uvx black custom_components/irrigation_plus/ tests/test_silent_sensor_commit.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/frontend/localize/languages/ tests/test_silent_sensor_commit.py
git commit -F - <<'EOF'
feat(calculation): the explanation names a silent sensor's time

A pausing group's zone explanation says, for each blocked span, which
fields had no values from when to when, and, where the module's own
fields were cut, the share of the window it booked. Groups that keep
get no sentence. Eight languages.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Der Hinweis sagt, was die Gruppe tut

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (`_async_check_mapping_liveness` Log `:454-462`; `_sync_stale_issue` `:484-500`; neue Methoden nach `_sync_stale_issue`)
- Modify: `custom_components/irrigation_plus/__init__.py` (`async_update_config` nach `await self.store.async_update_config(data)`, `:1245`; `async_update_mapping_config` vor dem abschließenden `async_dispatcher_send(… "_config_updated", mapping_id)`, `:1842-1844`)
- Modify: `custom_components/irrigation_plus/translations/{de,en,es,fr,it,nl,no,sk}.json` (Block `issues`, nach `weather_sensor_stale`)
- Test: `tests/test_sensor_liveness_coordinator.py` (Klasse anhängen)

**Interfaces:**
- Consumes: `group_pauses` (Task 1), `hourly_calculation_enabled` (`calculation.py:87`, im Methodenrumpf importiert:
  `calculation` importiert `sensor_liveness`).
- Produces: `SensorLivenessMixin._group_cuts(mapping: dict) -> bool`, `_stale_issue_key(mapping_id) -> str`,
  `async_resync_stale_issue(mapping: dict | None) -> None`. `_sync_stale_issue(mapping_id, name, outages)` behält
  seine Signatur (ein bestehender Test umhüllt sie, `test_sensor_liveness_coordinator.py:641-648`).

- [x] **Step 1: Failing test schreiben** — an `tests/test_sensor_liveness_coordinator.py` anhängen:

```python
def _pausing(group):
    group[const.MAPPING_ON_SILENT_SENSOR] = const.ON_SILENT_SENSOR_PAUSE
    return group


def _hourly(on):
    return SimpleNamespace(**{const.CONF_HOURLY_CALCULATION: on})


class TestThePausedNotice:
    async def _silent(self, monkeypatch, group, *, hourly=None):
        last = T0 - STALE - timedelta(seconds=1)
        coord, store, issues = _coord(
            monkeypatch,
            [group],
            {"sensor.temp": _state("sensor.temp", "21.5", last)},
            {"dev1": ["sensor.temp"]},
        )
        if hourly is not None:
            store.config = _hourly(hourly)
        await coord.async_check_sensor_liveness(now=T0)
        return issues.open["weather_sensor_stale_1"]["translation_key"]

    async def test_a_pausing_group_says_its_values_are_no_longer_used(
        self, monkeypatch, caplog
    ):
        group = _pausing(_group(fields={"Temperature": "sensor.temp"}))
        key = await self._silent(monkeypatch, group)
        assert key == const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
        assert "no longer used" in caplog.text
        assert "still used" not in caplog.text

    async def test_under_the_hourly_calculation_its_values_are_still_used(
        self, monkeypatch, caplog
    ):
        group = _pausing(_group(fields={"Temperature": "sensor.temp"}))
        key = await self._silent(monkeypatch, group, hourly=True)
        assert key == const.ISSUE_WEATHER_SENSOR_STALE
        assert "still used" in caplog.text

    async def test_changing_the_setting_rewrites_the_open_notice(self, monkeypatch):
        coord, _, issues = _mock_store_coord(
            monkeypatch, _pausing(_sensor_group_zero("sensor.old"))
        )
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_mapping_config(
                0, {const.MAPPING_ON_SILENT_SENSOR: const.ON_SILENT_SENSOR_PAUSE}
            )
        assert issues.open["weather_sensor_stale_0"]["translation_key"] == (
            const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
        )

    async def test_a_rename_leaves_the_notice_alone(self, monkeypatch):
        coord, _, issues = _mock_store_coord(
            monkeypatch, _pausing(_sensor_group_zero("sensor.old"))
        )
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_mapping_config(0, {const.MAPPING_NAME: "renamed"})
        assert issues.open["weather_sensor_stale_0"] == {}

    async def test_switching_the_hourly_calculation_rewrites_open_notices(
        self, monkeypatch
    ):
        group = _pausing(_sensor_group_zero("sensor.old"))
        coord, store, issues = _mock_store_coord(monkeypatch, group)
        store.async_update_config = AsyncMock()
        store.async_get_mappings = AsyncMock(return_value=[group])

        store.config = _hourly(True)
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_config({const.CONF_HOURLY_CALCULATION: True})
        assert issues.open["weather_sensor_stale_0"]["translation_key"] == (
            const.ISSUE_WEATHER_SENSOR_STALE
        )

        store.config = _hourly(False)
        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
            await coord.async_update_config({const.CONF_HOURLY_CALCULATION: False})
        assert issues.open["weather_sensor_stale_0"]["translation_key"] == (
            const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
        )

    async def test_a_group_without_an_open_outage_is_not_asked_about(
        self, monkeypatch
    ):
        group = _pausing(_sensor_group_zero("sensor.old"))
        group[const.MAPPING_SENSOR_OUTAGES] = [CLOSED_RECORD]
        coord, _, _ = _mock_store_coord(monkeypatch, group)
        monkeypatch.setattr(
            sensor_liveness,
            "_issue_registry",
            Mock(side_effect=AssertionError("issue registry asked")),
        )
        coord.async_resync_stale_issue(group)
        coord.async_resync_stale_issue(None)
```

  `CLOSED_RECORD` steht bereits in der Datei (`:752`), ebenso `_coord`, `_group`, `_state`, `_mock_store_coord`,
  `_sensor_group_zero`, `T0`, `STALE`, `SimpleNamespace`, `AsyncMock`, `patch`.

- [x] **Step 2: Test laufen lassen, er muss scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_coordinator.py -k TestThePausedNotice -p _local_socket_unblock -q`
Expected: FAIL — falscher `translation_key`, fehlender Log-Text, `AttributeError: … 'async_resync_stale_issue'`.
`test_under_the_hourly_calculation…` und `test_a_rename…` sind schon grün.

- [x] **Step 3: Variante wählen** — in `_sync_stale_issue` die Zeile
  `translation_key=const.ISSUE_WEATHER_SENSOR_STALE,` ersetzen durch `translation_key=self._stale_issue_key(mapping_id),`
  und direkt nach `_sync_stale_issue` einfügen:

```python
    def _group_cuts(self, mapping: dict) -> bool:
        """Whether this group's daily calculation leaves a silent sensor's time out.

        A pausing group, and only without the hourly calculation (see
        calculation._blocked_spans_for_zone); every other group still uses the
        last value.
        """
        # Imported here: calculation imports this module.
        from .calculation import hourly_calculation_enabled

        return group_pauses(mapping) and not hourly_calculation_enabled(self.store)

    def _stale_issue_key(self, mapping_id) -> str:
        """The notice's text: the paused one where the group's values are cut."""
        mapping = self.store.get_mapping(mapping_id) or {}
        if self._group_cuts(mapping):
            return const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
        return const.ISSUE_WEATHER_SENSOR_STALE

    def async_resync_stale_issue(self, mapping: dict | None) -> None:
        """Bring a group's open notice in line with its setting and the calculation form.

        Called when either changes; otherwise the notice is touched only when an
        outage opens or closes. A group without an open outage has no notice.
        """
        if not mapping:
            return
        outages = outages_of(mapping)
        if not any(o.end is None for o in outages):
            return
        mapping_id = mapping[const.MAPPING_ID]
        self._sync_stale_issue(
            mapping_id, mapping.get(const.MAPPING_NAME) or str(mapping_id), outages
        )
```

- [x] **Step 4: Log-Text** — in `_async_check_mapping_liveness` den Block

```python
        for outage in opened:
            _LOGGER.warning(
                "Sensor group %s: %s (%s) has not reported since %s; its last "
                "value is still used",
```

  ersetzen durch

```python
        cuts = self._group_cuts(mapping) if opened else False
        for outage in opened:
            _LOGGER.warning(
                (
                    "Sensor group %s: %s (%s) has not reported since %s; its values "
                    "are no longer used and no evapotranspiration is booked while it "
                    "is silent"
                    if cuts
                    else "Sensor group %s: %s (%s) has not reported since %s; its last "
                    "value is still used"
                ),
```

  (die vier Argumente `name, outage.entity_id, ", ".join(outage.fields), outage.start,` bleiben).

- [x] **Step 5: Auslöser** — `__init__.py`:
  - in `async_update_config` direkt nach `await self.store.async_update_config(data)`:

```python
        if const.CONF_HOURLY_CALCULATION in data:
            # A pausing group's notice says whether its values are left out,
            # and only the daily form leaves them out.
            for mapping in await self.store.async_get_mappings():
                self.async_resync_stale_issue(mapping)
```

  - in `async_update_mapping_config`, Zweig „modify a mapping“, direkt vor
    `async_dispatcher_send(self.hass, const.DOMAIN + "_config_updated", mapping_id)`:

```python
            if const.MAPPING_ON_SILENT_SENSOR in data:
                # The open notice says whether the group's values are still used.
                self.async_resync_stale_issue(self.store.get_mapping(mapping_id))
```

- [x] **Step 6: Übersetzungen** — in `translations/<lang>.json` nach dem Block `"weather_sensor_stale": {…}` (Komma
  setzen) den Block `"weather_sensor_stale_paused"` einfügen. Der Titel ist in jeder Sprache **wörtlich der von
  `weather_sensor_stale`**; die Beschreibungen (Absätze mit `\n\n` getrennt, Anführungszeichen wie in derselben Datei):

  - **en:** `Irrigation Plus has not heard from {entities} since {since}. After three hours of silence these values are no longer used, and no evapotranspiration is booked for the time without values; zones that depend on them therefore water less or not at all until new values arrive.\n\nCheck the device and its integration. If you replaced the device, select its new entities in the sensor group. If the value is meant to be fixed, use the \"Static value\" source instead. If the integration only updates every few hours, set the sensor group to \"Keep the last value\"; otherwise part of the time is missing at every update.\n\nThis notice clears itself when the sensor reports again.`
  - **de:** `Irrigation Plus hat seit {since} nichts mehr von {entities} gehört. Nach drei Stunden Stille werden diese Werte nicht mehr verwendet, und für die Zeit ohne Werte wird keine Verdunstung gebucht; Zonen, die davon abhängen, wässern deshalb weniger oder gar nicht, bis wieder Werte kommen.\n\nPrüfe das Gerät und seine Integration. Hast du das Gerät ersetzt, wähle seine neuen Entitäten in der Sensorgruppe. Soll der Wert fest sein, nutze stattdessen die Quelle „Fester Wert“. Aktualisiert die Integration nur alle paar Stunden, stelle die Sensorgruppe auf „Letzten Wert behalten“, sonst fehlt bei jedem Update ein Teil der Zeit.\n\nDieser Hinweis verschwindet von selbst, sobald der Sensor wieder meldet.`
  - **es:** `Irrigation Plus no tiene noticias de {entities} desde {since}. Tras tres horas sin datos, esos valores dejan de usarse y no se contabiliza evapotranspiración para el tiempo sin valores; por eso las zonas que dependen de ellos riegan menos o nada hasta que lleguen valores nuevos.\n\nRevisa el dispositivo y su integración. Si has sustituido el dispositivo, selecciona sus nuevas entidades en el grupo de sensores. Si el valor debe ser fijo, usa en su lugar la fuente «Valor estático». Si la integración solo se actualiza cada pocas horas, pon el grupo de sensores en «Mantener el último valor»; si no, en cada actualización falta una parte del tiempo.\n\nEste aviso desaparece por sí solo cuando el sensor vuelve a informar.`
  - **fr:** `Irrigation Plus n’a plus de nouvelles de {entities} depuis {since}. Après trois heures de silence, ces valeurs ne sont plus utilisées et aucune évapotranspiration n’est comptée pour le temps sans valeurs : les zones qui en dépendent arrosent donc moins, voire pas du tout, jusqu’à l’arrivée de nouvelles valeurs.\n\nVérifiez l’appareil et son intégration. Si vous avez remplacé l’appareil, sélectionnez ses nouvelles entités dans le groupe de capteurs. Si la valeur doit rester fixe, utilisez plutôt la source « Valeur statique ». Si l’intégration ne se met à jour qu’à quelques heures d’intervalle, réglez le groupe de capteurs sur « Garder la dernière valeur » ; sinon, une partie du temps manque à chaque mise à jour.\n\nCet avis disparaît de lui-même dès que le capteur envoie de nouveau des mesures.`
  - **it:** `Irrigation Plus non riceve notizie da {entities} dal {since}. Dopo tre ore di silenzio questi valori non vengono più usati e per il tempo senza valori non si conteggia evapotraspirazione; per questo le zone che ne dipendono irrigano meno o per niente finché non arrivano nuovi valori.\n\nControlla il dispositivo e la sua integrazione. Se hai sostituito il dispositivo, seleziona le sue nuove entità nel gruppo di sensori. Se il valore deve restare fisso, usa invece la fonte «Valore statico». Se l’integrazione si aggiorna solo ogni poche ore, imposta il gruppo di sensori su «Mantieni l’ultimo valore»: altrimenti a ogni aggiornamento manca una parte del tempo.\n\nQuesto avviso scompare da solo quando il sensore torna a inviare dati.`
  - **nl:** `Irrigation Plus heeft sinds {since} niets meer van {entities} gehoord. Na drie uur stilte worden deze waarden niet meer gebruikt en wordt voor de tijd zonder waarden geen verdamping geboekt; zones die ervan afhangen, beregenen daardoor minder of helemaal niet tot er nieuwe waarden binnenkomen.\n\nControleer het apparaat en de integratie ervan. Heb je het apparaat vervangen, kies dan de nieuwe entiteiten ervan in de sensorgroep. Moet de waarde vast zijn, gebruik dan de bron ‘Vaste waarde’. Werkt de integratie maar om de paar uur bij, zet de sensorgroep dan op ‘Laatste waarde behouden’, anders ontbreekt bij elke update een deel van de tijd.\n\nDeze melding verdwijnt vanzelf zodra de sensor weer meldt.`
  - **no:** `Irrigation Plus har ikke hørt fra {entities} siden {since}. Etter tre timer uten signal brukes ikke disse verdiene lenger, og det bokføres ingen fordampning for tiden uten verdier; soner som er avhengige av dem, vanner derfor mindre eller ikke i det hele tatt til nye verdier kommer inn.\n\nSjekk enheten og integrasjonen. Har du byttet ut enheten, velg de nye entitetene i sensorgruppen. Hvis verdien skal være fast, bruk heller kilden «Statisk verdi». Oppdateres integrasjonen bare med noen timers mellomrom, sett sensorgruppen til «Behold siste verdi», ellers mangler en del av tiden ved hver oppdatering.\n\nDenne meldingen forsvinner av seg selv når sensoren rapporterer igjen.`
  - **sk:** `Irrigation Plus od {since} nedostal nič od {entities}. Po troch hodinách ticha sa tieto hodnoty prestanú používať a za čas bez hodnôt sa nezapočíta žiadna evapotranspirácia; zóny, ktoré od nich závisia, preto zavlažujú menej alebo vôbec, kým neprídu nové hodnoty.\n\nSkontroluj zariadenie a jeho integráciu. Ak si zariadenie vymenil, vyber jeho nové entity v skupine senzorov. Ak má byť hodnota pevná, použi namiesto toho zdroj „Statická hodnota“. Ak sa integrácia aktualizuje len raz za niekoľko hodín, nastav skupinu senzorov na „Ponechať poslednú hodnotu“, inak pri každej aktualizácii chýba časť času.\n\nToto upozornenie zmizne samo, keď senzor znova začne hlásiť hodnoty.`

  Die Optionsnamen in Anführungszeichen sind die Panel-Beschriftungen aus Task 8.

- [x] **Step 7: Test laufen lassen, er muss grün sein; die Nachbarn bleiben grün**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_repair.py tests/test_sensor_liveness.py tests/test_i18n_completeness.py tests/test_mapping_source_change.py -p _local_socket_unblock -q`
Expected: alle grün (6 neue Fälle).

- [x] **Step 8: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_sensor_liveness_coordinator.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/__init__.py custom_components/irrigation_plus/translations/ tests/test_sensor_liveness_coordinator.py
git commit -F - <<'EOF'
feat(liveness): the notice says whether a silent sensor's values are used

A pausing group whose daily calculation leaves a silent sensor's time
out gets its own notice text and log line, saying the values are no
longer used and what to choose for an integration that updates only
every few hours. Every other group keeps the text it had. The open
notice follows when the group's setting or the hourly calculation is
switched. Eight languages.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---
### Task 8: View-Schema, Panel-Auswahl, Bundle

**Files:**
- Modify: `custom_components/irrigation_plus/websockets.py` (`SmartIrrigationMappingView`, `:229-250`)
- Modify: `custom_components/irrigation_plus/frontend/src/types.ts` (`SmartIrrigationMapping`, `:421-432`)
- Modify: `custom_components/irrigation_plus/frontend/src/views/mappings/view-mappings.ts` (`saveToHA` `:376-380`; `renderMappingCard` `:1045-1046`; neue Methode nach `renderMappingCard`)
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json` (Block `panels.mappings.cards.mapping`)
- Modify: `custom_components/irrigation_plus/frontend/dist/` (4 Bundles, neu gebaut)
- Test: `tests/test_silent_sensor_setting.py` (Test anhängen), `frontend/src/views/mappings/view-mappings-save.test.ts` (zwei `it` anhängen)

**Interfaces:**
- Consumes: `const.MAPPING_ON_SILENT_SENSOR`, `const.ON_SILENT_SENSOR_OPTIONS` (Task 1); Store-Feld (Task 2).
- Produces: `websockets.MAPPING_VIEW_SCHEMA` (das Schema der Mapping-View als Modul-Konstante); TS-Feld
  `SmartIrrigationMapping.on_silent_sensor?: string`; i18n-Block `panels.mappings.cards.mapping.on-silent-sensor`
  mit `title`, `help`, `keep`, `pause`.

- [x] **Step 1: Failing tests schreiben**

  An `tests/test_silent_sensor_setting.py` anhängen (Import `import voluptuous as vol` oben ergänzen):

```python
def test_the_mapping_view_takes_the_setting_and_only_its_two_values():
    from custom_components.irrigation_plus.websockets import MAPPING_VIEW_SCHEMA

    assert MAPPING_VIEW_SCHEMA({KEY: "pause"}) == {KEY: "pause"}
    assert MAPPING_VIEW_SCHEMA({KEY: "keep"}) == {KEY: "keep"}
    with pytest.raises(vol.Invalid):
        MAPPING_VIEW_SCHEMA({KEY: "sometimes"})
```

  In `view-mappings-save.test.ts` am Ende des `describe("a sensor group edit is saved", …)`-Blocks anhängen:

```ts
  it("saves the setting for a silent sensor with the group", () => {
    const { el, callApi } = make([
      { ...group(1, "Garden"), on_silent_sensor: "pause" },
    ]);
    el.handleEditMapping(0, {
      ...group(1, "Garden"),
      on_silent_sensor: "keep",
    });
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      { ...group(1, "Garden"), on_silent_sensor: "keep" },
    ]);
  });

  it("sends no setting for a copy that does not carry one", () => {
    const { el, callApi } = make([group(1, "Garden")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    vi.advanceTimersByTime(500);
    expect(Object.keys(saved(callApi)[0])).toEqual(["id", "name", "mappings"]);
  });
```

- [x] **Step 2: Tests laufen lassen, sie müssen scheitern**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_setting.py -p _local_socket_unblock -q`
Expected: FAIL `ImportError: cannot import name 'MAPPING_VIEW_SCHEMA'`.

Run: `cd custom_components/irrigation_plus/frontend && npx vitest run src/views/mappings/view-mappings-save.test.ts`
Expected: „saves the setting for a silent sensor with the group“ FAIL (die Einstellung fehlt im gesendeten Körper);
„sends no setting …“ ist schon grün (er hält fest, dass kein leerer Schlüssel mitgeht).

- [x] **Step 3: Schema** — in `websockets.py` das Schema aus dem Dekorator von `SmartIrrigationMappingView.post` als
  Modul-Konstante direkt vor `class SmartIrrigationMappingView` herausziehen und um die Einstellung ergänzen:

```python
# What the panel may send for a sensor group: its name, its fields and what it does
# with a silent sensor. The server-computed fields are accepted and stripped below,
# so older frontends do not fail validation.
MAPPING_VIEW_SCHEMA = vol.Schema(
    {
        vol.Optional(const.MAPPING_ID): vol.Coerce(int),
        vol.Optional(const.MAPPING_NAME): cv.string,
        vol.Optional(const.MAPPING_MAPPINGS): vol.Coerce(dict),
        vol.Optional(const.MAPPING_ON_SILENT_SENSOR): vol.In(
            const.ON_SILENT_SENSOR_OPTIONS
        ),
        vol.Optional(const.ATTR_REMOVE): cv.boolean,
        vol.Optional(const.MAPPING_DATA): object,
        vol.Optional(const.MAPPING_DATA_LAST_UPDATED): object,
        vol.Optional(const.MAPPING_DATA_LAST_ENTRY): object,
        vol.Optional(const.MAPPING_DATA_LAST_CALCULATION): object,
    }
)
```

  und den Dekorator auf `@RequestDataValidator(MAPPING_VIEW_SCHEMA)` setzen (der bisherige Kommentar zu den
  Server-Feldern steht jetzt über der Konstante).

- [x] **Step 4: Typ** — in `types.ts`, Klasse `SmartIrrigationMapping`, nach `data?: any[];`:

```ts
  on_silent_sensor?: string;
```

- [x] **Step 5: Speichern** — in `view-mappings.ts`, `saveToHA`, die zwei Zeilen

```ts
    const { id, name, mappings } = mapping;
    await saveMapping(this.hass, { id, name, mappings });
```

  ersetzen durch

```ts
    const { id, name, mappings, on_silent_sensor } = mapping;
    await saveMapping(this.hass, {
      id,
      name,
      mappings,
      // Absent on a copy made before the server sent it: the server then keeps
      // what it has, and a group created now pauses by default.
      ...(on_silent_sensor === undefined ? {} : { on_silent_sensor }),
    });
```

- [x] **Step 6: Auswahl** — in `renderMappingCard` zwischen dem schließenden `</ha-settings-row>` der Namenszeile und
  `${this.renderMappingSettings(mapping, index)}` die Zeile `${this.renderOnSilentSensor(mapping, index)}` einfügen,
  und nach `renderMappingCard` die Methode:

```ts
  private renderOnSilentSensor(
    mapping: SmartIrrigationMapping,
    index: number,
  ): TemplateResult {
    if (!this.hass) {
      return html``;
    }
    const language = this.hass.language;
    // A group the server has not sent back yet is a new one, and a new group pauses.
    const value = mapping.on_silent_sensor ?? "pause";
    return html`
      <ha-settings-row>
        <span slot="heading"
          >${localize(
            "panels.mappings.cards.mapping.on-silent-sensor.title",
            language,
          )}</span
        >
        <span slot="description"
          >${localize(
            "panels.mappings.cards.mapping.on-silent-sensor.help",
            language,
          )}</span
        >
        <select
          id="on_silent_sensor${mapping.id}"
          class="settings-input"
          @change="${(e: Event) =>
            this.handleEditMapping(index, {
              ...mapping,
              on_silent_sensor: (e.target as HTMLSelectElement).value,
            })}"
        >
          ${["pause", "keep"].map(
            (option) =>
              html`<option value="${option}" ?selected="${value === option}">
                ${localize(
                  `panels.mappings.cards.mapping.on-silent-sensor.${option}`,
                  language,
                )}
              </option>`,
          )}
        </select>
      </ha-settings-row>
    `;
  }
```

- [x] **Step 7: Beschriftungen** — in jeder `frontend/localize/languages/<lang>.json` im Block
  `panels.mappings.cards.mapping` nach dem Block `"items": {…}` (Komma setzen):

```json
          "on-silent-sensor": {
            "title": "…",
            "help": "…",
            "keep": "…",
            "pause": "…"
          },
```

| Sprache | `title` | `keep` | `pause` | `help` |
|---|---|---|---|---|
| en | When a sensor goes silent | Keep the last value | Pause | Pause: after 3 hours without a report, the sensor's values are no longer used and no evapotranspiration is booked for that time. Applies only without the hourly calculation. |
| de | Wenn ein Sensor verstummt | Letzten Wert behalten | Pausieren | Pausieren: Nach 3 Stunden ohne Meldung werden die Werte des Sensors nicht mehr verwendet, und für diese Zeit wird keine Verdunstung gebucht. Gilt nur ohne stündliche Berechnung. |
| es | Cuando un sensor deja de informar | Mantener el último valor | Pausar | Pausar: tras 3 horas sin informar, los valores del sensor dejan de usarse y no se contabiliza evapotranspiración para ese tiempo. Solo se aplica sin el cálculo por horas. |
| fr | Quand un capteur se tait | Garder la dernière valeur | Mettre en pause | Mettre en pause : après 3 heures sans mesure, les valeurs du capteur ne sont plus utilisées et aucune évapotranspiration n’est comptée pour cette durée. Ne s’applique que sans le calcul horaire. |
| it | Quando un sensore smette di inviare dati | Mantieni l’ultimo valore | Metti in pausa | Metti in pausa: dopo 3 ore senza dati, i valori del sensore non vengono più usati e per quel tempo non si conteggia evapotraspirazione. Vale solo senza il calcolo orario. |
| nl | Als een sensor stil valt | Laatste waarde behouden | Pauzeren | Pauzeren: na 3 uur zonder melding worden de waarden van de sensor niet meer gebruikt en wordt voor die tijd geen verdamping geboekt. Geldt alleen zonder de berekening per uur. |
| no | Når en sensor blir stille | Behold siste verdi | Sett på pause | Sett på pause: etter 3 timer uten rapport brukes ikke sensorens verdier lenger, og det bokføres ingen fordampning for den tiden. Gjelder bare uten timesberegningen. |
| sk | Keď senzor prestane hlásiť | Ponechať poslednú hodnotu | Pozastaviť | Pozastaviť: po 3 hodinách bez hlásenia sa hodnoty senzora prestanú používať a za tento čas sa nezapočíta žiadna evapotranspirácia. Platí len bez hodinového výpočtu. |

  Die Optionsnamen müssen wörtlich zu den Anführungen im Hinweis aus Task 7 passen.

- [x] **Step 8: Tests laufen lassen, sie müssen grün sein**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_setting.py tests/test_i18n_completeness.py -p _local_socket_unblock -q`
Expected: alle grün.

Run: `cd custom_components/irrigation_plus/frontend && npx vitest run`
Expected: alle grün (2 neue Fälle in `view-mappings-save.test.ts`).

- [x] **Step 9: Bundle bauen** (Node 24 reproduziert die CI byte-genau)

```bash
cd /d/Entwicklung/HASI/issue8-pr2-work/wt/custom_components/irrigation_plus/frontend && npm run build
cd /d/Entwicklung/HASI/issue8-pr2-work/wt && git status --short custom_components/irrigation_plus/frontend/dist/
```

Expected: `npm run build` ohne Lint-Fehler; `git status` zeigt die 4 Bundles als geändert, aber nur
`irrigation-plus.js` und `irrigation-plus-card-impl.js` ändern sich inhaltlich (im Probelauf waren `-card.js` und
`-card-legacy.js` byte-gleich mit HEAD; sie erscheinen nur wegen der Zeilenenden).

- [x] **Step 10: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_silent_sensor_setting.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/websockets.py custom_components/irrigation_plus/frontend/src/ custom_components/irrigation_plus/frontend/localize/languages/ tests/test_silent_sensor_setting.py
git add -f custom_components/irrigation_plus/frontend/dist/
git diff --cached --name-only | grep -c "frontend/dist/"
```

Expected: `2` (die zwei inhaltlich geänderten Bundles, Probelauf). Weicht die Zahl ab: je Bundle per
`git diff --cached --stat` prüfen, ob sie zum Bau passt, bevor committet wird. Dann:

```bash
git commit -F - <<'EOF'
feat(panel): choose per sensor group what happens to a silent sensor

The sensor group card gets a choice between pausing a silent sensor and
keeping its last value, with a line on what pausing does and that it
applies without the hourly calculation. The panel sends the choice with
the group when it has one; the mapping view accepts exactly the two
values. Eight languages; the bundles are rebuilt.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Doku und die Kommentare der Live-Schätzung

**Files:**
- Modify: `docs/configuration-sensor-groups.md` (Abschnitt „When a sensor goes silent“, `:54-61`)
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Docstring `:590-596`, Kommentar `:617-619`)

**Interfaces:** keine.

Kein automatischer Test (Doku und Kommentare). **Kriterium vorab:** Der Satz „Meanwhile the calculation keeps using the
sensor's last value.“ steht nicht mehr im Abschnitt; `grep -n "Keep the last value" docs/configuration-sensor-groups.md`
findet die neue Liste; `grep -n "pausing" custom_components/irrigation_plus/live_estimate.py` zeigt an beiden Stellen den
Zusatz; volle Suite unverändert (Task 10).

- [x] **Step 1: Doku** (Wortlaut zur Freigabe mit diesem Plan; deutsch zur Prüfung, englisch in die Datei)

  Deutsch:

  > Sobald ein Sensor drei Stunden lang nichts gemeldet hat, zeigt Irrigation Plus einen Reparaturhinweis für seine
  > Sensorgruppe und feuert das Event `irrigation_plus_weather_stale` (siehe Events). Meldet der Sensor wieder,
  > verschwindet der Hinweis von selbst, und ein zweites Event markiert das Ende. Was die Berechnung in der Zwischenzeit
  > tut, hängt von der Einstellung **Wenn ein Sensor verstummt** der Sensorgruppe ab:
  >
  > - **Pausieren** (Standard für jede neu angelegte Sensorgruppe): Ab drei Stunden nach der letzten Meldung bis zur
  >   nächsten werden die Werte des Sensors nicht mehr verwendet, und die tägliche Berechnung bucht für diese Zeit keine
  >   Verdunstung. Regen aus einem summierenden Regenmesser zählt weiter voll, denn was der Messer nach seiner Rückkehr
  >   anzeigt, wurde gemessen, nur spät übertragen. Zonen, die vom stummen Sensor abhängen, wässern deshalb weniger oder
  >   gar nicht, bis er wieder meldet. Die Erklärung der Berechnung nennt die stumme Zeit und den gebuchten Anteil.
  > - **Letzten Wert behalten** (Einstellung jeder schon vorhandenen Sensorgruppe): Die Berechnung verwendet weiter den
  >   letzten Wert des Sensors, wie bisher.
  >
  > Pausieren wirkt nur ohne die stündliche Berechnung; mit ihr wird der letzte Wert weiter verwendet. Mit der
  > Live-Schätzung kann ein Lauf während eines Ausfalls mit mehr Verdunstung bemessen werden, als die Berechnung danach
  > bucht. Die tägliche Berechnung mittelt einen pausierenden Sensor über die Stunden, in denen er gemeldet hat; welcher
  > Teil des Tages fehlte, kann das Ergebnis deshalb verschieben.
  >
  > (an den bestehenden Absatz zu den festen drei Stunden angehängt:) Bei **Pausieren** stelle eine solche
  > Sensorgruppe auf **Letzten Wert behalten**, sonst wird ein Teil der Zeit zwischen ihren Updates nie gebucht.

  Englisch, in die Datei: der bisherige zweite Absatz (`:57`) wird durch die folgenden ersetzt, der dritte Absatz
  (`:59`, die festen drei Stunden) bekommt den letzten Satz angehängt; der vierte Absatz (`:61`) bleibt:

```markdown
Once a sensor has not reported for three hours, Irrigation Plus shows a repair notice for its sensor group and fires the `irrigation_plus_weather_stale` event (see [Events](usage-events.md)). When the sensor reports again, the notice clears itself and a second event marks the end. What the calculation does meanwhile depends on the sensor group's setting **When a sensor goes silent**:

- **Pause** (the default for a sensor group created from now on): from three hours after the sensor's last report until it reports again, its values are no longer used, and the daily calculation books no evapotranspiration for that time. Rain from a cumulative rain gauge still counts in full, because what the gauge reads after its return was measured, only delivered late. Zones that depend on the silent sensor therefore water less, or not at all, until it reports again. The explanation of the calculation names the silent time and the share that was booked.
- **Keep the last value** (the setting of every sensor group that existed before): the calculation keeps using the sensor's last value, as it always did.

Pausing applies only without the hourly calculation; with it, the last value is still used. With the live estimate, a run during an outage can be sized on more evapotranspiration than the calculation books afterwards. The daily calculation averages a pausing sensor over the hours in which it reported, so which part of the day was missing can shift the result.

The three hours are fixed. An integration that updates less often, such as a cloud service polled every six hours, therefore raises the notice between its updates even though nothing has failed. With **Pause**, set such a sensor group to **Keep the last value**; otherwise part of the time between its updates is never booked.
```

- [x] **Step 2: Live-Schätzung** — in `live_estimate.py`:
  - im Docstring von `_aggregate_live_window` nach dem ersten Absatz (`:590-596`) einen Absatz anfügen:

```
        One difference is deliberate: a pausing sensor group's commit leaves a
        silent sensor's time out (calculation._blocked_spans_for_zone), and this
        estimate does not, so a run during an outage can be sized on more ET than
        the commit books afterwards.
```

  - den Kommentar „Must match _aggregate_for_zone exactly …“ (`:617-619`) um eine Zeile ergänzen:
    `# (Apart from a pausing group's blocked time; see the docstring.)`

- [x] **Step 3: Kriterium prüfen und Commit**

```bash
grep -c "Meanwhile the calculation keeps using" docs/configuration-sensor-groups.md   # 0
grep -n "Keep the last value" docs/configuration-sensor-groups.md                      # Liste + letzter Satz
grep -n "pausing" custom_components/irrigation_plus/live_estimate.py                   # beide Stellen
uvx black custom_components/irrigation_plus/
git add docs/configuration-sensor-groups.md custom_components/irrigation_plus/live_estimate.py
git commit -F - <<'EOF'
docs: what a sensor group does with a silent sensor

The section on silent sensors explains the two settings, their defaults,
that pausing applies without the hourly calculation, that the live
estimate does not cut, and what to choose for an integration that
updates only every few hours. The live estimate's comments no longer
claim it reduces the window exactly as the commit does.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Lint, volle Suite, Mutationen, Review

**Files:** keine Codeänderung (außer Befunden aus dem Review, je mit eigenem Commit).

- [x] **Step 1: Lint**

```bash
cd /d/Entwicklung/HASI/issue8-pr2-work/wt
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_sensor_liveness_blocked.py tests/test_silent_sensor_setting.py tests/test_weather_aggregate_blocked.py tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py tests/test_run_in_flight.py
```

Expected: black sauber. ruff: keine Funde in den geänderten Dateien. Mit ruff 0.17.0 meldet der Lauf 20 vorhandene
`UP017` in Dateien, die dieser Branch nicht anfasst (`forecast_window.py`, `weathermodules/*`; Probelauf); die bleiben
stehen. Vor dem Push prüfen, welche ruff-Version die CI nimmt, und dort sauber sein.

- [x] **Step 2: Volle Suite mit Namensvergleich**

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-pr2.txt 2>&1
tr '\r' '\n' < ../suite-pr2.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-pr2.txt
comm -23 ../names-baseline.txt ../names-pr2.txt | wc -l                                  # 0: nichts entfällt
grep "^FAILED" ../names-baseline.txt | diff - <(grep "^FAILED" ../names-pr2.txt) && echo "FAILED gleich"
comm -13 ../names-baseline.txt ../names-pr2.txt | sed -E 's/::.*//' | sort | uniq -c       # nur neue Teardown-ERROR
tail -c 400 ../suite-pr2.txt
```

Expected: `0`, `FAILED gleich`; neu hinzu kommen nur ERROR-Namen aus `tests/test_silent_sensor_commit.py` (im
Probelauf 28), und jeder davon ist ein Teardown-Fehler „Lingering timer“ eines grünen Tests (der echte Koordinator
lässt Timer stehen, lokales Muster wie `test_per_zone_consumption.py`); per
`grep -c "Lingering timer" ../suite-pr2.txt` gegen die Baseline gegenprüfen. `passed` = Baseline + 84 (15 + 11 + 23 +
29 + 6; Probelauf 3819 → 3903). `failed` wie die Baseline.

- [x] **Step 3: Frontend**

```bash
cd custom_components/irrigation_plus/frontend && npx vitest run && npm run build && cd ../../.. && git status --short custom_components/irrigation_plus/frontend/dist/
```

Expected: vitest grün; nach dem Bau **keine** Änderung an `dist/` (der committete Stand ist der gebaute).

- [x] **Step 4: Mutationen** — Skript nach Vorbild `D:\Entwicklung\HASI\issue66-work\mutate.py` (Timeout, Anker genau
  einmal, Sicherung `.bak` + sha256, Rücksetzen geprüft). Jede Mutation gegen die genannten Testdateien; jede muss
  sterben:

| # | Datei | Mutation | Erwarteter Killer |
|---|---|---|---|
| 1 | sensor_liveness.py | `outage.start + STALE_AFTER` → `outage.start` | `test_the_first_three_hours_are_bridged` |
| 2 | sensor_liveness.py | `if hi <= lo:` → `if hi < lo:` | `test_an_outage_of_three_hours_or_less_blocks_nothing` |
| 3 | sensor_liveness.py | `valid_share`: Vereinigung → kleinster Einzelanteil | `test_two_fields_silent_at_different_hours…` |
| 4 | sensor_liveness.py | `group_pauses`: `==` → Vergleich ohne Groß/Klein | `test_only_a_stored_pause_pauses` |
| 5 | weather_aggregate.py | `lo <= stamp < hi` → `lo <= stamp <= hi` | `test_the_reading_of_the_return_counts` |
| 6 | weather_aggregate.py | `t <= start or not _blocked_at(…)` → `not _blocked_at(…)` | `test_a_window_that_starts_blocked_holds_the_boundary…` |
| 7 | weather_aggregate.py | `_segment_weighted_mean`: `_held(kept, a)` → `kept[0][1]` | `test_a_value_is_not_held_into_a_span…` |
| 8 | weather_aggregate.py | `_riemann_over`: `valid` → `(t1 - t0).total_seconds()` | `test_a_rain_rate_is_integrated_over_its_valid_time_only` |
| 9 | weather_aggregate.py | `if not segments: return` entfernen | `test_a_field_blocked_throughout_is_left_out…` |
| 10 | weather_aggregate.py | `!= MAPPING_CONF_AGGREGATE_DELTA` → `True` | `test_a_rain_gauge_is_never_cut_even_if_asked` |
| 11 | calculation.py | Gate: `hourly_calculation_enabled`-Prüfung entfernen | `test_with_the_hourly_calculation_nothing_is_cut` |
| 12 | calculation.py | Gate: Filter auf `delta` entfernen | `test_a_rain_gauge_is_never_cut_and_a_rain_rate_is` |
| 13 | calculation.py | `if hourly is None and share != 0:` → `if hourly is None:` | `test_pyeto_without_a_measured_required_field…` |
| 14 | calculation.py | Passthrough-Zweig `if share == 0:` → `if False:` | `test_passthrough_with_its_et_blocked_throughout…` |
| 15 | calculation.py | `et_delta *= share` entfernen | `test_pyeto_books_the_share…` |
| 16 | calculation.py | Aufzeichnung Temperatur: Prüfung entfernen | `test_no_amplitude_is_recorded…` |
| 17 | calculation.py | Aufzeichnung Sonne: `MAPPING_SOLRAD in blocked` → `blocked` | `test_no_radiation_pair_is_recorded…` |
| 18 | calculation.py | Satz 2: `share < 1` → `share <= 1` | `test_a_field_the_module_does_without_gets_no_share_sentence` |
| 19 | store.py | `_as_on_silent_sensor`: Rückfall `KEEP` → `PAUSE` | `test_a_stored_group_without_a_valid_setting_keeps` |
| 20 | sensor_liveness.py | `_stale_issue_key` gibt immer den PR-1-Schlüssel | `test_a_pausing_group_says_its_values_are_no_longer_used` |
| 21 | __init__.py | Re-Sync nach Umschalten der Stundenrechnung entfernen | `test_switching_the_hourly_calculation_rewrites_open_notices` |
| 22 | websockets.py | `vol.In(…)` → `cv.string` | `test_the_mapping_view_takes_the_setting_and_only_its_two_values` |

  Ergebnis nach `../mutate-pr2.txt`. Überlebt eine: zuerst prüfen, ob die Tests überhaupt gesammelt wurden (Memory
  `mutation-survivor-suspects-the-test`), dann den Test schärfen (eigener Commit).

- [x] **Step 5: Review** — `superpowers:requesting-code-review` (Opus) gegen Spec PR 2 und diesen Plan, Diff
  `upstream/master..HEAD`. Befunde über `superpowers:receiving-code-review` prüfen, nicht reflexhaft umsetzen.
  **Bau 2026-10-12:** Urteil „With fixes“ — 0 Critical, 2 Important (Hinweis/Log melden einen Schnitt, den die Rechnung
  nicht macht: Regenzähler und Nicht-Pflichtfelder; Standard *pausieren* schneidet bei einem gerätelosen Template-Sensor
  wie `wind_at_2m` aus der Doku in windstillen Nächten echtes ET), beide vom Controller nachgeprüft; Entscheidung beim
  User. Bericht und Bauprotokoll: `docs/superpowers/probes/2026-10-12-dead-weather-sensor-pr2-build/`.

- [x] **Step 6: Eigene Bezüge** (Memory `no-own-issue-refs-upstream`)

```bash
git diff upstream/master..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|PR [123]\b|PR [A-T]\b"
git log upstream/master..HEAD --format='%H%n%B' | grep -nE "Eifel-Joe#|JustChr#"
```

Expected: beide leer.

---

### Task 11: Pre-Release und Live-Test auf HA-Test

**Files:** keine Codeänderung. Belege nach `D:\Entwicklung\HASI\issue8-pr2-work\livetest\`.

Prüft das Ende-zu-Ende-Kriterium der Spec PR 2. **Alles hier betrifft nur HA-Test; HA-Prod bleibt unberührt.** Auf
HA-Test bleiben das Abfrage-Intervall von 60 min und der neue Pirate-Schlüssel stehen; die Zonen 0 und 1 kommen nie auf
`service`. Vor jedem schreibenden Aufruf die Instanz nennen; Neustarts von HA-Test ankündigen.

- [ ] **Step 1: Basis prüfen** — `git fetch upstream && git rev-list --count HEAD..upstream/master` → `0`. Sonst:
  Upstream-Runde, den ungepushten Branch rebasen, Task 10 Steps 1–4 wiederholen.

- [ ] **Step 2: production-Pre-Release** (Freigabe im Chat vorher; Rezept: Projekt-`CLAUDE.md` *Produktiv-Rebuild/-Release*
  und Memory `hasi-production-on-upstream`). Delta = `upstream/master` + die Commits dieses Branches + Branding +
  Build-Commit. Version `vJJJJ.MM.TTb1` in `manifest.json` und `const.py` (mit `v`), `frontend/package.json` ohne;
  dist mit Node 24, `git add -f`, Dateizahl prüfen. Vor dem Push: `git rev-list --count HEAD..upstream/master` = 0,
  `grep -c "https://github.com" custom_components/irrigation_plus/translations/en.json` = 0, Suite mit Namensvergleich.
  Release `--prerelease`, englische Kurznotiz ohne IP und ohne Issue-Verweise; ZIP aus dem **SHA**; vor dem Upload
  `unzip -p irrigation_plus.zip sensor_liveness.py | grep -c "def blocked_spans"` = 1.
  Installation auf **HA-Test** per HACS, Neustart ankündigen und ausführen; danach Integration `loaded`, Version =
  Pre-Release, Log ohne Fehler von `irrigation_plus`.

- [ ] **Step 3: Testaufbau** (HA-Test; Mittel wie PR 1, siehe Archiv
  `docs/superpowers/probes/2026-10-04-dead-weather-sensor-pr1/livetest/L-pr1.md`): MQTT-Sensoren per YAML unter
  `hasi_livetest/`, ohne Discovery, ein Gerät „HASI Livetest A“ mit Temperatur, Taupunkt, Wind und Druck. Zwei neue
  Sensorgruppen auf diese Sensoren: „Livetest Pause“ (`pause`) und „Livetest Keep“ (`keep`); je eine Wegwerf-Zone mit
  PyETO (Tagesform), nicht Zone 0 oder 1. Stundenrechnung auf HA-Test lesen und, falls an, für den Test ausschalten
  (Stand notieren). Werte für A einmal veröffentlichen, beide Zonen einmal berechnen (setzt ihr Wasserzeichen),
  Startzeit notieren.

- [ ] **Step 4: Schweigen und Rechnen** — 3,5 h nichts an `hasi_livetest/a/#` veröffentlichen (Warten per
  Hintergrund-Schleife, kein Vordergrund-`sleep`). Danach: Diagnostics `data.store.mappings[].sensor_outages` beider
  Gruppen lesen (Beginn = letzte Meldung); **Soll vorab rechnen:** Anteil = (Fenster − (Ende − Beginn − 3 h)) / Fenster
  auf ganze Prozent, mit Fenster = Wasserzeichen bis Rechenzeitpunkt. Dann A wieder veröffentlichen (gleiche Werte),
  ≥ 5 min warten (Prüfung schließt den Ausfall), beide Zonen berechnen.

- [ ] **Step 5: Kriterium** — belegt mit Tool-Output:
  1. Erklärung der Pause-Zone: Satz 1 nennt Taupunkt, Druck, Temperatur, Windgeschwindigkeit von Beginn + 3 h bis Ende;
     Satz 2 nennt genau den vorab gerechneten Anteil.
  2. Erklärung der Keep-Zone: kein Satz; ihre Rechnung wie ohne Ausfall.
  3. Während des offenen Ausfalls: Hinweis der Pause-Gruppe im Paused-Text, der Keep-Gruppe im PR-1-Text; nach
     Umschalten der Stundenrechnung zeigt auch die Pause-Gruppe den PR-1-Text; nach Zurückschalten wieder den
     Paused-Text.
  4. Mit eingeschalteter Stundenrechnung (kurzer Gegenlauf, eine Rechnung der Pause-Zone): kein Satz.

- [ ] **Step 6: Aufräumen** — Testgruppen, -zonen und den MQTT-Block entfernen, `mqtt.reload`; Stundenrechnung auf den
  notierten Stand; prüfen, dass Intervall und Pirate-Schlüssel unverändert sind. Protokoll `livetest\L-pr2.md`.

---

### Task 12: PR an JustChr und Nachlauf

**Files:** keine Codeänderung. Texte unter `D:\Entwicklung\HASI\issue8-pr2-work\texts\`.

- [ ] **Step 1: Upstream-Runde**, dann `git rev-list --count HEAD..upstream/master` = 0.
- [ ] **Step 2: PR-Text** nach Skill `pr-workflow`: erst deutsch zur Freigabe, dann englisch. Inhalt: was PR 2 tut (die
  Einstellung, der Schnitt im Tagespfad, der Anteil, `s = 0`, Hinweis-Variante, Erklärung), was er bewusst nicht tut
  (Stundenpfad und Live-Schätzung folgen), Bestand byte-identisch, Feldtest von PR 1 auf echter Hardware ohne
  Fehlalarm, Live-Test auf HA-Test, Zahlen (Tests, Mutationen) **auf dem Endstand nachgemessen**. Jede `datei:zeile`
  im Text gegen den Branch-SHA öffnen. Keine eigenen Issue-Verweise, keine Branch-SHAs.
- [ ] **Step 3: Push und PR** (nach Freigabe):

```bash
git push -u origin feat/pause-silent-weather-sensor
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:feat/pause-silent-weather-sensor \
  --title "feat(liveness): a sensor group can pause a silent sensor in the daily calculation" --body-file <datei>
```

  Danach den Body per `gh api repos/JustChr/HAsmartirrigation/pulls/<N> --jq .body > datei` zurücklesen und mit `cmp`
  vergleichen.
- [ ] **Step 4: P2** — Kommentar auf Eifel-Joe#8 (Text vorher freigeben), `#42` Punkt 9 nachziehen, Label bleibt
  `upstream:freigegeben`. production bekommt PR 2 mit dem Pre-Release aus Task 11; HA-Prod nur auf Zuruf.
- [ ] **Step 5: P1** — Plan-Häkchen, Abweichungsprotokoll und Live-Test-Protokoll nach `archive/design-history`
  (Worktree `pr139-work\archive-wt`).

---

## Selbstprüfung gegen die Spec PR 2

| Spec PR 2 | Task |
|---|---|
| F1 Passthrough verbraucht ohne ERROR, nur bei Sperre | 5 (Steps 6.4; Tests `…throughout…`, `…another_reason…`) |
| F2 Wert von vor der Sperre gilt danach wieder | 3 (`_held`; Tests `…holds_again…`, `…boundary_after_the_span`) |
| F3 bekannte Grenze, kein Mindestanteil | 9 (Doku) |
| F4 ganzes Mittel × Anteil | 5 (Step 6.5; Test `…forecast_days…`) |
| Ansatz 1: `blocked=` neben dem Aggregat | 3, 4, 5 |
| §1 `blocked_spans`, halboffen, Vereinigung, Zuschnitt, Felder aus der Liste | 1 |
| §1 Gate: pause, keine Stundenrechnung, Wasserzeichen, leer → None, Regenzähler | 4 |
| §1 keine eigene Prüfung im Commit | 4 (Gate liest nur die Liste) |
| §2 Aggregation je Aggregat, Randzeile, Haltewert, `last_entry`, riemannsum, delta | 3 |
| §3 Anteil, Pflichtfelder, `s = 0`, Drainage unverändert | 5 |
| §4 Konstanten, Feld, Laden → keep, neue Gruppen → pause, Migration | 1, 2 |
| §4 View-Schema, Panel, Typ, 8 Sprachen, dist | 8 |
| §5 Hinweis-Variante, Re-Sync bei Einstellung und Stundenrechnung, Log-Text | 7 |
| §5 Erklärungssätze, Stelle, Format, 8 Sprachen | 6 |
| §6 Aufzeichnungen überspringen | 4 |
| §6 Kommentare der Live-Schätzung, Doku | 9 |
| Tests, Byte-Identität, Mutationen, Baseline | 1–8, 5 (Byte-Identität), 10 |
| Ende-zu-Ende auf HA-Test | 11 |
| Lieferung, P1, P2 | 11, 12 |
