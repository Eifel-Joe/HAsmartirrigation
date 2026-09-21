# Wetterpuffer-Zeitzonen-Naht: Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gespeicherte Wetterpuffer-Stempel werden in der Zone gelesen, in der sie geschrieben wurden, und künftig aware geschrieben — Schreiber, Leser und Migration in einem Zug.

**Architecture:** Ein gemeinsamer Coerce-Helfer (`helpers.as_stored_aware`) deutet naive Stempel als Prozess-lokal und reicht aware durch. Alle Leser rufen ihn; alle persistierenden Schreiber stellen auf `dt_util.now()` um; eine Store-Migration (14 → 15) zieht den Bestand nach. Die Prozess-Zone kommt aus einer eigenen Funktion, damit der Test sie ohne `time.tzset()` ersetzen kann.

**Tech Stack:** Python 3.12, Home Assistant `homeassistant.util.dt`, `attrs`, pytest + pytest-homeassistant-custom-component.

**Spec:** `docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md`
**Basis:** `upstream/master` = `965a4f9d`, Branch `fix/weather-buffer-aware-time`

**Testbefehl (verbatim, globale Regel 0):**
```bash
./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

**Bekannt rot unter Windows, auch auf unverändertem `upstream/master`** (kein Regress):
`tests/test_panel.py::test_async_register_panel_static_path_config` (Pfadtrenner).

---

## Reihenfolge — warum sie nicht beliebig ist

Die Stempel des Wetterpuffers werden gegeneinander verglichen. Ein halb umgestellter
Vergleichsraum wirft `TypeError` (naiv gegen aware). Deshalb:

1. Helfer zuerst (isoliert, bricht nichts).
2. Der Pin (RED).
3. Der Vergleichsraum Wetterpuffer **atomar** — Leser, Schreiber und `now`-Defaults in EINEM
   Commit. Das ist JustChrs „move both ends together"; hier ist es keine Stilfrage, sondern die
   Bedingung dafür, dass die Suite zwischen zwei Tasks nicht rot ist.
4. Die Satelliten (`sensor.py`, `auto_calc.py`, Solargeometrie) einzeln — sie lesen, vergleichen
   aber nicht gegen den Puffer.
5. Migration zuletzt: sie beschreibt den Bestand, den Schritt 3 bereits korrekt liest.

---

### Task 1: Der gemeinsame Coerce-Helfer

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py` (nach `as_datetime`, derzeit :987-998)
- Test: `tests/test_stored_stamp_timezone.py` (neu)

- [ ] **Step 1: Write the failing test**

Neue Datei `tests/test_stored_stamp_timezone.py`:

```python
"""A stored naive stamp means the zone the PROCESS was in when it was written.

``datetime.now()`` with no argument returns a naive stamp in the process's
zone; ``dt_util.now()`` returns an aware one in HA's configured zone. The two
are equal only on HA OS and Supervised, which is why this went unnoticed -- see
docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md.
"""

import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import helpers, sensor, weather_aggregate

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


def test_naive_stamp_is_read_in_the_process_zone(monkeypatch):
    """A container running UTC wrote 12:00; that is 12:00 UTC, not 12:00 Berlin."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware("2026-09-21T12:00:00")

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_naive_stamp_follows_the_process_zone_not_has(monkeypatch):
    """Same bytes, different process zone -- a different instant."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: BERLIN)

    got = helpers.as_stored_aware("2026-09-21T12:00:00")

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=BERLIN)
    assert got.astimezone(UTC).hour == 10


def test_aware_stamp_passes_through_untouched(monkeypatch):
    """An offset on disk is self-describing; nothing may reinterpret it."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware("2026-09-21T12:00:00+02:00")

    assert got.utcoffset() == datetime.timedelta(hours=2)
    assert got.astimezone(UTC).hour == 10


def test_datetime_instances_are_accepted_like_strings(monkeypatch):
    """The store hands back live objects before a restart, strings after one."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    got = helpers.as_stored_aware(datetime.datetime(2026, 9, 21, 12, 0))

    assert got == datetime.datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_none_passes_through_silently():
    """An unset watermark is normal, not an error (see helpers.as_datetime)."""
    assert helpers.as_stored_aware(None) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py -p _local_socket_unblock -v
```
Erwartet: 5 FAILED/ERROR mit `AttributeError: module 'custom_components.irrigation_plus.helpers' has no attribute '_process_timezone'`.

- [ ] **Step 3: Write minimal implementation**

In `custom_components/irrigation_plus/helpers.py`, direkt nach `as_datetime` (:998) einfügen:

```python
def _process_timezone():
    """The zone a bare ``datetime.now()`` writes in — the PROCESS's, not HA's.

    Its own function for one reason: the suite has to be able to substitute it.
    ``time.tzset()`` does not exist on Windows, so a test cannot set the real
    process zone, and a test that only runs on CI is one we never watch go from
    red to green ourselves.
    """
    return datetime.now().astimezone().tzinfo


def as_stored_aware(value) -> datetime | None:
    """Coerce a stored timestamp to an AWARE datetime.

    A naive stored stamp was written by a bare ``datetime.now()`` and is
    therefore in the PROCESS's zone. That is NOT HA's configured zone: on
    Docker/Core without ``TZ=`` the container runs UTC while the user
    configured, say, Europe/Berlin, and the two differ by the whole offset.

    Reading such a stamp as HA-local is the defect this replaces. It was in
    ``sensor._to_aware_datetime`` (``replace(tzinfo=DEFAULT_TIME_ZONE)``), in
    ``live_estimate._parse_local_naive`` and — most expensively — in
    ``calculation``'s solar-time correction, whose own comment says the stamps
    are "naive LOCAL times" while handing them HA's offset. Rso is a
    denominator there, so the error reaches +23.5% / -16% on the radiation the
    clearness-ratio hold refills.

    An aware value is returned untouched: an offset on disk is self-describing
    and nothing here may second-guess it. That is also what makes the store
    migration idempotent.
    """
    parsed = as_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_process_timezone())
    return parsed
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py -p _local_socket_unblock -v
```
Erwartet: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/helpers.py tests/test_stored_stamp_timezone.py
git commit -F - <<'EOF'
feat(time): read a stored naive stamp in the zone it was written in

A bare datetime.now() writes the PROCESS's zone; dt_util.now() reads HA's
configured one. They agree on HA OS and Supervised, which is why the seam
went unnoticed, and differ by the whole offset on Docker/Core without TZ=.

as_stored_aware attaches the process zone to a naive stamp and passes an
aware one through untouched. The zone lookup is its own function so the
suite can substitute it: time.tzset() does not exist on Windows.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Der Pin — das Fenster ist so lang, wie es wirklich war

Das ist der Test, den JustChr ausdrücklich verlangt: „a stored stamp written under one process
zone, read back under a different HA zone, asserting the elapsed window is the real one."

**Files:**
- Test: `tests/test_stored_stamp_timezone.py` (erweitern)

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_stored_stamp_timezone.py` anfügen (die Imports stehen bereits im Kopf
aus Task 1):

```python
def test_elapsed_window_is_the_real_one_across_a_process_ha_zone_split(monkeypatch):
    """The seam, end to end: written under UTC, read with HA on Europe/Berlin.

    _hour_multiplier prices a day's ET by the elapsed window, so a watermark
    read in the wrong zone scales the whole result. At a +2 h offset a one-hour
    window reads as three -- 3/24 instead of 1/24, i.e. 3x the ET.

    RED on today's code: weather_aggregate._parse returns the stamp naive, and
    subtracting it from an aware ``now`` raises TypeError.
    """
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)

    # Written by a container running UTC at the real instant 12:00Z.
    stored_on_disk = "2026-09-21T12:00:00"
    # One real hour later.
    now = datetime.datetime(2026, 9, 21, 13, 0, tzinfo=UTC)

    watermark = weather_aggregate._parse(stored_on_disk)

    assert weather_aggregate._hour_multiplier([], watermark, now) == pytest.approx(
        1 / 24
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py::test_elapsed_window_is_the_real_one_across_a_process_ha_zone_split -p _local_socket_unblock -v
```
Erwartet: FAILED mit `TypeError: can't subtract offset-naive and offset-aware datetimes`
(aus `weather_aggregate._hour_multiplier`, Zeile `diff = now - watermark`).

Das ist der Beleg, dass der Test den geänderten Pfad wirklich durchläuft (Memory
`verification-must-exercise-the-change`): Er fällt in `_parse`/`_hour_multiplier`, nicht an einem
fehlenden Namen.

- [ ] **Step 3: Commit den roten Test noch nicht**

Der Pin wird zusammen mit Task 3 grün und dort mit committet — ein roter Test allein im Verlauf
wäre ein Commit, der die Suite bricht.

---

### Task 3: Der Vergleichsraum Wetterpuffer, atomar

Leser, Schreiber und `now`-Defaults dieses Raums in EINEM Commit. Alles andere lässt die Suite
zwischen zwei Tasks rot.

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py:102-108` (`_parse`), `:337`, `:891`, `:1072`
- Modify: `custom_components/irrigation_plus/calculation.py:27` (Import), `:265`, `:377`, `:430`, `:492`, `:884`
- Modify: `custom_components/irrigation_plus/continuous_update.py:252`, `:378`, `:521`
- Modify: `custom_components/irrigation_plus/live_estimate.py:134-156`, `:204`, `:980`, `:1400`
- Modify: `custom_components/irrigation_plus/__init__.py:1429`, `:1506`, `:1516`, `:1632`, `:1644`, `:1799`, `:2023`
- Modify: `custom_components/irrigation_plus/store.py:1633`
- Test: `tests/test_stored_stamp_timezone.py` (aus Task 2)

- [ ] **Step 1: `weather_aggregate._parse` delegiert**

`custom_components/irrigation_plus/weather_aggregate.py:102-108` ersetzen durch:

```python
def _parse(value):
    """Parse a stored RETRIEVED_AT (datetime or ISO string) to an aware datetime.

    Aware, because a naive stamp on disk is in the PROCESS's zone and every
    comparison here is against HA-local time. See helpers.as_stored_aware.
    """
    return as_stored_aware(value)
```

Import oben in derselben Datei ergänzen (neben dem bestehenden `parse_datetime`-Import):

```python
from .helpers import as_stored_aware
```

Wird `parse_datetime` in `weather_aggregate.py` danach nirgends mehr benutzt, den Import entfernen
— `ruff` meldet es sonst als F401.

- [ ] **Step 2: Die drei `now`-Defaults in `weather_aggregate.py`**

Jeweils `if now is None: now = datetime.datetime.now()` → `dt_util.now()` an `:337`, `:891`, `:1072`.
Der `dt_util`-Import ist in der Datei bereits vorhanden (er wird für `DEFAULT_TIME_ZONE` benutzt);
falls nicht, `from homeassistant.util import dt as dt_util` ergänzen.

Außerdem den Docstring bei `:324` nachziehen: `defaults to ``datetime.now()``` →
`defaults to ``dt_util.now()```.

- [ ] **Step 3: `calculation.py` — Import und fünf Schreiber**

`:27` von `from .helpers import as_datetime as _as_datetime` auf

```python
from .helpers import as_stored_aware as _as_datetime
```

umstellen. Der lokale Alias bleibt, damit die sieben Aufrufstellen (`:59`, `:329`, `:396`, `:779`,
`:836`, `:925`, `:1066`) unverändert bleiben und der Diff klein bleibt.

Dann `now = datetime.now()` → `now = dt_util.now()` an `:265`, `:377`, `:430`, `:492`, `:884`.

Den Modul-Docstring-Teil bei `:45-53` (`pending_bucket_events`) anpassen — siehe Task 3, Step 6.

- [ ] **Step 4: `continuous_update.py` — drei Schreiber**

`timestamp = datetime.now()` → `dt_util.now()` an `:252` und `:378`; `now = datetime.now()` →
`dt_util.now()` an `:521`. Den Kommentar bei `:375` („Naive local, exactly like the interval path's
RETRIEVED_AT") auf aware umschreiben:

```python
        # Aware HA-local, exactly like the interval path's RETRIEVED_AT -- the
        # two rows land in the same buffer and are compared against each other.
```

- [ ] **Step 5: `__init__.py` — der Schwester-Pfad**

Sieben Stellen hinter dem `dt_datetime`-Alias: `:1429`, `:1506`, `:1516`, `:1632`, `:1644`, `:1799`,
`:2023`. Jeweils `dt_datetime.now()` → `dt_util.now()`.

`:1506` ist das On-Demand-Einzelzonen-Update, `:1632` der Intervall-Poll `_async_update_all` — der
erzeugt die meisten Pufferzeilen überhaupt. Beide gehören zusammen; das Issue nennt nur die
`calculation`/`continuous_update`-Hälfte.

Wird `dt_datetime` danach nirgends mehr benutzt, den Alias-Import (`:11`) **und** den erklärenden
NB-Kommentar (`:6-10`) entfernen — der Kommentar erklärt eine Kollision, die es dann nicht mehr
gibt. `grep -n "dt_datetime" custom_components/irrigation_plus/__init__.py` muss danach leer sein.

- [ ] **Step 6: `live_estimate.py` — das Plattmachen entfällt**

`:134-156` `_parse_local_naive` ersetzen durch:

```python
def _parse_stored(value):
    """Parse a stored last_calculated/last_updated to an AWARE datetime.

    Was ``_parse_local_naive``: it flattened everything to naive local so the
    value could be compared against a window built from bare ``datetime.now()``
    stamps. Both ends are aware now, so the flattening is not just unnecessary
    -- it was the bug. A naive stamp is in the PROCESS's zone, and reading it
    as HA-local shifted the intra-day window by the whole UTC offset.
    """
    try:
        return as_stored_aware(value)
    except ValueError:
        return None
```

Import ergänzen: `from .helpers import as_stored_aware`.

Alle Aufrufer von `_parse_local_naive` auf `_parse_stored` umbenennen
(`grep -n "_parse_local_naive" custom_components/irrigation_plus/live_estimate.py`).

Dann die drei Entkleidungen entfernen:
- `:204` `"now": now.replace(tzinfo=None),` → `"now": now,`
- `:980` `now_local = inputs.get("now") or dt_util.now().replace(tzinfo=None)` →
  `now_local = inputs.get("now") or dt_util.now()`
- `:1400` dieselbe Zeile, dieselbe Änderung

Sowie die drei `dt_util.as_local(...).replace(tzinfo=None)` an `:266`, `:301`, `:1358` → `dt_util.as_local(...)`.

- [ ] **Step 7: `calculation.pending_bucket_events` macht nicht mehr platt**

`custom_components/irrigation_plus/calculation.py:45-70`: Den Docstring-Absatz und die drei Zeilen

```python
        if stamp.tzinfo is not None:
            stamp = dt_util.as_local(stamp).replace(tzinfo=None)
```

entfernen. `_as_datetime` liefert jetzt immer aware; das Flachklopfen existierte ausschließlich,
weil das Fenster naiv gebaut war. Docstring-Kopf anpassen:

```python
def pending_bucket_events(zone):
    """A zone's unconsumed mid-window bucket credits as ``[(aware, mm)]``.

    Stored aware (see ``IrrigationRunnerMixin.async_write_watered_bucket``) and
    returned aware: the window these are placed on is aware too. Entries that
    will not parse are dropped rather than defaulted to a time: a credit placed
    at the wrong instant is worse than one placed at the window start, which is
    what dropping it falls back to.
    """
```

- [ ] **Step 8: `store.py:1633`**

`new_zone = attr.evolve(new_zone, last_consumed_at=datetime.datetime.now())` →
`last_consumed_at=dt_util.now())`. `dt_util`-Import in `store.py` prüfen und ggf. ergänzen.

- [ ] **Step 9: Pin und Suite prüfen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py -p _local_socket_unblock -v
```
Erwartet: 6 passed (die 5 aus Task 1 plus der Pin).

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q
```
Erwartet: nur `test_panel.py::test_async_register_panel_static_path_config` rot (bekannt, Windows).
Jeder andere Fehlschlag ist ein Regress und wird hier behoben, nicht später.

- [ ] **Step 10: Commit**

```bash
git add custom_components/irrigation_plus/ tests/test_stored_stamp_timezone.py
git commit -F - <<'EOF'
fix(time): move the weather buffer's stamps and readers to aware HA time

The buffer's timestamps were written by a bare datetime.now() -- naive, in
the PROCESS's zone -- while parts of the code read them as HA-local. Both
being naive is why nothing ever raised. On Docker/Core without TZ= the two
zones differ by the whole UTC offset, so a one-hour window priced as three.

Writers and readers move together, because a half-converted comparison
space raises instead of drifting: every persisted datetime.now() becomes
dt_util.now(), every stored stamp is read through as_stored_aware, and the
deliberate flattening in live_estimate and pending_bucket_events goes away
-- it only existed to meet the naive window.

__init__.py is the sister path the report did not cover: seven more naive
writers behind the dt_datetime alias, including the interval poll that
produces most buffer rows.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: `sensor.py` liest nicht mehr HA-lokal

**Files:**
- Modify: `custom_components/irrigation_plus/sensor.py:605-621`
- Test: `tests/test_stored_stamp_timezone.py` (erweitern)

- [ ] **Step 1: Write the failing test**

```python
def test_sensor_reads_a_stored_stamp_in_the_process_zone(monkeypatch):
    """sensor._to_aware_datetime assumed naive == HA-local. It is not."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(BERLIN)
    try:
        got = sensor._to_aware_datetime("2026-09-21T12:00:00")
    finally:
        dt_util.set_default_time_zone(original)

    # 12:00 in a UTC process is 12:00Z -- NOT 10:00Z, which is what reading it
    # as Berlin would produce.
    assert got.astimezone(UTC).hour == 12
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py::test_sensor_reads_a_stored_stamp_in_the_process_zone -p _local_socket_unblock -v
```
Erwartet: FAILED, `assert 10 == 12`.

- [ ] **Step 3: Write minimal implementation**

`custom_components/irrigation_plus/sensor.py:605-621` ersetzen durch:

```python
def _to_aware_datetime(value):
    """Parse a stored timestamp (datetime or ISO string) to an aware datetime.

    A naive stored value is in the PROCESS's zone, not HA's -- see
    helpers.as_stored_aware. This used to attach DEFAULT_TIME_ZONE, which is
    correct only where the two agree (HA OS, Supervised).
    """
    try:
        return as_stored_aware(value)
    except ValueError:
        return None
```

Import ergänzen: `from .helpers import as_stored_aware`.

- [ ] **Step 4: Run test to verify it passes**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py -p _local_socket_unblock -v
```
Erwartet: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/sensor.py tests/test_stored_stamp_timezone.py
git commit -F - <<'EOF'
fix(sensor): a stored naive stamp is process-local, not HA-local

_to_aware_datetime attached DEFAULT_TIME_ZONE, which is right only where
the process zone and HA's configured zone agree.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: `auto_calc.py` — der Stale-Ledger-Cutoff

**Files:**
- Modify: `custom_components/irrigation_plus/auto_calc.py:84-96`

- [ ] **Step 1: Änderung**

Die Kommentarzeilen `:85-87` und den Cutoff `:88-90` ersetzen durch:

```python
        # Aware, like everything the store now holds. This used to strip the
        # tzinfo to match calculation.py's bare datetime.now() stamps; both
        # ends are aware since the weather buffer moved.
        cutoff = dt_util.now() - timedelta(
            hours=const.AUTO_CALC_MAX_LEDGER_AGE_HOURS
        )
```

Prüfen, womit `cutoff` verglichen wird, und dass die Gegenseite über `as_stored_aware` kommt:

```bash
grep -n "cutoff" custom_components/irrigation_plus/auto_calc.py
```

- [ ] **Step 2: Run the auto-calc tests**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -k "auto_calc or ledger" -p _local_socket_unblock -v
```
Erwartet: passed.

- [ ] **Step 3: Commit**

```bash
git add custom_components/irrigation_plus/auto_calc.py
git commit -F - <<'EOF'
fix(auto-calc): compare the ledger cutoff in the zone the store now uses

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Die Solargeometrie nimmt den Offset der Zeile, nicht HAs

Die teuerste Einzelstelle. `weather_aggregate.py:970` macht heute

```python
row_offset = tz.utcoffset(hour_start)
```

mit `tz = dt_util.DEFAULT_TIME_ZONE` (aus `calculation.py:773`) und naivem `hour_start`. Das fragt
„welchen Offset hat **HA** zu dieser Wanduhrzeit" — und deutet damit den prozess-lokalen Stempel
als HA-lokal. Genau die Verwechslung, nur an der Stelle, an der sie am meisten kostet: Rso steht
im Nenner des Clearness-Ratio-Holds, also +23,5 % / −16 % auf die Strahlung.

**Aware-Machen allein behebt das nicht.** `et_estimate.py:140` und `weather_aggregate.py:725`
lesen den Offset aus einem `row["tz_offset_h"]`-**Schlüssel**, nicht aus der tzinfo des Stempels.
Gefüllt wird der Schlüssel nur an `:970-972`. Diese eine Zeile muss mit.

Nach Task 3 ist `hour_start` aware (`:946` `start.replace(minute=0, …)`, `start` aus
`_window_bounds`), trägt also den Offset, unter dem die Zeile geschrieben wurde. Bei `ZoneInfo`
löst `.utcoffset()` aus den Wanduhr-Feldern auf, DST-Übergänge im Fenster bleiben damit korrekt
aufgelöst — das ist genau die Eigenschaft, die der Docstring bei `:871-879` verlangt.

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py:966-972`, `:867-879` (Docstring)
- Modify: `custom_components/irrigation_plus/calculation.py:765-775` (Kommentar)
- Test: `tests/test_stored_stamp_timezone.py` (erweitern)

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_stored_stamp_timezone.py`:

```python
def test_row_offset_comes_from_the_stamp_not_from_has_zone():
    """The clearness-ratio denominator must use the offset the row was written
    under, not HA's offset at the same wall-clock reading.

    A row stamped 12:00Z (a UTC container) must carry tz_offset_h 0.0 even when
    HA is configured Europe/Berlin, where 12:00 wall clock is +2.
    """
    berlin = BERLIN
    stamp_utc = datetime.datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

    # What the code does today, for contrast: ask HA's zone about this reading.
    assert berlin.utcoffset(stamp_utc.replace(tzinfo=None)) == datetime.timedelta(
        hours=2
    )
    # What it must do: take the offset the stamp carries.
    assert stamp_utc.utcoffset() == datetime.timedelta(0)
```

Dieser Test pinnt die Regel selbst. Den Durchstich durch `build_hourly_rows` deckt
`tests/test_hourly_rows_dst.py` bereits ab; er muss nach der Änderung weiter grün sein.

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_timezone.py::test_row_offset_comes_from_the_stamp_not_from_has_zone -p _local_socket_unblock -v
```
Erwartet: PASS — der Test pinnt reine `datetime`-Semantik und ist absichtlich unabhängig vom
Produktivcode. Er dokumentiert die Regel, an der Step 3 sich messen lässt. Der RED für diese Task
ist `tests/test_hourly_rows_dst.py`, sobald Step 3 falsch umgesetzt wird.

- [ ] **Step 3: Write the implementation**

`custom_components/irrigation_plus/weather_aggregate.py:966-972` ersetzen durch:

```python
        # Resolved from THIS row's own stamp, not once for the window and not
        # by asking the site zone about a wall-clock reading: the stamp is
        # aware and carries the offset it was actually written under. Asking
        # ``tz`` instead was the defect -- it answered "what is HA's offset at
        # this wall clock", which reinterprets a process-local stamp as
        # HA-local and is wrong by the whole difference on Docker/Core without
        # TZ=. ZoneInfo resolves utcoffset() from the wall-clock fields, so a
        # window straddling a DST transition still gets both offsets right.
        row_offset = hour_start.utcoffset()
        if row_offset is None and tz is not None:
            row_offset = tz.utcoffset(hour_start)
        if row_offset is not None:
            row["tz_offset_h"] = row_offset.total_seconds() / 3600.0
```

Das umschließende `if tz is not None:` bei `:969` entfällt — `tz` ist jetzt nur noch Fallback.
Einrückung entsprechend anpassen.

Docstring bei `:867-879` nachziehen: `` `tz_offset_h` `` ist nicht mehr „the local UTC offset the
naive buffer stamps are in", sondern der Fallback für Zeilen ohne eigenen Offset; der Satz „each
row resolves its own UTC offset from its own naive stamp" wird zu „from its own aware stamp". Der
Absatz zu `fold=0` bei mehrdeutigen Rückfall-Stunden entfällt — ein aware Stempel ist nicht
mehrdeutig.

- [ ] **Step 4: Kommentar in `calculation.py:765-775`**

```python
        # The scalar fallback only. Each buffer row is aware and carries the
        # offset it was written under; build_hourly_rows reads it from the row
        # and both the ETo series and the Eq. 36 ratio denominator prefer it.
        # This scalar covers a row that carries none.
        tz = dt_util.DEFAULT_TIME_ZONE
        offset = dt_util.now().utcoffset()
        tz_offset_h = offset.total_seconds() / 3600.0 if offset else 0.0
```

- [ ] **Step 5: Run the solar/hourly tests**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_hourly_rows_dst.py tests/test_solar_ratio_hold.py tests/test_solar_azimuth_bearing.py tests/test_stored_stamp_timezone.py -p _local_socket_unblock -v
```
Erwartet: passed. `test_hourly_rows_dst.py` ist hier der eigentliche Wächter: Es prüft, dass Zeilen
beiderseits eines DST-Übergangs verschiedene Offsets bekommen. Fällt es, ist `hour_start` entgegen
der Annahme nicht aware — dann zuerst dort nachsehen, nicht den Test anpassen.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/calculation.py tests/test_stored_stamp_timezone.py
git commit -F - <<'EOF'
fix(solar): take a row's UTC offset from its stamp, not from HA's zone

build_hourly_rows asked the site zone what ITS offset was at the row's
wall-clock reading, which reinterprets a process-local stamp as HA-local.
The stamps are aware now and carry the offset they were written under.

This is the expensive end of the seam: Rso is the denominator of the
clearness ratio, so the error reaches +23.5% / -16% on the radiation the
hold refills, against 0.26-0.74% on daily ETo.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Die Migration, `STORAGE_VERSION` 14 → 15

**Files:**
- Modify: `custom_components/irrigation_plus/store.py:195` (`STORAGE_VERSION`), `:757` (nach dem `old_version <= 13`-Block)
- Test: `tests/test_weather_buffer_time_migration.py` (neu)

- [ ] **Step 1: Write the failing test**

Neue Datei `tests/test_weather_buffer_time_migration.py`:

```python
"""v15: stored naive stamps become aware, watermark and buffer in one pass.

Migrating one without the other is the only way to create double counting:
select_window compares a buffer row against the watermark, so a uniform shift
of both cancels there, and a shift of one does not.
"""

import datetime
import zoneinfo

from custom_components.irrigation_plus import helpers
from custom_components.irrigation_plus.store import MigratableStore

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


def _doc():
    return {
        "config": {},
        "zones": [
            {
                "id": 1,
                "last_calculated": "2026-09-21T12:00:00",
                "last_consumed_at": "2026-09-21T11:00:00",
                "last_updated": "2026-09-21T12:00:00",
                "last_irrigation": "2026-09-21T06:00:00+02:00",
            }
        ],
        "mappings": [
            {
                "id": 1,
                "data_last_updated": "2026-09-21T12:00:00",
                "data": [
                    {"retrieved": "2026-09-21T11:30:00", "temperature": 19.0},
                    {"retrieved": "2026-09-21T12:00:00", "temperature": 20.0},
                ],
            }
        ],
    }


async def test_v15_makes_stored_stamps_aware_in_the_process_zone(hass, monkeypatch):
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    store = MigratableStore(hass, 15, "irrigation_plus.test")

    data = await store._async_migrate_func(14, _doc())

    zone = data["zones"][0]
    assert zone["last_calculated"].endswith("+00:00")
    assert zone["last_consumed_at"].endswith("+00:00")
    assert zone["last_updated"].endswith("+00:00")
    rows = data["mappings"][0]["data"]
    assert rows[0]["retrieved"].endswith("+00:00")
    assert rows[1]["retrieved"].endswith("+00:00")
    assert data["mappings"][0]["data_last_updated"].endswith("+00:00")


async def test_v15_leaves_already_aware_stamps_alone(hass, monkeypatch):
    """last_irrigation was always aware; reinterpreting it would move it."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    store = MigratableStore(hass, 15, "irrigation_plus.test")

    data = await store._async_migrate_func(14, _doc())

    assert data["zones"][0]["last_irrigation"] == "2026-09-21T06:00:00+02:00"


async def test_v15_is_idempotent(hass, monkeypatch):
    """An aware stamp on disk is self-describing, so a second pass is a no-op."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    store = MigratableStore(hass, 15, "irrigation_plus.test")

    once = await store._async_migrate_func(14, _doc())
    twice = await store._async_migrate_func(14, once)

    assert twice == once


async def test_v15_shifts_watermark_and_buffer_by_the_same_amount(hass, monkeypatch):
    """The invariant that rules out double counting.

    select_window keeps a row when ``retrieved > watermark``. A uniform shift
    of the whole stored time axis cancels in that comparison; shifting only one
    side would silently re-admit readings the zone already consumed.
    """
    monkeypatch.setattr(helpers, "_process_timezone", lambda: BERLIN)
    store = MigratableStore(hass, 15, "irrigation_plus.test")

    data = await store._async_migrate_func(14, _doc())

    watermark = datetime.datetime.fromisoformat(data["zones"][0]["last_consumed_at"])
    row = datetime.datetime.fromisoformat(data["mappings"][0]["data"][0]["retrieved"])
    # 11:00 and 11:30 were 30 minutes apart before and must stay 30 apart.
    assert row - watermark == datetime.timedelta(minutes=30)
    assert watermark.utcoffset() == row.utcoffset()


async def test_v15_tolerates_a_document_saved_without_its_buffer(hass, monkeypatch):
    """_data_to_save omits the ``data`` key entirely when the buffer is clean."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    store = MigratableStore(hass, 15, "irrigation_plus.test")
    doc = _doc()
    del doc["mappings"][0]["data"]

    data = await store._async_migrate_func(14, doc)

    assert "data" not in data["mappings"][0]
    assert data["zones"][0]["last_calculated"].endswith("+00:00")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_time_migration.py -p _local_socket_unblock -v
```
Erwartet: 5 FAILED — die Stempel kommen unverändert naiv zurück (`assert False`, weil
`"2026-09-21T12:00:00".endswith("+00:00")` falsch ist).

- [ ] **Step 3: Write minimal implementation**

`custom_components/irrigation_plus/store.py:195`: `STORAGE_VERSION = 14` → `STORAGE_VERSION = 15`.

Nach dem `old_version <= 13`-Block (endet `:757`, vor dem `# CRITICAL:`-Kommentar) einfügen:

```python
        if old_version <= 14:
            # v15: the weather buffer's timestamps become aware.
            #
            # These were written by a bare ``datetime.now()``, so they are in
            # the PROCESS's zone -- which is what we attach here. That is not
            # HA's configured zone: on Docker/Core without ``TZ=`` the
            # container runs UTC while the user configured, say, Europe/Berlin.
            #
            # Attaching HA's zone instead would be the WRONG repair and is the
            # tempting one, because sensor.py and live_estimate read these as
            # HA-local for years. That is how they were READ, not how they were
            # WRITTEN, and this migration's job is to preserve the instant.
            #
            # ASSUMPTION, stated because it can be wrong: a naive stamp is only
            # unambiguously process-local as long as the process zone has not
            # changed since it was written. A user who fixes their container's
            # TZ and THEN updates has stamps from the old zone, which this
            # shifts by the delta between them.
            #
            # We do not try to detect that, and not merely to save the code.
            # The buffer legitimately contains discontinuities of exactly the
            # shape a detector would key on: at the autumn DST transition the
            # naive sequence runs an hour BACKWARDS, and those bytes are
            # identical to a container TZ fix. A detector would therefore fire
            # on every DST user twice a year with the same error magnitude it
            # exists to prevent. A future-stamp clamp is worse still -- the
            # scenario above raises the offset, so its stamps land in the PAST
            # and the clamp never fires at all.
            #
            # The unguarded case is bounded: _hour_multiplier prices one window
            # by delta/24, so a 2 h error is 8.3% of one day's ET, once, and
            # every stamp written afterwards carries its own offset.
            #
            # Watermark and buffer move in the SAME pass. A wrong assumption is
            # then a uniform translation of the whole stored time axis, and
            # select_window's ``retrieved > watermark`` cancels it exactly.
            # Migrating one without the other is the only way to double-count.
            for zone in data.get("zones", []):
                for key in (ZONE_LAST_CALCULATED, ZONE_LAST_CONSUMED, ZONE_LAST_UPDATED):
                    zone[key] = _stamp_to_aware(zone.get(key))
            for mapping in data.get("mappings", []):
                mapping[MAPPING_DATA_LAST_UPDATED] = _stamp_to_aware(
                    mapping.get(MAPPING_DATA_LAST_UPDATED)
                )
                # Absent when a routine save wrote this document -- see
                # _data_to_save, which omits the key entirely.
                for row in mapping.get(MAPPING_DATA) or []:
                    if isinstance(row, dict) and RETRIEVED_AT in row:
                        row[RETRIEVED_AT] = _stamp_to_aware(row.get(RETRIEVED_AT))
```

Auf Modulebene in `store.py` (neben `_migrate_schedule_to_v14`) ergänzen:

```python
def _stamp_to_aware(value):
    """One stored stamp, aware, as an ISO string — or unchanged if unparseable.

    Idempotent by construction: HA's JSONEncoder writes ``datetime.isoformat()``,
    so an aware stamp already carries an offset and ``as_stored_aware`` returns
    it untouched. A value that will not parse is left exactly as found: this
    migration must never be the reason a document stops loading.
    """
    if value is None:
        return None
    try:
        parsed = as_stored_aware(value)
    except (ValueError, TypeError):
        return value
    return parsed.isoformat() if parsed is not None else value
```

Imports in `store.py` ergänzen: `as_stored_aware` aus `.helpers`, sowie `ZONE_LAST_CALCULATED`,
`ZONE_LAST_CONSUMED`, `ZONE_LAST_UPDATED`, `RETRIEVED_AT`, `MAPPING_DATA`,
`MAPPING_DATA_LAST_UPDATED` aus `.const` — vorher prüfen, welche davon schon importiert sind:

```bash
grep -n "ZONE_LAST_CALCULATED\|ZONE_LAST_CONSUMED\|ZONE_LAST_UPDATED\|RETRIEVED_AT\|MAPPING_DATA\b\|MAPPING_DATA_LAST_UPDATED" custom_components/irrigation_plus/store.py | head -20
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_time_migration.py -p _local_socket_unblock -v
```
Erwartet: 5 passed.

- [ ] **Step 5: Die bestehenden Migrationstests dürfen nicht brechen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_store_legacy_migrations.py tests/test_schedule_migration_v14.py tests/test_batch_config_survives_v14.py tests/test_unit_system_migration.py tests/test_store.py -p _local_socket_unblock -q
```
Erwartet: passed. Ein Test, der `STORAGE_VERSION == 14` fest verdrahtet, wird auf 15 gezogen.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/store.py tests/test_weather_buffer_time_migration.py
git commit -F - <<'EOF'
feat(store): v15 migrates stored weather-buffer stamps to aware

Existing naive stamps were written by a bare datetime.now(), so the
migration attaches the PROCESS's zone -- the one they were written in --
and not HA's configured zone, which is how they were mistakenly read.

Watermark and buffer move in the same pass. A wrong assumption is then a
uniform translation of the stored time axis and cancels in select_window's
retrieved > watermark; moving one side alone is the only way to re-admit
readings a zone already consumed.

The assumption is stated in full in the migration, together with the
reason no detection is attempted: the autumn DST transition runs the naive
sequence an hour backwards, which is byte-identical to a container TZ fix.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Gesamtabnahme

**Files:** keine

- [ ] **Step 1: Volle Suite**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q
```
Erwartet: nur `tests/test_panel.py::test_async_register_panel_static_path_config` rot.

Gegenprobe, falls etwas anderes rot ist — auf unverändertem `upstream/master` laufen lassen und
vergleichen, bevor es als Regress behandelt wird:

```bash
git stash && git checkout upstream/master -- custom_components/ && \
  ./.venv/Scripts/python.exe -m pytest tests/<verdaechtig> -p _local_socket_unblock -q
```

- [ ] **Step 2: Restliche naive Schreiber suchen (Schwester-Pfad-Check)**

```bash
grep -rn "datetime\.now()" custom_components/irrigation_plus/*.py | grep -v dt_util
```
Erwartet übrig: nur `services.py:273/289` und `watering_calendar.py:79/93` (`generated_at`, reine
Anzeigewerte, erreichen den Store nicht) sowie `helpers._process_timezone` selbst. Alles andere ist
eine übersehene Stelle und kommt in denselben PR.

- [ ] **Step 3: Lint (nur diese zwei zählen in CI)**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```
Erwartet: black reformatiert höchstens, ruff meldet nichts. Reformatierungen mit committen.

- [ ] **Step 4: Kein Frontend-Build nötig**

Diese Arbeit fasst `frontend/` nicht an. Gegenprobe:

```bash
git diff --name-only upstream/master...HEAD -- custom_components/irrigation_plus/frontend/
```
Erwartet: leer. Ist sie es nicht, gilt die Palette (`npm ci && npm run build`, dist mit `git add -f`).

- [ ] **Step 5: Commit etwaiger Lint-Korrekturen**

```bash
git add custom_components/irrigation_plus/
git commit -m "style: black" || echo "nichts zu committen"
```

---

## Danach (nicht Teil dieses Plans)

- **Design-Historie archivieren** (Regel P1): Spec + dieser Plan auf `archive/design-history`,
  VOR jeder Branch-Löschung. Rezept: Memory `preserve-design-docs-archive-branch`.
- **(D)** Doku-Absatz `TZ=` — geht **vor** diesem PR raus, eigener Branch, eigener PR.
- **(C)** Laufzeit-Check Prozess-Offset vs. HA-Offset — eigener PR, nach A+B.
- **Upstream-PR** nach Skill `pr-workflow` und Memory `hasi-pr-build-recipe`; Body vorher im Chat
  freigeben (globale Regel „Text-Freigabe").
