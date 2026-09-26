# Forecast weighting from the run's start — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The experimental forecast weighting measures its look-ahead window from the run it is about to size, not from the moment the calculation happens.

**Architecture:** A new bucket-free resolver on `RecurringScheduleManager` answers "when does this zone's next scheduled run begin". `calculate_module` hands that instant to the existing `forecast_window.expected_rain` instead of slicing the forecast list by position. Where no start resolves, or the forecast does not cover the run's first 24 hours, the weighting abstains — which means watering the full amount, the safe direction.

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest with `pytest-homeassistant-custom-component`.

**Spec:** `docs/superpowers/specs/2026-09-26-forecast-weighting-from-run-start-design.md`

**Base:** `upstream/master` = `10bb8077`. Worktree `D:/Entwicklung/HASI/issue21-work/wt`, branch `fix/forecast-weighting-from-run-start`.

---

## Before you start

**Canonical test command** (from the project `CLAUDE.md` — do not re-derive it):

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```

**Lint, both CI gates, before any push:**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

**A throwaway repro exists** at `tests/test_zz_repro_issue21.py`. It asserts today's buggy behaviour and is green on `10bb8077`. Leave it in place while you work — it is the cross-check that you are changing what you think you are changing. Task 8 removes it.

**Two things the spec warns about, repeated here because they bite during implementation:**

1. `expected_rain` needs **dated** daily entries. `forecast_window.day_span` returns `None` unless both `FORECAST_DAY_START` and `FORECAST_DAY_END` are present and carry a time zone. Undated entries contribute nothing.
2. A forecast fixture of **two** days leaves the run's 24-hour block only 18/24 covered, so `first_24h_covered` comes back `False` and the weighting abstains — which looks exactly like the fix not working. Use **seven** days in every fixture on this path. Measured: 2 abstains, 3 and above cover.

---

## File structure

| File | Responsibility | Touched by |
| --- | --- | --- |
| `custom_components/irrigation_plus/scheduler.py` | gains `async_next_run_start_for_zone` plus one private helper; nothing else changes | Tasks 1–3 |
| `custom_components/irrigation_plus/calculation.py:1104-1136` | the weighting block calls `expected_rain` instead of slicing | Tasks 6–7 |
| `tests/test_next_run_start_for_zone.py` | new module for the resolver, including the cycle pin | created in Task 1 |
| `tests/test_experimental_features.py` | the four existing weighting tests get dated fixtures and a resolvable start | Task 5 |
| `tests/test_forecast_weighting_window.py` | new module for the weighting's new window behaviour | created in Task 6 |
| `tests/test_zz_repro_issue21.py` | throwaway cross-check | deleted in Task 8 |

---

## Task 1: the resolver answers for a start-anchored schedule

**Files:**
- Modify: `custom_components/irrigation_plus/scheduler.py` (insert above `async_get_next_run_projection`)
- Test: `tests/test_next_run_start_for_zone.py` (create)

The recurrence math has its own tests. These tests patch `_next_governing_time` so they exercise **this** method's logic — zone matching, the armed preference, earliest-wins — and not the clock and sun resolution underneath it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_next_run_start_for_zone.py`:

```python
"""RecurringScheduleManager.async_next_run_start_for_zone (Eifel-Joe#21).

The forecast weighting runs inside calculate_module, so anything it calls that
reads a zone's bucket or duration closes a loop around the number being
computed. async_get_next_run_projection is therefore unusable there: it sizes
every zone from the bucket at the decision point. This resolver exists to answer
the one question the weighting needs -- when does the next run begin -- while
touching recurrence resolution only.

The recurrence math is tested in test_scheduler.py and the schedule-anchor
suites. These tests patch _next_governing_time so they exercise the resolver's
own decisions instead of re-testing its dependency.
"""

import datetime

import pytest

from custom_components.irrigation_plus import const

from tests.test_scheduler import _make_manager

UTC = datetime.timezone.utc
TARGET = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC)


def _schedule(sid="s1", zones="all", enabled=True):
    return {
        const.SCHEDULE_CONF_ID: sid,
        const.SCHEDULE_CONF_ENABLED: enabled,
        const.SCHEDULE_CONF_ZONES: zones,
        const.SCHEDULE_CONF_RECURRENCE: const.SCHEDULE_RECURRENCE_DAILY,
        const.SCHEDULE_CONF_START_MODE: const.SCHEDULE_BOUND_MODE_TIME,
        const.SCHEDULE_CONF_FINISH_MODE: const.SCHEDULE_BOUND_MODE_NONE,
    }


def _fixed_target(manager, target=TARGET):
    """Stand in for the clock/sun resolution, which has its own tests."""

    async def _governing(schedule, end, reference_utc=None):
        return target

    async def _advance(schedule, end, t, *, quiet=False):
        return t

    manager._next_governing_time = _governing
    manager._advance_past_fired_occurrence = _advance


@pytest.mark.asyncio
async def test_a_schedule_naming_all_zones_answers_for_any_zone():
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) == TARGET


@pytest.mark.asyncio
async def test_a_schedule_naming_the_zone_answers_for_it():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(zones=[2, 3])]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(3) == TARGET


@pytest.mark.asyncio
async def test_a_schedule_not_naming_the_zone_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(zones=[2, 3])]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_a_disabled_schedule_does_not_answer():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(enabled=False)]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_no_schedules_at_all_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = []

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_a_non_numeric_zone_id_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(None) is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 6 failed, every one with `AttributeError: Mock object has no attribute 'async_next_run_start_for_zone'` or `TypeError` — the method does not exist yet.

- [ ] **Step 3: Add the resolver**

In `custom_components/irrigation_plus/scheduler.py`, insert immediately **above** `async def async_get_next_run_projection`:

```python
    async def async_next_run_start_for_zone(self, zone_id):
        """When this zone's next scheduled run begins, in UTC, or None.

        Bucket-free by construction, and that is the whole point rather than a
        nicety. The forecast weighting runs inside ``calculate_module``, so
        anything it calls that reads a zone's bucket or duration closes a loop
        around the number being computed. ``async_get_next_run_projection`` is
        therefore NOT usable there: it sizes every zone from the bucket at the
        decision point and filters through the runner's guards. This resolver
        touches recurrence resolution only, and
        ``test_next_run_start_for_zone.py`` pins that it stays that way.

        The earliest answer across the schedules that name the zone wins: that is
        the run whose window the caller is about to price. None when no enabled
        schedule names it, or when none of them resolves a target -- an
        un-anchored interval schedule has no clock target at all.
        """
        try:
            zid = int(zone_id)
        except (TypeError, ValueError):
            return None
        best = None
        for schedule in self._schedules:
            if not schedule.get(const.SCHEDULE_CONF_ENABLED, True):
                continue
            # Raw "all"/list shape, the same way every other consumer takes it
            # (see _perform_scheduled_irrigation's note). The literal is what the
            # rest of this module compares against; there is no constant for it.
            zones = schedule.get(const.SCHEDULE_CONF_ZONES, "all")
            if zones != "all":
                try:
                    named = {int(z) for z in zones}
                except (TypeError, ValueError):
                    continue
                if zid not in named:
                    continue
            start = await self._next_run_start_for_schedule(schedule)
            if start is not None and (best is None or start < best):
                best = start
        return best

    async def _next_run_start_for_schedule(self, schedule: dict[str, Any]):
        """One schedule's next run start, without pricing anything.

        The target comes from the same resolvers ``_project_schedule`` uses, and
        nothing else: no ``_estimate_duration``, no ``_duration_bound``, no
        ``_decision_point``. Those are where the bucket would be read.
        """
        recurrence = schedule.get(const.SCHEDULE_CONF_RECURRENCE)
        governing, _paired = self._bounded_ends(schedule)
        if recurrence == const.SCHEDULE_RECURRENCE_INTERVAL:
            target = self._next_interval_target(schedule, dt_util.utcnow())
        elif governing is None:
            # Neither end bounded. Rejected at save time, but a document written
            # before that check still loads.
            return None
        else:
            target = await self._next_governing_time(schedule, governing)
            if target is not None:
                target = await self._advance_past_fired_occurrence(
                    schedule, governing, target, quiet=True
                )
        return target
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 6 passed.

- [ ] **Step 5: Run the scheduler oracles to verify nothing regressed**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_scheduler.py tests/test_schedule_time_anchor.py tests/test_schedule_tracker_rearm.py -p _local_socket_unblock -q --tb=short
```

Expected: all pass. Record the exact counts — Task 9 compares against them.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/scheduler.py tests/test_next_run_start_for_zone.py
git commit -F - <<'EOF'
feat(scheduler): answer when a zone's next scheduled run begins, without pricing it

The forecast weighting needs a run start and runs inside calculate_module, so it
cannot ask async_get_next_run_projection: that sizes every zone from the bucket
at the decision point, which is the number the weighting is in the middle of
computing. This resolver answers the same question from recurrence resolution
alone -- no _estimate_duration, no _duration_bound, no _decision_point -- and the
earliest schedule naming the zone wins.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 2: an armed run's start is preferred over the target

**Files:**
- Modify: `custom_components/irrigation_plus/scheduler.py` (`_next_run_start_for_schedule`)
- Test: `tests/test_next_run_start_for_zone.py`

A Finish-anchored schedule's start is `target - estimated duration`, and that estimate reads the bucket. The arm already computed the real start earlier, so where an arm exists it is both exact and free.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_next_run_start_for_zone.py`:

```python
ARMED_START = datetime.datetime(2026, 9, 28, 5, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_an_armed_run_supplies_the_exact_start():
    """The arm computed the real start earlier, and reading it costs nothing.

    For a Finish-anchored schedule the start is otherwise the target minus an
    estimated duration, and that estimate reads every zone's bucket -- the one
    call this resolver must not make.
    """
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)
    manager._armed_runs = {"s1": {"target": TARGET, "start_utc": ARMED_START}}

    assert await manager.async_next_run_start_for_zone(1) == ARMED_START


@pytest.mark.asyncio
async def test_an_arm_for_another_occurrence_is_ignored():
    """Proximity, not equality: a solar bound answers seconds apart each time."""
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)
    manager._armed_runs = {
        "s1": {
            "target": TARGET + datetime.timedelta(days=1),
            "start_utc": ARMED_START,
        }
    }

    assert await manager.async_next_run_start_for_zone(1) == TARGET


@pytest.mark.asyncio
async def test_an_arm_without_a_start_falls_back_to_the_target():
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)
    manager._armed_runs = {"s1": {"target": TARGET, "start_utc": None}}

    assert await manager.async_next_run_start_for_zone(1) == TARGET
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 1 failed (`test_an_armed_run_supplies_the_exact_start`, returning `TARGET` instead of `ARMED_START`), 8 passed. The other two already pass — they assert the fallback, which is Task 1's behaviour, and they are here to pin that the new branch does not swallow it.

- [ ] **Step 3: Prefer the arm**

In `_next_run_start_for_schedule`, replace the final line `return target` with:

```python
        if target is None:
            return None
        armed = self._armed_runs.get(schedule.get(const.SCHEDULE_CONF_ID))
        if (
            armed is not None
            and armed.get("start_utc") is not None
            and abs(armed["target"] - target) < SAME_OCCURRENCE
        ):
            # The arm's own start, computed when it armed. Exact even for a
            # Finish-anchored schedule, whose start is otherwise the target minus
            # an estimated duration -- and that estimate is the bucket-reading
            # call this resolver exists to avoid. Proximity rather than equality
            # for the reason _advance_past_fired_occurrence gives: a solar bound
            # answers a second or two later every time it is asked.
            return armed["start_utc"]
        # No arm: the governing target stands in. For a Finish-anchored schedule
        # that anchors the window at the run's END rather than its start, which is
        # at most one run length out against a 24-hour block. Stated in the spec
        # as accepted, not fixed.
        return target
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/scheduler.py tests/test_next_run_start_for_zone.py
git commit -F - <<'EOF'
feat(scheduler): prefer an armed run's own start over the schedule's target

A Finish-anchored schedule's start is the target minus an estimated duration, and
that estimate reads every zone's bucket. The arm already computed the real start,
so where one exists it is both exact and free to read. Without an arm the target
stands in, which anchors the window at the run's end instead of its start -- at
most one run length out against a 24-hour block.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 3: the earliest schedule wins

**Files:**
- Test only: `tests/test_next_run_start_for_zone.py`

Task 1's loop already takes the minimum. This task pins it, because a later edit that returns on the first match would pass every test written so far.

- [ ] **Step 1: Write the test**

Append to `tests/test_next_run_start_for_zone.py`:

```python
@pytest.mark.asyncio
async def test_the_earliest_of_several_schedules_wins():
    """Two schedules name the zone; the sooner run is the one being priced."""
    manager, _ = _make_manager()
    manager._schedules = [_schedule("late", zones=[1]), _schedule("soon", zones=[1])]
    later = TARGET + datetime.timedelta(hours=8)

    async def _governing(schedule, end, reference_utc=None):
        return TARGET if schedule[const.SCHEDULE_CONF_ID] == "soon" else later

    async def _advance(schedule, end, t, *, quiet=False):
        return t

    manager._next_governing_time = _governing
    manager._advance_past_fired_occurrence = _advance

    assert await manager.async_next_run_start_for_zone(1) == TARGET


@pytest.mark.asyncio
async def test_a_schedule_that_resolves_nothing_does_not_hide_one_that_does():
    """The unresolvable one is listed first, so a short-circuit would lose the other."""
    manager, _ = _make_manager()
    manager._schedules = [_schedule("dead", zones=[1]), _schedule("live", zones=[1])]

    async def _governing(schedule, end, reference_utc=None):
        return None if schedule[const.SCHEDULE_CONF_ID] == "dead" else TARGET

    async def _advance(schedule, end, t, *, quiet=False):
        return t

    manager._next_governing_time = _governing
    manager._advance_past_fired_occurrence = _advance

    assert await manager.async_next_run_start_for_zone(1) == TARGET
```

- [ ] **Step 2: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 11 passed. Both pass on Task 1's code — that is intended, they are pins.

- [ ] **Step 3: Prove the pins are sharp by mutation**

Change the loop body in `async_next_run_start_for_zone` from

```python
            if start is not None and (best is None or start < best):
                best = start
```

to

```python
            if start is not None:
                return start
```

then run the file again. Expected: **1 failed** —
`test_the_earliest_of_several_schedules_wins` only. This mutation short-circuits on a
non-`None` result, and the unresolvable schedule returns `None`, so the loop still reaches the
one behind it. Measured 2026-09-26; an earlier draft of this plan predicted two and was wrong.

The mutation that covers both replaces the whole loop body with a return on the first
**matching** schedule, resolved or not:

```python
            return await self._next_run_start_for_schedule(schedule)
```

Expected: **2 failed**, both pins. Revert and confirm 11 passed again. Run both mutations —
the pair is what shows that "earliest wins" and "no short-circuit" are two separate
properties, each with its own failure mode.

A test that is green before and after the change it claims to cover is unproven. This branch treats a mutation check as the proof, not as a follow-up request.

- [ ] **Step 4: Commit**

```bash
git add tests/test_next_run_start_for_zone.py
git commit -F - <<'EOF'
test(scheduler): pin that the earliest schedule wins and none is short-circuited

Both pass on the existing loop, so they are pins rather than a change. Mutating
the loop to return on its first match fails exactly these two, which is what
makes them worth having: an edit that looks like a simplification would otherwise
price the wrong run for any zone in more than one schedule.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 4: the cycle pin

**Files:**
- Test only: `tests/test_next_run_start_for_zone.py`

This is the load-bearing test of the whole change. The resolver must never reach a bucket, because the weighting calls it from inside the calculation that writes one.

- [ ] **Step 1: Write the test**

Append to `tests/test_next_run_start_for_zone.py`:

```python
@pytest.mark.asyncio
async def test_the_resolver_never_prices_a_zone():
    """The cycle pin, and the reason this method exists at all.

    calculate_module calls this while computing the very bucket that
    get_total_irrigation_duration reads. Any path from here to that call is a
    loop, so it is made to raise: the resolver still has to answer.
    """
    manager, coordinator = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)

    def _explode(*args, **kwargs):
        raise AssertionError(
            "the resolver reached a zone duration, which closes the cycle "
            "calculate_module calls it from"
        )

    coordinator.get_total_irrigation_duration = _explode
    manager._estimate_duration = _explode
    manager._duration_bound = _explode
    manager._decision_point = _explode

    assert await manager.async_next_run_start_for_zone(1) == TARGET
```

- [ ] **Step 2: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_next_run_start_for_zone.py -p _local_socket_unblock -q
```

Expected: 12 passed.

- [ ] **Step 3: Prove the pin is sharp by mutation**

Insert `await self._estimate_duration(schedule)` as the first line of `_next_run_start_for_schedule`'s body, after its docstring. Run the file again. Expected: **`test_the_resolver_never_prices_a_zone` fails** with the `AssertionError` above. Remove the line and confirm 12 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_next_run_start_for_zone.py
git commit -F - <<'EOF'
test(scheduler): pin that the run-start resolver never prices a zone

The resolver is called from inside calculate_module, so a path from it to
get_total_irrigation_duration closes a loop around the bucket being computed.
Making all four pricing entry points raise turns that architectural constraint
into a failing test instead of a comment nobody re-checks.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 5: the existing weighting tests get dated fixtures and a run start

**Files:**
- Modify: `tests/test_experimental_features.py:27-54` and its four weighting tests

Behaviour-preserving: today's weighting ignores dates, so dating the entries changes nothing yet. Doing it now keeps Task 6's diff about the change rather than about fixtures.

- [ ] **Step 1: Add the dated-entry helper and wire a run start into the fixture**

In `tests/test_experimental_features.py`, add after the imports:

```python
import datetime

UTC = datetime.timezone.utc
# get_forecast_data starts TOMORROW by contract (forecast_window's docstring), so
# the first entry is the day after the run's own date here.
# Midnight of the first forecast day, so each 24-hour block from the run lines up
# with exactly one dated entry and the four tests here keep testing the weighting's
# ARITHMETIC rather than partial-day overlap. Measured 2026-09-26: a 06:00 start
# makes every block 18/24 of one entry plus 6/24 of the next and breaks THREE of
# the four, not the one this plan first predicted.
RUN_START = datetime.datetime(2026, 9, 27, tzinfo=UTC)


def _days(*mm):
    """Dated daily entries, the shape every client has supplied since #145.

    Seven days minimum on this path: expected_rain reports first_24h_covered
    False when the entries do not span the run's whole 24-hour block, and the
    weighting then abstains -- which reads as the code being broken when it is
    the fixture being short. Measured: two days abstains, three and above cover.
    """
    entries = []
    for index in range(max(7, len(mm))):
        start = datetime.datetime(2026, 9, 27, tzinfo=UTC) + datetime.timedelta(
            days=index
        )
        entries.append(
            {
                const.MAPPING_PRECIPITATION: mm[index] if index < len(mm) else 0.0,
                const.FORECAST_DAY_START: start,
                const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
            }
        )
    return entries
```

In `_calc_coordinator`, add before `return coord`:

```python
    coord.recurring_schedule_manager = SimpleNamespace(
        async_next_run_start_for_zone=AsyncMock(return_value=RUN_START)
    )
```

- [ ] **Step 2: Re-fixture the four weighting tests**

Replace each forecast argument with `_days(...)`:

- `test_no_weighting_leaves_target_zero_and_full_duration`: `[{"precipitation": 4.0}]` --> `_days(4.0)`
- `test_forecast_weighting_reduces_duration_and_sets_target`: `[{const.MAPPING_PRECIPITATION: 4.0}]` --> `_days(4.0)`
- `test_forecast_covering_deficit_skips_run`: `[{const.MAPPING_PRECIPITATION: 12.0}]` --> `_days(12.0)`
- `test_forecast_weighting_sums_lookahead_days`: the three-entry list --> `_days(2.0, 3.0, 9.0)`

Leave every assertion exactly as it is.

- [ ] **Step 3: Run the file to verify nothing changed**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: the same number of passes as before the edit, with no failures. Today's weighting slices by position and ignores the dates, so `_days(4.0)` behaves as `[{...: 4.0}]` did.

- [ ] **Step 4: Commit**

```bash
git add tests/test_experimental_features.py
git commit -F - <<'EOF'
test(weighting): date the forecast fixtures and give the zone a run start

Preparation, behaviour-preserving: today's weighting slices the list by position
and never looks at a date, so this changes no assertion. forecast_window needs
FORECAST_DAY_START/END on every entry it prices and seven days to cover a run's
own 24-hour block, and doing it in its own commit keeps the next diff about the
change rather than about fixtures.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 6: the weighting prices the run's own window

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py:1104-1136`
- Test: `tests/test_forecast_weighting_window.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_forecast_weighting_window.py`:

```python
"""The forecast weighting prices the run's own window (Eifel-Joe#21).

The weighting summed get_forecast_data by position, and that list starts tomorrow
by contract, so it priced calendar days from tomorrow whatever day and hour the
run fell on. Measured on 10bb8077: a zone whose run is the day after tomorrow
watered its full 10 mm deficit the night before 8 mm of rain -- 6 mm over-watered
on that one forecast.

Seven dated days in every fixture: see _days in test_experimental_features.
"""

import datetime

import pytest

from custom_components.irrigation_plus import const

from .test_experimental_features import _calc_coordinator, _days, _weather, _zone

UTC = datetime.timezone.utc


def _run_at(coord, when):
    coord.recurring_schedule_manager.async_next_run_start_for_zone.return_value = when


async def test_rain_inside_the_runs_window_is_weighted():
    """8 mm falls on the run's own day, which is position 1 of the list."""
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    # Run at 06:00 on the second forecast day, so its first 24 h is 18/24 of that
    # day plus 6/24 of the next: 8 mm * 18/24 = 6 mm.
    _run_at(coord, datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC))

    data = await coord.calculate_module(_zone(), _weather(10.0), _days(0.0, 8.0))

    assert data[const.ZONE_BUCKET] == pytest.approx(-10.0)
    # 10 mm deficit less 6 mm expected rain, at 60 mm/h -> 4 mm -> 240 s.
    assert data[const.ZONE_DURATION] == 240
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(-6.0)


async def test_rain_outside_the_runs_window_is_not_weighted():
    """The mirror: rain on the list's first day, run two days later."""
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    _run_at(coord, datetime.datetime(2026, 9, 29, 6, 0, tzinfo=UTC))

    data = await coord.calculate_module(_zone(), _weather(10.0), _days(8.0))

    # Position 0 carried the rain, and master would have weighted on it.
    assert data[const.ZONE_DURATION] == 600
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(0.0)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_forecast_weighting_window.py -p _local_socket_unblock -q
```

Expected: 2 failed. The first reports `600 == 240` (the rain in the run's window was not seen); the second reports `120 == 600` — 8 mm against a 10 mm deficit leaves 2 mm, which is 120 s at 60 mm/h.

- [ ] **Step 3: Add the import**

At the top of `custom_components/irrigation_plus/calculation.py`, add `import functools` after `import logging` (line 10), and add to the local imports beside `from .helpers import ...`:

```python
from .forecast_window import expected_rain
```

- [ ] **Step 4: Replace the positional slice**

In `calculate_module`, replace this block:

```python
            if fd:
                config = await self.store.async_get_config()
                days = max(
                    1,
                    config.get(
                        const.CONF_PRECIPITATION_FORECAST_DAYS,
                        const.CONF_DEFAULT_PRECIPITATION_FORECAST_DAYS,
                    ),
                )
                forecast_precip = sum(
                    day_data.get(const.MAPPING_PRECIPITATION, 0.0)
                    for day_data in fd[:days]
                )
                if forecast_precip > 0:
```

with:

```python
            if fd:
                config = await self.store.async_get_config()
                days = max(
                    1,
                    config.get(
                        const.CONF_PRECIPITATION_FORECAST_DAYS,
                        const.CONF_DEFAULT_PRECIPITATION_FORECAST_DAYS,
                    ),
                )
                # Wurzel: the window used to be fd[:days], a positional slice of a
                #   list that starts TOMORROW by contract -- so it priced calendar
                #   days from tomorrow whatever day the run fell on. The skip
                #   guard, the other half of this same setting, had the defect and
                #   lost it in #146; forecast_window is the module that fixed it
                #   and is reused here rather than copied, so the two halves of one
                #   dropdown cannot diverge again.
                # siehe tests/test_forecast_weighting_window.py
                run_start = await self.recurring_schedule_manager.async_next_run_start_for_zone(
                    zone.get(const.ZONE_ID)
                )
                # dt_util, deliberately not this method's own `now`: that parameter
                # defaults to a bare datetime.now(), which is naive process-local
                # and is the seam Eifel-Joe#22 is about to move. expected_rain
                # compares aware instants either way, so taking the moment from
                # dt_util keeps this independent of how that lands.
                rain = (
                    expected_rain(
                        run_start=run_start,
                        evaluated_at=dt_util.utcnow(),
                        days=days,
                        hourly=await self._weighting_hourly(run_start, days),
                        daily=fd,
                    )
                    if run_start is not None
                    else None
                )
                forecast_precip = rain.mm if rain is not None else 0.0
                if rain is not None and forecast_precip > 0:
```

- [ ] **Step 5: Add the hourly accessor**

Insert immediately above `async def calculate_module` in the same class:

```python
    async def _weighting_hourly(self, run_start, days):
        """The hourly precipitation series covering the weighting's window.

        Same plumbing as the skip guard's: the far end is the RUN's start plus the
        whole look-ahead, not the evaluation's, so a client holding two products of
        different reach can pick the one that gets there. Only Met Office acts on
        it; the others hand back the one document they have. None where the client
        has no hourly accessor at all, which expected_rain takes.
        """
        client = self._WeatherServiceClient
        if client is None or not hasattr(client, "get_hourly_precipitation_forecast"):
            return None
        return await self.hass.async_add_executor_job(
            functools.partial(
                client.get_hourly_precipitation_forecast,
                covering_until=run_start + timedelta(hours=24 * days),
            )
        )
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_forecast_weighting_window.py tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: **24 passed**, both files. With `RUN_START` at midnight the four existing tests
keep their numbers exactly, because each 24-hour block then covers one dated entry whole.

An earlier draft of this plan put `RUN_START` at 06:00 and predicted that one existing test
would need fixing in Task 7. Measured: three of the four broke, and the fix belongs in the
fixture rather than in each test. Task 7 therefore has no step for it.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py tests/test_forecast_weighting_window.py
git commit -F - <<'EOF'
fix(weighting): price the forecast over the run's window, not the list's head

The weighting summed get_forecast_data by position, and that list starts tomorrow
by contract, so it priced calendar days from tomorrow whatever day and hour the
run fell on. Measured before the change: a zone whose run was the day after
tomorrow watered its full 10 mm deficit the night before 8 mm of rain, because
position 0 was the dry day -- 6 mm over-watered on that one forecast.

forecast_window.expected_rain is reused rather than copied. It is the module that
fixed the same defect for the precipitation skip guard, the other half of this
same setting, and a second windowing rule is how the two diverged in the first
place.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 7: the weighting abstains rather than guessing

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (the block from Task 6)
- Modify: `tests/test_experimental_features.py` (`test_forecast_weighting_sums_lookahead_days`)
- Test: `tests/test_forecast_weighting_window.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_forecast_weighting_window.py`:

```python
async def test_a_zone_with_no_resolvable_run_is_not_weighted(caplog):
    """No enabled schedule names it, so there is no window to price."""
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    _run_at(coord, None)

    data = await coord.calculate_module(_zone(), _weather(10.0), _days(8.0))

    assert data[const.ZONE_DURATION] == 600
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(0.0)
    assert any(
        "no scheduled run" in r.getMessage() and "zone 1" in r.getMessage()
        for r in caplog.records
    ), caplog.text


async def test_a_window_the_forecast_does_not_cover_is_not_weighted(caplog):
    """Mirrors the skip guard, which refuses to decide on an uncovered first 24 h.

    Two dated days only, so the run's block is 18/24 covered. Abstaining means
    watering the full amount, which is the safe direction for a feature whose job
    is to water less.
    """
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    _run_at(coord, datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC))
    short = _days(0.0, 8.0)[:2]

    data = await coord.calculate_module(_zone(), _weather(10.0), short)

    assert data[const.ZONE_DURATION] == 600
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(0.0)
    assert any(
        "does not cover" in r.getMessage() for r in caplog.records
    ), caplog.text
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_forecast_weighting_window.py -p _local_socket_unblock -q
```

Expected: 2 failed. `test_a_zone_with_no_resolvable_run_is_not_weighted` passes on the duration but finds no log line; `test_a_window_the_forecast_does_not_cover_is_not_weighted` weights on the partial coverage and reports a duration of 240.

- [ ] **Step 3: Add the two abstentions**

Replace the `rain = (...)` / `forecast_precip = ...` / `if rain is not None and forecast_precip > 0:` block from Task 6 with:

```python
                if run_start is None:
                    # Abstaining waters the full amount, which is the safe
                    # direction for a feature whose whole job is to water less.
                    _LOGGER.debug(
                        "[calculate-module]: no scheduled run resolves for zone "
                        "%s, so the forecast weighting has no window to price",
                        zone.get(const.ZONE_ID),
                    )
                    rain = None
                else:
                    rain = expected_rain(
                        run_start=run_start,
                        evaluated_at=dt_util.utcnow(),
                        days=days,
                        hourly=await self._weighting_hourly(run_start, days),
                        daily=fd,
                    )
                    if not rain.first_24h_covered:
                        # The same refusal the skip guard makes: a forecast that
                        # does not reach the run's first 24 hours says nothing
                        # about them, and a partial sum reads as "little rain".
                        _LOGGER.debug(
                            "[calculate-module]: the forecast does not cover the "
                            "first 24 hours from zone %s's run, so it is not "
                            "weighted",
                            zone.get(const.ZONE_ID),
                        )
                        rain = None
                forecast_precip = rain.mm if rain is not None else 0.0
                if rain is not None and forecast_precip > 0:
```

- [ ] **Step 4: Fix the look-ahead test from Task 6**

`test_forecast_weighting_sums_lookahead_days` in `tests/test_experimental_features.py` asserted the positional two-day sum. Replace its body with the run-window equivalent:

```python
async def test_forecast_weighting_sums_lookahead_days():
    """Two 24-hour blocks from the run, not two entries from the list's head."""
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=2)
    # Run at midnight on the first forecast day, so the two blocks line up with
    # the first two entries exactly and the arithmetic stays readable.
    coord.recurring_schedule_manager.async_next_run_start_for_zone.return_value = (
        datetime.datetime(2026, 9, 27, tzinfo=UTC)
    )
    data = await coord.calculate_module(
        _zone(), _weather(10.0), _days(2.0, 3.0, 9.0)
    )
    # 5 mm over the two blocks -> effective deficit 5 mm. The 9 mm sits in the
    # third block, outside the window.
    assert data[const.ZONE_DURATION] == 300
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(-5.0)
```

- [ ] **Step 5: Run both files to verify they pass**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_forecast_weighting_window.py tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: all pass, 4 in `test_forecast_weighting_window.py`.

- [ ] **Step 6: Prove the abstentions by mutation**

Two mutations, one at a time, reverting between:

1. Delete the `if not rain.first_24h_covered:` branch. Expected: `test_a_window_the_forecast_does_not_cover_is_not_weighted` fails.
2. Change `if run_start is None:` to `if False:`. Expected: `test_a_zone_with_no_resolvable_run_is_not_weighted` fails — `expected_rain` raises on a `None` run start, so the failure is a `TypeError`, which is itself the point: without the guard the calculation would raise rather than abstain.

Confirm all pass again after reverting both.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py tests/test_forecast_weighting_window.py tests/test_experimental_features.py
git commit -F - <<'EOF'
fix(weighting): abstain instead of guessing when there is no window to price

Two cases, both silent before. A zone no enabled schedule names has no run to
measure from, and a forecast that does not reach the run's first 24 hours says
nothing about them -- a partial sum there reads as "little rain" and waters MORE
than it should. Both now leave the weighting out and say so at debug level.

Abstaining waters the full amount, which is the safe direction for a feature
whose whole job is to water less. It is also what the precipitation skip guard
already does with the same coverage flag, which is the behaviour these two halves
of one setting should share.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 8: retire the throwaway repro

**Files:**
- Delete: `tests/test_zz_repro_issue21.py`

- [ ] **Step 1: Confirm every assertion it made is now covered**

| Repro assertion | Now covered by |
| --- | --- |
| master waters the full 10 mm on a dry position 0 | `test_forecast_weighting_window.py::test_rain_inside_the_runs_window_is_weighted` (inverted: 240 s, not 600) |
| `expected_rain` from the run sees 6.0 mm, fully covered | the same test's `-6.0` target bucket |
| the 6 mm gap | the same test — the gap is the difference between the two durations it pins |

- [ ] **Step 2: Delete and commit**

```bash
git rm tests/test_zz_repro_issue21.py
git commit -F - <<'EOF'
test(weighting): retire the throwaway repro

It asserted the defect and is superseded by the real tests, which assert the fix
over the same forecast. Kept until now as the cross-check that the change did
what it claimed.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 9: full verification

- [ ] **Step 1: Measure the baseline on THIS base commit**

The stored `issue2-work/baseline-names.txt` was taken on `965a4f9d` and does **not** apply: `10bb8077` carries 349 collection errors on this Windows environment where `965a4f9d` carried 320, and the difference is `JustChr#167`, not us.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree add --detach /d/Entwicklung/HASI/issue21-work/base 10bb8077
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue21-work/base/
cd /d/Entwicklung/HASI/issue21-work/base
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no > /d/Entwicklung/HASI/issue21-work/base-full.txt 2>&1
```

Expected: `7 failed, 3235 passed, 9 skipped, 349 errors`.

- [ ] **Step 2: Run the full suite on the branch**

```bash
cd /d/Entwicklung/HASI/issue21-work/wt
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no > /d/Entwicklung/HASI/issue21-work/full.txt 2>&1
tail -2 /d/Entwicklung/HASI/issue21-work/full.txt
```

- [ ] **Step 3: Prove the failure set is unchanged**

```bash
cd /d/Entwicklung/HASI/issue21-work
for f in base-full full; do
  grep -E "^(FAILED|ERROR) " $f.txt | sed 's/ - \.\.\.$//' | sort > $f-names.txt
done
diff base-full-names.txt full-names.txt && echo "IDENTICAL"
```

The `sed` matters: pytest truncates its one-line summaries differently between runs, and without stripping that suffix the diff reports a difference that is not one.

Expected: `IDENTICAL`, and the `passed` delta equals the number of tests added — count them with
`pytest tests/test_next_run_start_for_zone.py tests/test_forecast_weighting_window.py --collect-only -q`
and subtract the one repro file's 3 that Task 8 deleted. Both numbers must add up, not just one.

- [ ] **Step 4: Remove the baseline worktree**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree remove /d/Entwicklung/HASI/issue21-work/base
```

- [ ] **Step 5: Confirm the guard is untouched**

```bash
cd /d/Entwicklung/HASI/issue21-work/wt
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py tests/test_forecast_window.py -p _local_socket_unblock -q
```

Expected: all pass, and `git diff 10bb8077 --stat -- custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/forecast_window.py` is empty. The guard is the oracle for the module being reused; if either file changed, the change went wider than the plan.

- [ ] **Step 6: Lint**

```bash
uvx black custom_components/irrigation_plus/ tests/
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: both clean. Commit any reformatting on its own.

- [ ] **Step 7: Sister-path check**

`calculate_module` is the only reader of `forecast_weighting_enabled` in the package, verified on this base, so the weighting has no sibling branch to mirror. The sibling to check is the other half of the same setting: the precipitation skip guard, covered by Step 5. Record that both were checked.

---

## Notes for whoever writes the PR body

- **What this does not close:** the weighting still never reaches the live estimate, so a zone under `live_estimate_enabled` is sized without it. That is JustChr's explicit split (`JustChr#159`) and needs its own decision.
- **The accepted inexactness:** for a Finish-anchored schedule with no armed run, the window is anchored at the run's end rather than its start — at most one run length out against a 24-hour block. Name it; a reviewer will look for it.
- **Lead with the measurement**, not the mechanism: full 10 mm watered the night before 8 mm of rain, 6 mm over-watered, and the direction is the harmful one.
- **Say that `forecast_window` was reused, not copied**, and why: it is the module that fixed the identical defect for the guard in `JustChr#146`, and a second windowing rule is how the two halves diverged.
