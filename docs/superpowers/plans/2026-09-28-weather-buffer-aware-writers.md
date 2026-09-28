# Weather buffer: the write side moves into HA's zone — Implementation Plan

> ⛔ **SUPERSEDED — DO NOT EXECUTE.** Checked against the code before any line was built
> (2026-09-28): Task 1 turns the daily calculation's correct 1.0 h window into 3.0 h and the
> live estimate's 3.0 h into 5.0 h; Tasks 4–6 then raise `TypeError` on a store holding both
> naive and aware stamps; and this plan's own end-to-end pin 2 stays green through all of it.
> See Revision 4, `specs/2026-09-28-weather-buffer-one-frame-design.md`, and the probes it
> cites. Kept unchanged below as history.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every weather-buffer timestamp mean one thing — naive HA-local inside the
integration, aware HA-local in the store — so the live estimate stops subtracting across
two clocks on installs where the process zone and HA's configured zone disagree.

**Architecture:** `coerce_stamp(value, provenance)` (shipped by `JustChr#177`) stays the
single funnel and keeps normalising **to naive**, but `STAMP_FROM_STORE` changes what it
normalises *to*: naive HA-local instead of naive process-local. A legacy naive value is
read in the process zone and lifted; an aware value goes through `as_local`. Writers move
to `dt_util.now()`, so new stamps are self-describing and the process-zone assumption
stops being load-bearing for anything but data already in the store.

**Tech Stack:** Python 3.12, Home Assistant custom component, `homeassistant.util.dt`,
pytest + `pytest-homeassistant-custom-component`.

**Spec:** `docs/superpowers/specs/2026-09-28-weather-buffer-aware-writers-design.md`
(Revision 3; on `archive/design-history` as `6ce399f8`).

**Base:** `upstream/master` = `1876aa03`. **Branch:** `fix/weather-buffer-aware-writers`.

---

## Environment

All commands run from the worktree `D:\Entwicklung\HASI\issue22-work\wt`. There is **no**
`.venv` in a worktree — address the interpreter absolutely:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```

**Baseline on `1876aa03`, measured 2026-09-28:** 7 failed / 3455 passed / 9 skipped /
**367 errors**. All 367 errors are `Failed: Lingering timer after test`, a teardown
artifact of this Windows env, not a defect. **Only the delta is meaningful.** Stored at
`/d/Entwicklung/HASI/issue22-work/measure/baseline-1876aa03.txt`.

Count failures with the directory in the filter, or a log line counts:

```bash
grep -cE "^(FAILED|ERROR) tests/" <resultfile>
```

Read a result file only **after** the run ends.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/helpers.py` | the one coercion rule + the named "now" in that frame | modify `coerce_stamp`; add `local_naive_now()` |
| `custom_components/irrigation_plus/weather_aggregate.py` | window/row reduction; deliberately free of `homeassistant` imports | 3 `now` defaults → `local_naive_now()` |
| `custom_components/irrigation_plus/calculation.py` | daily calc, buffer prune | 5 writers |
| `custom_components/irrigation_plus/continuous_update.py` | event-driven ingestion | 3 writers + `dt_util` import |
| `custom_components/irrigation_plus/__init__.py` | coordinator, polls | 7 writers |
| `custom_components/irrigation_plus/store.py` | persistence | 1 writer + `dt_util` import |
| `tests/test_time_provenance.py` | the vocabulary pins | 2 existing tests inverted |
| `tests/test_weather_buffer_frame.py` | **new** — the two end-to-end seam pins | create |
| `tests/test_stored_stamp_is_self_describing.py` | **new** — writers produce aware | create |

`weather_aggregate.py` keeps its HA-free import list; that is why the "now" default is
named in `helpers.py` and imported, rather than `dt_util` being pulled into it.

---

### Task 1: The reader frame moves — one internal zone

This is the change JustChr asked to be pinned: "a stored stamp written under one process
zone, read back under a different HA zone, asserting the elapsed window is the real one."

**Files:**
- Create: `tests/test_weather_buffer_frame.py`
- Modify: `tests/test_time_provenance.py:51-81` (two existing tests invert)
- Modify: `custom_components/irrigation_plus/helpers.py:1055-1060`

- [ ] **Step 1: Write the failing end-to-end pins**

Create `tests/test_weather_buffer_frame.py`:

```python
"""The seam: a buffer written on the process clock, read against HA's.

Both assertions are required and they fail for different reasons. The first is the
elapsed-window drift the upstream report describes. The second is the expensive half
-- `calculation.py:796` warns that the solar offset does NOT travel as `tzinfo`, it
travels as a float into `row["tz_offset_h"]`, so a stamp that merely becomes aware
"leaves this arithmetic untouched and the suite green".

What moves is `row["hour"]`, the local clock midpoint -- NOT `tz_offset_h`, which is
+2.0 under either zone in summer. The defect is the mismatched PAIR: hour 10.5 read
off a UTC wall clock, charged against Berlin's +2 offset, puts the row 2 h out in
solar time. That is the +23.5 % / -16 % on Rso.
"""

import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import const, helpers
from custom_components.irrigation_plus.helpers import (
    STAMP_FROM_STORE,
    coerce_stamp,
)
from custom_components.irrigation_plus.weather_aggregate import build_hourly_rows

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


@pytest.fixture
def split_zones(monkeypatch):
    """Container at UTC, user at Europe/Berlin -- the case that separates the two.

    Restored to UTC rather than to whatever was found: the test plugin asserts UTC at
    teardown, and monkeypatch would faithfully put back a leaked value.
    """
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(UTC)


def test_the_elapsed_window_is_the_real_one(split_zones):
    """One hour of real time must not be read as three.

    This is requirement 2 in executable form. The anchor was written by a bare
    `datetime.now()` on a UTC process, so its naive form is 10:00 -- the instant
    10:00Z, which is 12:00 on the user's clock. An hour later the user's clock reads
    13:00. Read in one frame the window is 1 h; read across two clocks it is 3 h.

    Both stamps are fixed rather than taken from the clock, so the assertion is a
    number and not a tolerance.
    """
    anchor_naive = datetime.datetime(2026, 7, 15, 10, 0)
    now_local = datetime.datetime(2026, 7, 15, 13, 0)

    anchor = coerce_stamp(anchor_naive, STAMP_FROM_STORE)
    elapsed_hours = (now_local - anchor).total_seconds() / 3600.0

    assert anchor == datetime.datetime(2026, 7, 15, 12, 0)
    assert anchor.tzinfo is None
    assert elapsed_hours == 1.0


def test_the_row_hour_is_the_local_clock_hour(split_zones):
    """The expensive half: the row's wall-clock hour must be HA's, not the process's.

    A reading at 10:00Z is 12:00 on the user's clock. `row["hour"]` is the local
    clock midpoint, so it must be 12.5. Today the stamp is read as 10:00 and the row
    reports 10.5 while `tz_offset_h` still says +2.0 -- the pair that is 2 h out in
    solar time.
    """
    readings = [
        {
            const.RETRIEVED_AT: datetime.datetime(2026, 7, 15, 10, 0),
            const.MAPPING_TEMPERATURE: 20.0,
            const.MAPPING_HUMIDITY: 50.0,
            const.MAPPING_WINDSPEED: 2.0,
            const.MAPPING_SOLRAD: 2.5,
        },
        {
            const.RETRIEVED_AT: datetime.datetime(2026, 7, 15, 11, 0),
            const.MAPPING_TEMPERATURE: 21.0,
            const.MAPPING_HUMIDITY: 48.0,
            const.MAPPING_WINDSPEED: 2.2,
            const.MAPPING_SOLRAD: 2.7,
        },
    ]

    rows = build_hourly_rows(
        readings,
        None,
        {},
        now=datetime.datetime(2026, 7, 15, 13, 0),
        latitude=50.0,
        longitude=6.0,
        elevation=200.0,
        tz=BERLIN,
    )

    assert rows, "expected hourly rows for a two-reading window"
    hours = [r["hour"] for r in rows]
    assert min(hours) >= 12.0, (
        f"row hours {hours} are on the process clock; HA's clock starts at 12.5"
    )
    assert rows[0]["tz_offset_h"] == 2.0
```

- [ ] **Step 2: Run the pins to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_frame.py -p _local_socket_unblock -v
```

Expected: **both FAIL.** `test_the_elapsed_window_is_the_real_one` with
`assert datetime(2026,7,15,10,0) == datetime(2026,7,15,12,0)` — the naive value came
back untouched, and `elapsed_hours` is 3.0 rather than 1.0.
`test_the_row_hour_is_the_local_clock_hour` with `row hours [10.5, 11.5] are on the
process clock`.

If either passes, stop: the frame is not what this plan assumes and the rest of it is
invalid.

- [ ] **Step 3: Invert the two existing vocabulary pins**

In `tests/test_time_provenance.py`, replace `test_the_same_instant_coerces_differently_per_provenance`
(line 51) and `test_a_naive_value_is_returned_unchanged_under_either_provenance`
(line 68) with these two. The truth inverts: it is the **naive** input that diverges now,
and the **aware** input that converges.

```python
def test_a_naive_value_coerces_differently_per_provenance(split_zones):
    """The divergence moved to the naive input, which is where the ambiguity lives.

    A naive STORED stamp was written by a bare `datetime.now()`, so 10:00 on a UTC
    process is the instant 10:00Z and reads as 12:00 on the user's clock. A naive
    CLIENT row is already a site-local clock time, so 10:00 means 10:00 and stays.
    """
    naive = datetime.datetime(2026, 9, 21, 10, 0)

    stored = coerce_stamp(naive, STAMP_FROM_STORE)
    client = coerce_stamp(naive, STAMP_FROM_CLIENT)

    assert stored == datetime.datetime(2026, 9, 21, 12, 0)
    assert client == datetime.datetime(2026, 9, 21, 10, 0)
    assert stored - client == datetime.timedelta(hours=2)
    assert stored.tzinfo is None and client.tzinfo is None


def test_an_aware_value_coerces_the_same_under_either_provenance(split_zones):
    """What the write-side change buys: an aware stamp has no ambiguity left.

    Both provenances resolve it through `as_local`, so the result no longer depends
    on which rule the reader picked -- nor on the process zone at all. This is the
    property that retires the migration's assumption for every stamp written from
    the upgrade onward.
    """
    instant = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    stored = coerce_stamp(instant, STAMP_FROM_STORE)
    client = coerce_stamp(instant, STAMP_FROM_CLIENT)

    assert stored == client == datetime.datetime(2026, 9, 21, 12, 0)
    assert stored.tzinfo is None
    assert coerce_stamp("2026-09-21T10:00:00+00:00", STAMP_FROM_STORE) == stored
```

- [ ] **Step 4: Run them to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py -p _local_socket_unblock -v
```

Expected: the two new tests **FAIL**, the other four still pass.

- [ ] **Step 5: Flip `coerce_stamp`'s store branch**

In `custom_components/irrigation_plus/helpers.py`, replace the tail of `coerce_stamp`
(currently lines 1055-1060):

```python
    if parsed.tzinfo is None:
        return parsed
    if provenance == STAMP_FROM_STORE:
        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)
    return dt_util.as_local(parsed).replace(tzinfo=None)
```

with:

```python
    if provenance == STAMP_FROM_STORE and parsed.tzinfo is None:
        # Legacy: written by a bare `datetime.now()`, so this wall clock is the
        # PROCESS's. Read it there, then lift it into the one frame everything on
        # these paths compares in.
        parsed = parsed.replace(tzinfo=_process_timezone())
    if parsed.tzinfo is None:
        # A naive CLIENT row is already a site-local clock time, i.e. HA's zone.
        return parsed
    return dt_util.as_local(parsed).replace(tzinfo=None)
```

- [ ] **Step 6: Run both test files to verify they pass**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_frame.py tests/test_time_provenance.py -p _local_socket_unblock -v
```

Expected: **all PASS** — 2 new end-to-end pins + 6 in `test_time_provenance.py`.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/helpers.py tests/test_time_provenance.py tests/test_weather_buffer_frame.py
git commit -F - <<'EOF'
fix(time): read a stored stamp into HA's zone, not the process's

The buffer was stamped on the process clock and compared against HA's.
Both naive, so nothing raised -- the subtraction just measured across two
clocks on every install where the two zones differ, which is Container
without `-e TZ=` and Core on a UTC host.

coerce_stamp keeps normalising to naive; what changes is the target frame
for STAMP_FROM_STORE. A legacy naive value is read in the process zone and
lifted into HA's; an aware value goes through as_local. Both provenances
now mean one frame, so the comparison happens in one zone.

The two vocabulary pins invert with it: the divergence belongs to the
NAIVE input, and an aware input resolves identically under either rule --
which is the property the write side is about to start producing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Measure the delta and reclassify the fixtures it exposes

JustChr expected this change "small in code and large only in tests". This task is where
that shows up. Nothing here may change production code.

**Files:**
- Modify: whichever test files the delta in Step 2 names.

This is the one task whose file list cannot be written in advance, and that is
deliberate rather than an omission: naming files here would mean predicting which
fixtures encode the old frame, and a predicted list is exactly what makes an
implementer "fix" a test that was actually right. Step 2 produces the list by
measurement; Step 3 gives the rule for deciding each entry.

- [ ] **Step 1: Run the full suite into a file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/after-task1.txt 2>&1; echo "exit $?"
```

Wait for the command to finish before reading the file.

- [ ] **Step 2: Diff against the baseline**

```bash
cd /d/Entwicklung/HASI/issue22-work/measure
echo "baseline: $(grep -cE '^(FAILED|ERROR) tests/' baseline-1876aa03.txt)"
echo "after   : $(grep -cE '^(FAILED|ERROR) tests/' after-task1.txt)"
grep -E "^(FAILED|ERROR) tests/" baseline-1876aa03.txt | sed 's/ - .*//' | sort > b.txt
grep -E "^(FAILED|ERROR) tests/" after-task1.txt     | sed 's/ - .*//' | sort > a.txt
echo "--- NEW failures (the delta that matters) ---"; comm -13 b.txt a.txt
echo "--- disappeared ---"; comm -23 b.txt a.txt
```

Expected: the baseline's 374 are unchanged in composition; the new entries are tests
whose fixtures encode the old frame.

- [ ] **Step 3: Reclassify each new failure, one at a time**

For every test in the NEW list, decide and record which of the two it is:

1. **A fixture that carried a process-local stamp and asserted a process-local
   result.** Correct fix: state the stamp's provenance in the fixture. If it stands for
   something the store wrote, it is `STAMP_FROM_STORE` and the expectation moves by the
   offset. If it stands for a weather-client row, it belongs in HA's zone already and
   the fixture should say so.
2. **A real regression.** Stop and treat it as one — a changed expectation is only
   legitimate when the old expectation encoded the defect.

Read a reddening test as "is this state even reachable?" before editing it
(memory `narrowing-exposes-impossible-fixtures`).

- [ ] **Step 4: Re-run and confirm the delta is zero**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/after-task2.txt 2>&1; echo "exit $?"
```

Then re-run Step 2's diff against `after-task2.txt`. Expected: **NEW list empty.**

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -F - <<'EOF'
test(time): say which clock each buffer fixture was written on

These fixtures asserted process-local results because the code produced
them. With one internal frame the same stamps read in HA's zone, so each
fixture now names the provenance it stands for instead of leaving it to
the reader.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Name "now" in the one frame, and use it for the three defaults

`build_hourly_rows`, `aggregate_window` and `select_window`'s siblings default `now` to a
bare `datetime.datetime.now()`. After Task 1 that default is in the wrong frame: every
call that passes no `now` compares HA-local row stamps against a process-local now.

`weather_aggregate.py` deliberately imports no `homeassistant` module, so the frame is
named once in `helpers.py` and imported.

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py` (after `coerce_stamp`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py:45`, `:370`, `:938`, `:1133`
- Test: `tests/test_time_provenance.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_time_provenance.py`, add the third zone beside the existing two
(the file currently defines only `UTC` and `BERLIN`):

```python
TOKYO = zoneinfo.ZoneInfo("Asia/Tokyo")
```

Then append:

```python
def test_the_default_now_follows_has_zone():
    """The default `now` must track HA's configured zone, not the machine's.

    Every entry point on these paths defaults `now` when the caller passes none. A
    process-local default is then compared against HA-local row stamps, which is the
    same two-clock subtraction one level up.

    Pinned by MOVING HA's zone rather than by restating the implementation: the
    machine's own clock cannot be moved from a test (`time.tzset()` does not exist on
    Windows), so the observable is that the value follows HA when HA changes. An
    assertion against `dt_util.now().replace(tzinfo=None)` would just be the function's
    own body and would pass the moment it exists.

    Restored to UTC rather than to what was found: the test plugin asserts UTC at
    teardown.
    """
    try:
        dt_util.set_default_time_zone(BERLIN)
        berlin_now = helpers.local_naive_now()
        dt_util.set_default_time_zone(TOKYO)
        tokyo_now = helpers.local_naive_now()
    finally:
        dt_util.set_default_time_zone(UTC)

    assert berlin_now.tzinfo is None and tokyo_now.tzinfo is None
    # Tokyo is +9 all year; Berlin is +2 in summer and +1 in winter.
    delta_hours = (tokyo_now - berlin_now).total_seconds() / 3600.0
    assert 6.5 < delta_hours < 8.5
```

- [ ] **Step 2: Run it to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py::test_the_default_now_follows_has_zone -p _local_socket_unblock -v
```

Expected: FAIL with `AttributeError: module 'custom_components.irrigation_plus.helpers' has no attribute 'local_naive_now'`.

- [ ] **Step 3: Add the helper**

In `custom_components/irrigation_plus/helpers.py`, directly after `coerce_stamp`:

```python
def local_naive_now() -> datetime:
    """"Now" in the one frame the weather-buffer paths compare in: naive HA-local.

    Wurzel: the entry points defaulted `now` to a bare ``datetime.now()``, i.e. the
      PROCESS's clock, while the stamps it is compared against are HA-local. Every
      call that passed no `now` therefore reintroduced the very subtraction across
      two clocks that the coercion above removes.
    Fix: one named function for the frame, so a caller cannot pick the wrong clock by
      omission, and so ``weather_aggregate`` keeps its ``homeassistant``-free imports.
    NOT-TO-DO: do not inline ``dt_util.now().replace(tzinfo=None)`` at the call sites.
      There are three of them and they must not drift; the stripping is also the exact
      step a future reader would "simplify" into an aware value and detonate the
      blanket ``except`` in the live estimate.
    siehe tests/test_time_provenance.py::test_now_in_the_internal_frame_is_has_clock
    """
    return dt_util.now().replace(tzinfo=None)
```

- [ ] **Step 4: Run it to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py -p _local_socket_unblock -v
```

Expected: PASS, 7 tests.

- [ ] **Step 5: Point the three defaults at it**

In `custom_components/irrigation_plus/weather_aggregate.py`, change the import on line 45:

```python
from .helpers import STAMP_FROM_STORE, coerce_stamp, local_naive_now
```

Then at **each** of lines 370, 938 and 1133 — all three have the identical shape, and
they are sister paths that move together — replace:

```python
        else datetime.datetime.now()
```

with:

```python
        else local_naive_now()
```

- [ ] **Step 6: Verify all three moved and none was missed**

```bash
grep -n "datetime.datetime.now()" custom_components/irrigation_plus/weather_aggregate.py
```

Expected: **no output.** Then:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_aggregate.py tests/test_weather_buffer_frame.py -p _local_socket_unblock -q
```

Expected: no new failures against the baseline composition.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/helpers.py custom_components/irrigation_plus/weather_aggregate.py tests/test_time_provenance.py
git commit -F - <<'EOF'
fix(time): default "now" to HA's clock, not the container's

The three entry-point defaults were a bare datetime.now(), so any call
that passed no `now` compared HA-local row stamps against a process-local
now -- the same two-clock subtraction, one level up.

Named once in helpers rather than inlined three times, which also keeps
weather_aggregate free of homeassistant imports.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Writers produce self-describing stamps — the pin, on the cheapest path

This is the property that retires the assumption: an aware stamp reads back to the same
instant **whatever the process zone is now**, so a user who fixes `TZ` after upgrading
loses nothing.

**Files:**
- Create: `tests/test_stored_stamp_is_self_describing.py`
- Modify: `custom_components/irrigation_plus/store.py` (import + line 1653)

- [ ] **Step 1: Write the failing test**

Create `tests/test_stored_stamp_is_self_describing.py`:

```python
"""A stamp written now must not depend on the process zone at read time.

JustChr's one reservation on the migration: a naive stored stamp is only
unambiguously process-local as long as the process TZ has not changed since it was
written. Someone who fixes their container's `TZ` and *then* upgrades has old stamps
from the old zone, and no detector can tell (see D4 in the spec -- a DST fall-back
has the identical signature).

The fix is not detection, it is removing the ambiguity going forward: an aware stamp
carries its own offset, so the read no longer consults the process zone at all. This
pins exactly that, by moving the process zone between write and read.
"""

import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import const, helpers
from custom_components.irrigation_plus.helpers import STAMP_FROM_STORE, coerce_stamp
from custom_components.irrigation_plus.store import SmartIrrigationStorage

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
TOKYO = zoneinfo.ZoneInfo("Asia/Tokyo")


@pytest.fixture
def ha_on_berlin(monkeypatch):
    """HA on Europe/Berlin; the process zone is set per-test by the test itself."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(UTC)


async def test_a_new_zones_watermark_is_written_aware(hass, hass_storage):
    """The writer's own pin, driven through the production path.

    `async_create_zone` anchors the consumption watermark at creation time. While it
    stamps a bare `datetime.now()` the persisted value carries no offset, so reading
    it back has to assume which clock wrote it. An aware value removes the question.

    This is the RED for the write side: it exercises the changed function rather than
    a neighbour of it (memory `verification-must-exercise-the-change`).
    """
    store = SmartIrrigationStorage(hass)
    await store.async_load()

    zone = await store.async_create_zone({const.ZONE_NAME: "Front"})

    assert zone[const.ZONE_LAST_CONSUMED].tzinfo is not None


def test_an_aware_stamp_survives_the_process_zone_changing(ha_on_berlin, monkeypatch):
    """Write under one process zone, read under another, same instant.

    This is the whole point of the write-side change. With a naive stamp the read
    applies whatever the process zone is NOW, so the value moves by the difference;
    with an aware stamp there is nothing left to assume.
    """
    written_aware = dt_util.now()

    first_read = coerce_stamp(written_aware, STAMP_FROM_STORE)
    # The user fixes their container's TZ and restarts: same stored bytes, new
    # process zone.
    monkeypatch.setattr(helpers, "_process_timezone", lambda: TOKYO)
    second_read = coerce_stamp(written_aware, STAMP_FROM_STORE)

    assert first_read == second_read


def test_a_naive_stamp_does_not_survive_it(ha_on_berlin, monkeypatch):
    """The contrast, so the test above is not vacuous.

    Kept as a pin rather than deleted: it states the size of what the write-side
    change removes, and it is the assertion that would go green again if someone
    "simplified" a writer back to a bare datetime.now().
    """
    written_naive = dt_util.now().replace(tzinfo=None)

    first_read = coerce_stamp(written_naive, STAMP_FROM_STORE)
    monkeypatch.setattr(helpers, "_process_timezone", lambda: TOKYO)
    second_read = coerce_stamp(written_naive, STAMP_FROM_STORE)

    assert first_read != second_read
```

- [ ] **Step 2: Run it to verify the first test fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_stored_stamp_is_self_describing.py -p _local_socket_unblock -v
```

Expected:

- `test_a_new_zones_watermark_is_written_aware` **FAILS** with
  `AssertionError: assert None is not None` — the persisted watermark is naive. This is
  the RED for the write side.
- the two `*_survives_the_process_zone_changing` tests **PASS** already, because
  `coerce_stamp` routes aware values through `as_local` after Task 1. They are
  characterisation pins, kept deliberately: together they state the size of what the
  write side removes, and `test_a_naive_stamp_does_not_survive_it` is the assertion that
  turns red if someone later "simplifies" a writer back to a bare `datetime.now()`
  (memory `regression-pin-on-removals`).

If `test_a_new_zones_watermark_is_written_aware` passes, stop — a writer already moved
and the plan's accounting of 16 sites is wrong.

- [ ] **Step 3: Move `store.py`'s writer**

In `custom_components/irrigation_plus/store.py`, add the import after `import attr`
(line 10):

```python
import attr
import homeassistant.util.dt as dt_util
```

Then replace line 1653:

```python
            new_zone = attr.evolve(new_zone, last_consumed_at=datetime.datetime.now())
```

with:

```python
            new_zone = attr.evolve(new_zone, last_consumed_at=dt_util.now())
```

- [ ] **Step 4: Verify the store has no bare writer left**

```bash
grep -n "datetime.datetime.now()" custom_components/irrigation_plus/store.py
```

Expected: **no output.**

- [ ] **Step 5: Run the store tests to verify GREEN**

There are seven store test files; run them all, because `last_consumed_at` at creation
time is read by more than one of them:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_store.py tests/test_store_buffers.py tests/test_store_distributor.py tests/test_store_legacy_migrations.py tests/test_store_operations.py tests/test_store_self_closing.py tests/test_store_zone_explanation.py tests/test_stored_stamp_is_self_describing.py -p _local_socket_unblock -q
```

Expected: `test_a_new_zones_watermark_is_written_aware` **PASSES**, and no store test
that passed before now fails. A store test that asserted a naive `last_consumed_at` is a
fixture to reclassify by Task 2 Step 3's rule, not an expectation to overwrite blindly.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/store.py tests/test_stored_stamp_is_self_describing.py
git commit -F - <<'EOF'
fix(time): stamp a new zone's last_consumed_at in HA's zone

First of the writers. An aware stamp carries its own offset, so reading it
back stops consulting the process zone -- which is what removes the one
assumption the migration would otherwise have to keep making forever.

The two pins state the property and its contrast, so a later
"simplification" back to a bare datetime.now() turns one of them red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Writers in `calculation.py` and `continuous_update.py`

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py:267`, `:379`, `:432`, `:498`, `:934`
- Modify: `custom_components/irrigation_plus/continuous_update.py` (import + `:252`, `:378`, `:521`)

- [ ] **Step 1: Move the five in `calculation.py`**

`dt_util` is already imported (line 14). At lines 267, 432 replace:

```python
        now = datetime.now()
```

with:

```python
        now = dt_util.now()
```

At lines 379, 498, 934 replace:

```python
            now = datetime.now()
```

with:

```python
            now = dt_util.now()
```

- [ ] **Step 2: Add the import to `continuous_update.py`**

Insert before line 58 (`from homeassistant.const import (`):

```python
import homeassistant.util.dt as dt_util
```

- [ ] **Step 3: Move the three in `continuous_update.py`**

At lines 252 and 378 replace:

```python
        timestamp = datetime.now()
```

with:

```python
        timestamp = dt_util.now()
```

At line 521 replace:

```python
        now = datetime.now()
```

with:

```python
        now = dt_util.now()
```

- [ ] **Step 4: Verify nothing bare is left in either file**

```bash
grep -nE "(^|[^.\w])datetime\.now\(\)" custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/continuous_update.py
```

Expected: matches only inside comments and docstrings (`calculation.py:52`, `:789`,
`:1194` and the `NOT-TO-DO` block). **No assignment** may match.

- [ ] **Step 5: Run the suite and diff**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/after-task5.txt 2>&1; echo "exit $?"
```

Then Task 2 Step 2's diff, against `after-task5.txt`. Expected: NEW list empty, or only
fixtures that assert a naive stored value — reclassify those as in Task 2 Step 3.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/continuous_update.py tests/
git commit -F - <<'EOF'
fix(time): stamp the daily calc and the event ingestion in HA's zone

Eight more writers onto dt_util.now(). Both files wrote a bare
datetime.now() and compared the result against buffer stamps written the
same way, which was self-consistent and wrong together.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Writers in `__init__.py` — the sister path the issue does not name

The upstream report counts five plus three. `__init__.py` has seven more behind the
`dt_datetime` alias, including the interval poll that produces most buffer rows. Same
defect, different caller — and 1506 (on-demand single-zone update) and 1632 (interval
poll `_async_update_all`) belong in the same commit.

**Files:**
- Modify: `custom_components/irrigation_plus/__init__.py:1429`, `:1506`, `:1516`, `:1632`, `:1644`, `:1799`, `:2023`

- [ ] **Step 1: Move all seven**

`dt_util` is already imported (line 15). Replace, line by line:

| Line | From | To |
|---|---|---|
| 1429 | `            now = dt_datetime.now()` | `            now = dt_util.now()` |
| 1506 | `                weatherdata[const.RETRIEVED_AT] = dt_datetime.now()` | `                weatherdata[const.RETRIEVED_AT] = dt_util.now()` |
| 1516 | `                updated_at = dt_datetime.now()` | `                updated_at = dt_util.now()` |
| 1632 | `                weatherdata[const.RETRIEVED_AT] = dt_datetime.now()` | `                weatherdata[const.RETRIEVED_AT] = dt_util.now()` |
| 1644 | `                    const.ZONE_LAST_UPDATED: dt_datetime.now(),` | `                    const.ZONE_LAST_UPDATED: dt_util.now(),` |
| 1799 | `                now = dt_datetime.now()` | `                now = dt_util.now()` |
| 2023 | `                const.ZONE_LAST_CONSUMED: dt_datetime.now(),` | `                const.ZONE_LAST_CONSUMED: dt_util.now(),` |

- [ ] **Step 2: Verify the alias has no `.now()` caller left**

```bash
grep -n "dt_datetime" custom_components/irrigation_plus/__init__.py
```

Expected: the comment at line 10, the import at line 11, and **no `.now()` call**. If the
alias now has no remaining use at all, remove the import and its comment — a named alias
whose only stated purpose was `dt_datetime.now()` is dead weight, and ruff will say so.

- [ ] **Step 3: Run the suite and diff**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/after-task6.txt 2>&1; echo "exit $?"
```

Then Task 2 Step 2's diff, against `after-task6.txt`. Expected: NEW list empty.

- [ ] **Step 4: Commit**

```bash
git add custom_components/irrigation_plus/__init__.py tests/
git commit -F - <<'EOF'
fix(time): stamp the coordinator's polls in HA's zone

The sister path the report does not name: seven writers behind the
dt_datetime alias, including the interval poll that produces most buffer
rows and the on-demand single-zone update. Same defect, different caller,
so they move with the rest rather than after it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: State the assumption, and the alternative that was rejected

Requirement 3: "I would rather the migration state that assumption in a comment than have
it be implicit." The comment must also name the rejected alternative — otherwise a later
reader "repairs" the process zone to `DEFAULT_TIME_ZONE` to match `sensor.py`, which is
the original bug.

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py` (`coerce_stamp` docstring)

- [ ] **Step 1: Extend the docstring**

In `coerce_stamp`, replace the `Direction, and it is deliberate:` paragraph with:

```
    Direction, and it is deliberate: this normalises to NAIVE HA-local -- one frame for
      both provenances, so the subtraction happens in one zone. It does NOT produce an
      aware value: the callers sit inside a blanket ``except`` that turns a naive/aware
      mix into the live estimate quietly going unavailable with a plausible
      "last calculated" still on display.
    The one assumption, and it is load-bearing only for legacy data: a naive
      ``STAMP_FROM_STORE`` value is read in the PROCESS's current zone. That is correct
      as long as the process zone has not changed since the value was written. Someone
      who fixes their container's ``TZ`` and only then upgrades has stamps from the old
      zone, and for up to ``BUFFER_RETENTION`` (7 days) they read one offset out. A
      watermark error d costs exactly d/24 of one window's ETo -- 2 h is ~0.25 mm of
      bucket at 3 mm/day -- and then heals, because every stamp written from here on is
      aware and carries its own offset.
    NOT-TO-DO: do not add a detector for "the process zone changed". It is not expensive,
      it is impossible: at the autumn DST transition the naive series runs an hour
      BACKWARDS, which is byte-for-byte the signature a detector would look for, so it
      would fire for every DST user twice a year with the same error size it prevents. A
      future-dated clamp is direction-blind (the scenario above pushes stamps into the
      PAST, hit rate 0 %) and false-positive on boards without a buffered RTC. Pairing
      naive against aware stamps fails quantitatively, and on a freshly configured
      install -- exactly the one that just corrected its TZ -- there are no aware stamps
      to pair against.
    NOT-TO-DO: do not "repair" ``_process_timezone`` to ``dt_util.DEFAULT_TIME_ZONE`` to
      match ``sensor.py``. Reading a stored naive stamp in HA's zone IS the original
      defect; the whole point here is that the two are different questions.
```

- [ ] **Step 2: Verify the docstring still parses and the pins still hold**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py tests/test_weather_buffer_frame.py tests/test_stored_stamp_is_self_describing.py -p _local_socket_unblock -q
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add custom_components/irrigation_plus/helpers.py
git commit -F - <<'EOF'
docs(time): state the legacy assumption and why detection was rejected

Writes down what a naive stored stamp is assumed to mean, how long that
assumption can be wrong (one retention window), what it costs while it is
(~0.25 mm of bucket), and why no data-based detector can do better -- a
DST fall-back and a container TZ fix have the identical signature.

Also pins the repair a future reader would reach for first: pointing the
process zone at DEFAULT_TIME_ZONE to match sensor.py is the original bug.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Lint, final delta, and the release note

**Files:** none modified unless lint says so.

- [ ] **Step 1: Run the two linters CI actually gates on**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: black reformats nothing or reformats only touched files; ruff reports no
findings. Fix anything it names, then re-run both.

- [ ] **Step 2: Full suite, final measurement**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/final.txt 2>&1; echo "exit $?"
```

- [ ] **Step 3: Confirm the delta is only additions**

```bash
cd /d/Entwicklung/HASI/issue22-work/measure
echo "baseline: $(grep -cE '^(FAILED|ERROR) tests/' baseline-1876aa03.txt)"
echo "final   : $(grep -cE '^(FAILED|ERROR) tests/' final.txt)"
grep -E "^(FAILED|ERROR) tests/" baseline-1876aa03.txt | sed 's/ - .*//' | sort > b.txt
grep -E "^(FAILED|ERROR) tests/" final.txt | sed 's/ - .*//' | sort > f.txt
echo "--- NEW (must be empty) ---"; comm -13 b.txt f.txt
tail -1 final.txt
```

Expected: **NEW list empty**, and the passed count risen by the tests this plan adds.

- [ ] **Step 4: Confirm every writer moved**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt
grep -rnE "(^|[^.\w])datetime\.now\(\)|dt_datetime\.now\(\)|datetime\.datetime\.now\(\)" \
  custom_components/irrigation_plus/ --include=*.py | grep -v "weathermodules/"
```

Expected: matches only in comments, docstrings and `helpers._process_timezone` (which
must keep its bare `datetime.now()` — that is how it reads the process zone). The
`weathermodules/` exclusion is deliberate and documented in the spec: those are
in-process TTL comparisons, never stored, and moving one side would introduce a defect.

- [ ] **Step 5: Note for the release text, not code**

Record for the PR body, in this order — the spec says the radiation leads:

1. **+23.5 % / −16 % on the clearness-ratio radiation**, because Rso is a denominator
   there. The larger error and the one that surprised everyone.
2. The elapsed-window drift: every live window one UTC offset too long, constant through
   the day, ~0.8–1.0 mm too negative at a summer ETo near 4 mm/day — enough to flip a
   skip decision.

- [ ] **Step 6: Final commit if anything changed**

```bash
git status --short
git add -u custom_components/irrigation_plus/
git commit -F - <<'EOF'
style(time): black/ruff on the touched modules

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

If `git status` is clean, skip this step — do not create an empty commit.

---

## Out of scope — do not touch in this plan

- **`weathermodules/*.py`, 11 sites.** In-process TTL comparisons
  (`datetime.now() < fetched_at + timedelta(ttl)`): same clock, same process, never
  stored, never compared against HA time. No defect, and moving one side creates one.
- **`generated_at`, 4 sites** (`services.py:273`, `:289`, `watering_calendar.py:79`,
  `:93`). Display values that never reach the store and are never subtracted.
- **Aware internals**, **any reconstruction of the old zone**, **any future clamp**, **any
  heuristic**.
- **No `STORAGE_VERSION` bump.** Coercion is at read time. A bump rewrites stamps to
  aware, and a HACS rollback then reads them with code that has no coercion — the silent
  live-estimate failure this work exists to remove.
- **The `exc_info=True` one-liner** on `_intraday_for_zone`'s blanket `except`, and **the
  runtime process-vs-HA zone warning.** Both are their own PRs; JustChr must be able to
  decline either without blocking this fix.

## Before calling this done

- [ ] The design doc and this plan are on `archive/design-history` (Regel P1). They must
      **never** be staged on this branch: both name `Eifel-Joe#22`, and no text reaching
      JustChr may reference our tracker (memory `no-own-issue-refs-upstream`, absolute).
- [ ] `grep -rn "Eifel-Joe" custom_components/ tests/` is empty before any push.
- [ ] The two end-to-end assertions were seen **RED** on `1876aa03`, not assumed.
