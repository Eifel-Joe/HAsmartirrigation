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

---

# Phase R — the maintainer's review (Tasks 10–17)

> Spec: §9 of `docs/superpowers/specs/2026-09-26-forecast-weighting-from-run-start-design.md`.
> Tasks 1–9 above are **done and committed**; this phase reworks them in place.

**Goal:** close `JustChr#172`'s two findings and its question, on a branch rebased
onto `c5330c7f`, with no commit anywhere in the history naming our own tracker.

**Architecture:** the caller that knows the run start passes it — a keyword-only
`run_start` threaded from `_execute_schedule` down to `calculate_module`; the
resolver is consulted only when nobody passed one; and `evaluated_at` stands in
when the resolver has no answer. Test dates stop being literals and become derived
from one pinned evaluation moment.

## Before you start on this phase

**The base moved.** The eight existing commits sit on `10bb8077`, 8 behind.
Everything below assumes `c5330c7f`.

**The baseline for `c5330c7f` already exists** — do not re-measure it:
`D:\Entwicklung\HASI\pr174-work\baseline-names.txt`, **374 names**
(7 failed / 3322 passed / 9 skipped / 367 errors). §6's numbers (349 errors, 356
names) belong to `10bb8077` and are void.

**Only the full run with a name diff decides.** On `JustChr#174` five test files
were green while `tests/test_valve_verification.py` was red — a file no partial run
had touched.

**The probe that proves Finding 2 is already written** and is the seed of Task 13:
`D:\Entwicklung\HASI\issue21-work\probe_before_run_anchor.py`. Run it before
changing anything; it prints `+1 day` on two of three rows.

**Two measured facts that will bite if you skip them:**

1. **`_perform_scheduled_irrigation` has no `now`.** Its signature is
   `(self, zones, schedule_name, *, order=None, deadline=None, pre_committed=False)`.
   `_execute_schedule` is the one that carries `now`, as a required positional, and
   it calls down without it (`scheduler.py:2302`). The anchor therefore has to be
   threaded through one more method than it looks.
2. **`_entries_behind` drops a daily entry that starts exactly at the hourly
   series' end** — its own docstring: *"An entry that overlaps the series, or
   starts exactly at its end, is left out whole."* Any fixture that pairs an hourly
   series with dated dailies has to leave no seam, or `first_24h_covered` comes
   back `False` and the weighting abstains, which looks exactly like the code being
   wrong.

**Reference discipline: three checks, all before any push** (Task 17). The one
allowed match anywhere is the `Author:` line.

---

## Task 10: rebase onto `c5330c7f`, keep the old head recoverable

**Files:** none — history only.

- [x] **Step 1: keep the granular history under a name**

```bash
cd /d/Entwicklung/HASI/issue21-work/pr
git branch issue21-granular
git rev-parse issue21-granular
```

Expected: `1523acea…`.

- [x] **Step 2: rebase**

```bash
git fetch upstream
git rebase --onto c5330c7f 10bb8077
```

Expected: 8 commits replayed. A conflict in `calculation.py`'s import block takes
both imports (`functools`, `from .forecast_window import expected_rain`); the
`I001` sort lands in Task 16.

- [x] **Step 3: confirm the base**

```bash
git rev-list --count HEAD..upstream/master
```

Expected: `0`.

- [x] **Step 4: full suite against the baseline**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ \
  -p _local_socket_unblock -q 2>&1 | tail -5
```

Expected: **10 failed** — the baseline's 7 plus §9.1's three clock failures, which
Task 11 fixes. Anything else is a rebase casualty; understand it before going on.

- [x] **Step 5: nothing to commit.** A rebase is not a commit.

---

## Task 11: pin the evaluation moment, derive every date from it

**Files:**
- Modify: `tests/test_experimental_features.py` (imports, header block, `_days`)
- Modify: `tests/test_forecast_weighting_window.py` (imports, three run starts)

- [x] **Step 1: prove RED against today's real clock**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_experimental_features.py -p _local_socket_unblock -q 2>&1 | tail -8
```

Expected on 2026-09-27: `3 failed` — `assert 490 == 360`, `assert 269 == 0`,
`assert 365 == 300`. Every actual **above** its expectation: a partially covered
window sums part of the rain, so less is subtracted and the zone waters more.

- [x] **Step 2: extend the import line**

```python
from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    calculation,
    const,
)
```

- [x] **Step 3: replace the `UTC` / `RUN_START` / `_days` block**

```python
UTC = datetime.timezone.utc
# The pinned evaluation moment. RUN_START and every forecast entry below are
# DERIVED from it, so no date in this module can rot.
# Wurzel: RUN_START was the literal 2026-09-27 00:00 while evaluated_at came from
#   the real clock. window_intervals cuts a block back to max(block_start,
#   evaluated_at) and drops one wholly past, so on 2026-09-27 the first block was
#   half gone: three tests summed a PARTIAL rain and asserted 490/269/365 against
#   360/0/300. Worse, past 2026-09-28 the two abstention tests would have gone
#   GREEN for the wrong reason -- window in the past, weighting abstaining,
#   assertions holding without exercising anything.
# siehe _pin_the_evaluation_moment below
NOW = datetime.datetime(2026, 9, 26, 21, 0, tzinfo=UTC)
# Midnight of the first forecast day, three hours AFTER the evaluation so nothing
# is cut: each 24-hour block from the run then lines up with exactly one dated
# entry, which keeps the four tests here testing the weighting's ARITHMETIC. A
# 06:00 start makes every block 18/24 of one entry plus 6/24 of the next and
# breaks three of the four (measured 2026-09-26); that overlap is real behaviour
# and is tested in test_forecast_weighting_window.py.
RUN_START = NOW + datetime.timedelta(hours=3)


@pytest.fixture(autouse=True)
def _pin_the_evaluation_moment(monkeypatch):
    """Pin the moment the weighting evaluates at, for every test in this module.

    Only ``dt_util.utcnow`` is redirected -- not ``datetime.now``, not
    ``time.time`` -- and that is the single clock read on the weighting's path
    (``evaluated_at`` in calculation.py). The attribute lives on the shared
    ``homeassistant.util.dt`` module, so the patch is process-wide while one test
    runs; acceptable here because these coordinators are ``__new__``-built stubs
    with a ``Mock`` hass rather than a running instance. freezegun was rejected for
    the opposite reason: it replaces the whole process clock.
    NOT-TO-DO: do not "fix" a date-dependent test by moving its literals further
      into the future. That is the defect, not the cure -- the assertions then hold
      because the window has moved into the past and the weighting abstained.
    """
    monkeypatch.setattr(calculation.dt_util, "utcnow", lambda: NOW)


def _days(*mm):
    """Dated daily entries from RUN_START on, the shape every client has supplied
    since #145.

    Seven days minimum on this path: expected_rain reports first_24h_covered False
    when the entries do not span the run's whole 24-hour block, and the weighting
    then abstains -- which reads as the code being broken when it is the fixture
    being short. Measured: two days abstains, three and above cover.
    """
    entries = []
    for index in range(max(7, len(mm))):
        start = RUN_START + datetime.timedelta(days=index)
        entries.append(
            {
                const.MAPPING_PRECIPITATION: mm[index] if index < len(mm) else 0.0,
                const.FORECAST_DAY_START: start,
                const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
            }
        )
    return entries
```

- [x] **Step 4: derive the run starts in `tests/test_forecast_weighting_window.py`**

```python
from .test_experimental_features import (
    NOW,
    RUN_START,
    _calc_coordinator,
    _days,
    _pin_the_evaluation_moment,  # noqa: F401  autouse; applies by being imported
    _weather,
    _zone,
)
```

Three substitutions, all `RUN_START`-relative:

| test | was | becomes |
| --- | --- | --- |
| `test_rain_inside_the_runs_window_is_weighted` | `2026-09-28 06:00` | `RUN_START + datetime.timedelta(days=1, hours=6)` |
| `test_rain_outside_the_runs_window_is_not_weighted` | `2026-09-29 06:00` | `RUN_START + datetime.timedelta(days=2, hours=6)` |
| `test_a_window_the_forecast_does_not_cover_is_not_weighted` | `2026-09-28 06:00` | `RUN_START + datetime.timedelta(days=1, hours=6)` |

The third keeps its `_days(0.0, 8.0)[:2]` and therefore its 18/24 coverage.

- [x] **Step 5: GREEN**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_experimental_features.py tests/test_forecast_weighting_window.py \
  -p _local_socket_unblock -q 2>&1 | tail -5
```

Expected: 26 passed (22 + 4), 0 failed.

- [x] **Step 6: the discriminating check — the pin has to be load-bearing**

The maintainer's second ask: *"then check that each test still fails for its own
reason when the clock moves."*

Moving `NOW` alone proves nothing now — `RUN_START` and the forecast derive from
it, so the whole picture slides and every test stays green. That is the point of
deriving them, and it means the check has to break the *relationship* instead:
push the evaluation past the run while the run stays put. Add one temporary line
and point the fixture at it:

```python
_EVALUATE_AT = NOW + datetime.timedelta(days=3)   # TEMPORARY, Step 6 only
```

```python
    monkeypatch.setattr(calculation.dt_util, "utcnow", lambda: _EVALUATE_AT)
```

then run:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_experimental_features.py tests/test_forecast_weighting_window.py \
  -p _local_socket_unblock -q 2>&1 | tail -14
```

Expected: the four arithmetic tests in `test_experimental_features.py` and
`test_rain_inside_the_runs_window_is_weighted` **fail**; the two abstention tests
pass (they assert the full duration, which is what abstaining produces — that is
the silent-green class, and it is why the arithmetic tests are the ones that have
to move). Write down which failed. Then revert:

```bash
git checkout -- tests/test_experimental_features.py
```

and re-apply Steps 2–4, or keep a copy before Step 6. Re-run Step 5 and confirm 26
passed before committing.

- [x] **Step 7: commit**

```bash
git add tests/test_experimental_features.py tests/test_forecast_weighting_window.py
git commit -F - <<'EOF'
test(weighting): pin the evaluation moment and derive every date from it

The run start was a literal while evaluated_at came from the real clock, so three
of these went red the next day, and past the run's date the abstention tests would
have gone green for the wrong reason.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 12: thread a caller-supplied run start down to the weighting

**Files:**
- Modify: `custom_components/irrigation_plus/auto_calc.py:46-66`
- Modify: `custom_components/irrigation_plus/calculation.py:421`, `:453`, `:476`, `:523`, `:877`
- Modify: `custom_components/irrigation_plus/__init__.py:2028`, `:2100`
- Test: `tests/test_forecast_weighting_window.py`

- [x] **Step 1: write the failing test**

Append to `tests/test_forecast_weighting_window.py`:

```python
async def test_a_caller_supplied_run_start_wins_over_the_resolver():
    """The run start the caller KNOWS beats the one the schedules imply.

    The resolver is made to raise rather than mocked quiet: inside a dispatch it
    answers for the FOLLOWING run, so a silent fallback would hide the very defect
    this parameter exists for.
    """
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    coord.recurring_schedule_manager.async_next_run_start_for_zone.side_effect = (
        AssertionError("the resolver must not be consulted when a start is given")
    )

    data = await coord.calculate_module(
        _zone(),
        _weather(10.0),
        _days(0.0, 8.0),
        run_start=RUN_START + datetime.timedelta(days=1, hours=6),
    )

    # Same window as test_rain_inside_the_runs_window_is_weighted: 8 mm * 18/24.
    assert data[const.ZONE_DURATION] == 240
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(-6.0)
```

- [x] **Step 2: RED**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_forecast_weighting_window.py::test_a_caller_supplied_run_start_wins_over_the_resolver \
  -p _local_socket_unblock -q 2>&1 | tail -6
```

Expected: FAIL — `calculate_module() got an unexpected keyword argument 'run_start'`.

- [x] **Step 3: `calculate_module` takes it and prefers it**

`calculation.py:877`:

```python
    async def calculate_module(
        self, zone, weatherdata, forecastdata, *, now=None, run_start=None
    ):
```

In the weighting block, wrap the existing resolver call:

```python
                # A caller inside a dispatch passes the run start, because the
                # resolver cannot know it there: the fired-occurrence guard has
                # already moved past this occurrence and _next_governing_time
                # resolves strictly after now, so both hand back the FOLLOWING run.
                # Measured +1 day on a finish callback and on a plain start-time
                # schedule alike.
                # siehe tests/test_before_run_anchor.py
                if run_start is None:
                    run_start = await (
                        self.recurring_schedule_manager.async_next_run_start_for_zone(
                            zone.get(const.ZONE_ID)
                        )
                    )
```

- [x] **Step 4: thread it through the three methods above**

`calculation.py:476` — `async_calculate_zone`:

```python
    async def async_calculate_zone(
        self, zone_id, forecastdata=None, *, now=None, prune=True, run_start=None
    ):
```

and its call at `:523`:

```python
        calc_data = await self.calculate_module(
            zone, weatherdata, forecastdata, now=now, run_start=run_start
        )
```

`calculation.py:421` — `_async_calculate_all`:

```python
    async def _async_calculate_all(self, *args, run_start=None):
```

and its call at `:453`:

```python
                await self.async_calculate_zone(
                    zone.get(const.ZONE_ID),
                    forecastdata,
                    now=now,
                    prune=False,
                    run_start=run_start,
                )
```

`__init__.py:2028` — `async_update_zone_config`:

```python
    async def async_update_zone_config(
        self, zone_id: int | None = None, data: dict | None = None, *, run_start=None
    ):
```

with this added under its docstring's `Args:`:

```
            run_start: when the run this calculation precedes begins, used by the
                ATTR_CALCULATE branch only. Keyword-only and BESIDE ``data`` on
                purpose: ``data``'s keys are schema-validated as websocket fields
                (websockets.py:295-296), so a run start carried inside the dict
                would become part of an external API.
```

and its call at `:2100`:

```python
            await self.async_calculate_zone(zone_id, forecastdata, run_start=run_start)
```

`auto_calc.py:46` — the commit:

```python
    async def async_commit_pre_run_calculation(
        self, zones=None, *, run_start=None
    ) -> None:
```

adding this paragraph to its docstring:

```
        ``run_start`` is when the run this commit precedes actually begins, and is
        passed only by a caller that knows -- a dispatch, where the run starts now.
        Left None the weighting resolves the start from the schedules itself, which
        is right for a commit made ahead of the run at a decision point and wrong
        inside a dispatch.
```

and both body calls:

```python
        if selection is None:
            await self._async_calculate_all(run_start=run_start)
        else:
            for zone_id in selection:
                await self.async_update_zone_config(
                    zone_id, {const.ATTR_CALCULATE: True}, run_start=run_start
                )
```

- [x] **Step 5: GREEN, and the suites that mock this commit**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_forecast_weighting_window.py tests/test_experimental_features.py \
  tests/test_auto_calc_mode.py -p _local_socket_unblock -q 2>&1 | tail -5
```

Expected: all pass. Nothing calls the commit with a `run_start` yet, so
`test_auto_calc_mode.py`'s `assert_awaited_once_with("all")` still holds. It stops
holding in Task 13 — that is expected there, not here.

- [x] **Step 6: commit**

```bash
git add custom_components/irrigation_plus/auto_calc.py \
        custom_components/irrigation_plus/calculation.py \
        custom_components/irrigation_plus/__init__.py \
        tests/test_forecast_weighting_window.py
git commit -F - <<'EOF'
feat(weighting): let the caller that knows the run start supply it

Keyword-only beside the zone-config dict rather than inside it: that dict's keys
are schema-validated as websocket fields.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

- [x] **Step 7: mark this point — the reshape in Task 17 needs it**

Nothing up to here has touched `scheduler.py` beyond the resolver, and Tasks 13 and
14 are about to. `scheduler.py` therefore ends up carrying two unrelated changes,
and the reshape has to separate them without `git add -p` (interactive staging is
not available in this environment). A branch here is the deterministic way to get
the resolver-only version of that file back later:

```bash
git branch issue21-resolver-only
git rev-parse issue21-resolver-only
```

---

## Task 13: the dispatch names its own moment, proven through the real advance

**Files:**
- Modify: `custom_components/irrigation_plus/scheduler.py:2302`, `:2311`, `:2332`
- Modify: `tests/test_auto_calc_mode.py:345-354` (two assertions)
- Create: `tests/test_before_run_anchor.py`

- [x] **Step 1: create the test file**

```python
"""The pre-run calculation prices the run it is part of, not the one after it.

Under autocalcmode "before each irrigation run" the calculation that runs the
forecast weighting is reached from inside the run's own dispatch. Two independent
mechanisms then make the run-start resolver answer for the FOLLOWING run:

  (A) the fire callback writes _finish_last_target and pops _armed_runs before it
      calls _execute_schedule, so _advance_past_fired_occurrence treats this run's
      own target as already fired;
  (B) _next_governing_time resolves strictly after its reference, which defaults
      to now -- and at dispatch now IS the occurrence.

Measured before the fix: +1 day for both, on a daily schedule. These tests
therefore stand in ONLY for the clock/sun layer (_resolve_bound) and run
_next_governing_time and _advance_past_fired_occurrence for real. The resolver
suite (test_next_run_start_for_zone.py) stubs both and cannot see any of this,
which is why it stayed green.
"""

import datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus import scheduler as scheduler_module

from .test_scheduler import _make_manager

UTC = datetime.timezone.utc
SID = "s1"
# The run being dispatched, on a daily 06:00 UTC bound.
TODAY_RUN = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC)
TOMORROW_RUN = TODAY_RUN + datetime.timedelta(days=1)


def _schedule():
    return {
        const.SCHEDULE_CONF_ID: SID,
        const.SCHEDULE_CONF_ENABLED: True,
        const.SCHEDULE_CONF_ZONES: "all",
        const.SCHEDULE_CONF_RECURRENCE: const.SCHEDULE_RECURRENCE_DAILY,
        const.SCHEDULE_CONF_START_MODE: const.SCHEDULE_BOUND_MODE_TIME,
        const.SCHEDULE_CONF_FINISH_MODE: const.SCHEDULE_BOUND_MODE_NONE,
    }


def _daily_0600_bound(manager):
    """The clock/sun layer only. Everything above it stays real."""

    async def _resolve(schedule, end, reference_utc, *, direction):
        candidate = reference_utc.replace(hour=6, minute=0, second=0, microsecond=0)
        while candidate <= reference_utc:
            candidate += datetime.timedelta(days=1)
        return candidate

    manager._resolve_bound = _resolve


@pytest.fixture
def at_dispatch(monkeypatch):
    """Freeze the scheduler's clock at the dispatch moment."""
    monkeypatch.setattr(scheduler_module.dt_util, "utcnow", lambda: TODAY_RUN)


@pytest.mark.asyncio
async def test_the_resolver_answers_for_the_next_run_at_dispatch(at_dispatch):
    """Mechanism (A): not what we want, and the reason the anchor is passed in.

    Pinned so that anyone removing the explicit run start can read what they are
    falling back to.
    """
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _daily_0600_bound(manager)
    # Verbatim what the finish callback does before _execute_schedule
    # (scheduler.py:1656-1657).
    manager._finish_last_target[SID] = TODAY_RUN.isoformat()
    manager._armed_runs.pop(SID, None)

    assert await manager.async_next_run_start_for_zone(1) == TOMORROW_RUN


@pytest.mark.asyncio
async def test_a_plain_start_time_schedule_needs_no_fired_marker(at_dispatch):
    """Mechanism (B) alone: nothing recorded a fired occurrence here.

    This is why "return an occurrence fired within SAME_OCCURRENCE of now" does
    not fix it -- there is no fired occurrence to return, and the answer is still
    a day late.
    """
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _daily_0600_bound(manager)
    assert not manager._finish_last_target

    assert await manager.async_next_run_start_for_zone(1) == TOMORROW_RUN
```

- [x] **Step 2: run those two, expect PASS**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_before_run_anchor.py -p _local_socket_unblock -q 2>&1 | tail -6
```

Expected: `2 passed`. They pin today's behaviour of the resolver, which the fix
does not change — it stops *relying* on it.

- [x] **Step 3: write the failing test for the dispatch, reusing the existing precedent**

`tests/test_auto_calc_mode.py` already has a manager wired for exactly this
(`TestTheScheduleActuallyCommitsBeforeItRuns._manager`, which mocks
`async_commit_pre_run_calculation`, `_check_skip_conditions`,
`_last_skip_evaluation`, `_record_skipped_run`, `_irrigate_linked_entities`,
`_dispatch_distributor_cycles` and `_reset_days_since_irrigation`). Add a third
test to that class rather than rebuilding the wiring:

```python
    async def test_the_dispatch_names_its_own_moment_as_the_run_start(self, hass):
        """The window the weighting prices is THIS run's, not the next one's.

        Left unnamed, the resolver answers for the following occurrence -- measured
        +1 day for a finish callback and for a plain start-time schedule.
        siehe tests/test_before_run_anchor.py
        """
        mgr, _ = self._manager(hass)
        fired = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=datetime.timezone.utc)

        await mgr._perform_scheduled_irrigation("all", "Morning", run_start=fired)

        mgr.coordinator.async_commit_pre_run_calculation.assert_awaited_once_with(
            "all", run_start=fired
        )
```

Add `import datetime` to that file if it is not already imported.

- [x] **Step 4: RED**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  "tests/test_auto_calc_mode.py::TestTheScheduleActuallyCommitsBeforeItRuns" \
  -p _local_socket_unblock -q 2>&1 | tail -8
```

Expected: the new test FAILS — `_perform_scheduled_irrigation() got an unexpected
keyword argument 'run_start'`. The other two still pass.

- [x] **Step 5: thread the anchor through the two scheduler methods**

`scheduler.py:2311` — signature:

```python
    async def _perform_scheduled_irrigation(
        self,
        zones: str | list[str],
        schedule_name: str,
        *,
        order=None,
        deadline=None,
        pre_committed=False,
        run_start=None,
    ) -> None:
```

and the commit at `:2332`:

```python
            if not pre_committed:
                # The run starts at the moment this dispatch fired. Without it the
                # weighting asks the resolver, which at this moment answers for the
                # NEXT occurrence: the fired-occurrence guard has moved past this
                # one and the governing bound resolves strictly after now.
                # siehe tests/test_before_run_anchor.py
                await self.coordinator.async_commit_pre_run_calculation(
                    zones, run_start=run_start
                )
```

`scheduler.py:2302` — the one production caller, inside `_execute_schedule`, which
carries `now` as a required positional:

```python
            self._perform_scheduled_irrigation(
                zones,
                schedule_name,
                order=order,
                deadline=deadline,
                pre_committed=pre_committed,
                run_start=now,
            ),
```

**NOT-TO-DO:** do not make `run_start` required here to force the issue. There is
one production caller and twelve test call sites across five files; a required
parameter would churn all twelve for nothing. `_execute_schedule`'s `now` is
already mandatory, so the production path cannot forget it, and the default is
reached only from tests.

- [x] **Step 6: update the two existing assertions to the call that now happens**

`tests/test_auto_calc_mode.py:346` and `:354` assert the commit's arguments, and
the commit genuinely takes one more now:

```python
        mgr.coordinator.async_commit_pre_run_calculation.assert_awaited_once_with(
            "all", run_start=None
        )
```

```python
        mgr.coordinator.async_commit_pre_run_calculation.assert_awaited_once_with(
            [1, 2], run_start=None
        )
```

`run_start=None` is correct in those two: they call
`_perform_scheduled_irrigation` directly without a dispatch, which is what the
default is for.

- [x] **Step 7: GREEN, plus every suite that touches this call**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_before_run_anchor.py tests/test_auto_calc_mode.py \
  tests/test_scheduler.py tests/test_decision_log_noise.py \
  tests/test_scheduler_distributor.py tests/test_schedule_time_anchor.py \
  tests/test_sunrise_anchored_fitting.py -p _local_socket_unblock -q 2>&1 | tail -6
```

Expected: all pass.

- [x] **Step 8: commit**

```bash
git add custom_components/irrigation_plus/scheduler.py \
        tests/test_before_run_anchor.py tests/test_auto_calc_mode.py
git commit -F - <<'EOF'
fix(weighting): a calculation inside a dispatch prices that run, not the next

The resolver cannot know at that moment: the fired-occurrence guard has already
moved past this occurrence, and the governing bound resolves strictly after now.
Both mechanisms measured at +1 day for a daily schedule.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 14: the start-pinned site, which the review did not name

**Files:**
- Modify: `custom_components/irrigation_plus/scheduler.py:1820`
- Test: `tests/test_before_run_anchor.py`

- [x] **Step 1: write the failing test**

Append to `tests/test_before_run_anchor.py`:

```python
@pytest.mark.asyncio
async def test_the_start_pinned_decide_and_run_names_the_run_start():
    """It commits AT THE FIRE, by its own docstring, not at a decision point.

    The review sorted this under the pre_committed=True paths that commit ahead of
    the run. It does not: run_callback sets _finish_last_target and hands straight
    to it. It leaves _armed_runs in place, but that arm carries TODAY's target
    while the resolver has advanced to tomorrow's, so the SAME_OCCURRENCE
    proximity test rejects it and mechanism (B) stands alone.
    """
    manager, _ = _make_manager()
    manager.coordinator.async_commit_pre_run_calculation = AsyncMock()
    manager.coordinator.async_plan_zone_runs = AsyncMock(return_value=[])

    # _decide_and_run_start_pinned(schedule, now, target, finish)
    await manager._decide_and_run_start_pinned(_schedule(), TODAY_RUN, TODAY_RUN, None)

    manager.coordinator.async_commit_pre_run_calculation.assert_awaited_once_with(
        "all", run_start=TODAY_RUN
    )
```

- [x] **Step 2: RED**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_before_run_anchor.py::test_the_start_pinned_decide_and_run_names_the_run_start \
  -p _local_socket_unblock -q 2>&1 | tail -8
```

Expected: FAIL — awaited with `("all",)`. If it fails on something else
(`async_plan_zone_runs` needing more wiring, or an empty plan taking a different
branch), wire the minimum that gets past the commit line and note what you added.

- [x] **Step 3: pass it at `scheduler.py:1820`**

```python
        # At the fire, not at a decision point (see this method's own docstring),
        # so the run starts now and the resolver must not be asked.
        # siehe tests/test_before_run_anchor.py
        await self.coordinator.async_commit_pre_run_calculation(zones, run_start=now)
```

- [x] **Step 4: GREEN**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_before_run_anchor.py tests/test_sunrise_anchored_fitting.py \
  tests/test_schedule_time_anchor.py -p _local_socket_unblock -q 2>&1 | tail -6
```

Expected: all pass.

- [x] **Step 5: confirm the third commit site is deliberately untouched**

`_decide_and_arm(commit=True)` at `:1962` is reached from the `decide_callback`
registered only when `decision_point > now_utc` (`:1889-1894`) — genuinely ahead
of the run, so it must keep resolving.

```bash
git diff c5330c7f..HEAD -- custom_components/irrigation_plus/scheduler.py | grep -n "run_start"
```

Expected: three added `run_start` lines — the signature at `:2311`, `run_start=now`
at `:2302`, `run_start=run_start` at `:2332`, `run_start=now` at `:1820` — and
nothing within the `_decide_and_arm` body.

- [x] **Step 6: commit**

```bash
git add custom_components/irrigation_plus/scheduler.py tests/test_before_run_anchor.py
git commit -F - <<'EOF'
fix(weighting): the start-pinned dispatch names its run start too

Its own docstring says it commits at the fire rather than at a decision point, so
it carried the same day offset as the other dispatch path.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 15: a zone no schedule names is weighted from the calculation

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (the weighting block)
- Modify: `tests/test_experimental_features.py` (`_calc_coordinator` gains `hourly`)
- Modify: `tests/test_forecast_weighting_window.py` (replace one test, add one)

This **reverses requirement 3 of §2 and the third row of §8**. Decided by the
user, 2026-09-27, on the evidence that the precipitation skip guard — the other
half of the same setting, and the module being reused — already does exactly this
(`skip_conditions.py:235`).

- [x] **Step 1: let the coordinator factory serve an hourly series**

In `tests/test_experimental_features.py`:

```python
def _calc_coordinator(
    *, forecast_weighting=False, use_weather_service=False, days=1, hourly=None
):
```

and replace `coord._WeatherServiceClient = None` with:

```python
    # A client with an hourly accessor, because that series is what covers the
    # first 24 hours from the EVALUATION: get_forecast_data starts tomorrow by
    # contract, so a window anchored at the calculation has no daily entry for its
    # first hours. The skip guard leans on the same series for the same reason.
    coord._WeatherServiceClient = (
        SimpleNamespace(get_hourly_precipitation_forecast=lambda covering_until: hourly)
        if hourly is not None
        else None
    )
```

- [x] **Step 2: replace the test that pinned the old rule, and add its bound**

In `tests/test_forecast_weighting_window.py`, **delete**
`test_a_zone_with_no_resolvable_run_is_not_weighted` and put these in its place:

```python
def _hourly_covering_the_first_block(mm_per_hour_for_first_three):
    """24 stamps at one-hour spacing from NOW, covering block 0 exactly.

    Each rate covers the hour ENDING at its stamp and the first reaches back one
    step, so 24 stamps span [NOW, NOW+24h) -- the whole first block.
    The series has to cover the block WHOLE rather than hand over to the dated
    dailies partway: _entries_behind leaves out any entry that overlaps the series
    or starts exactly at its end, so a seam would leave the block uncovered and the
    weighting would abstain for a reason that has nothing to do with this test.
    """
    return [
        (
            NOW + datetime.timedelta(hours=hour),
            mm_per_hour_for_first_three if hour <= 3 else 0.0,
        )
        for hour in range(1, 25)
    ]


async def test_a_zone_no_schedule_names_is_weighted_from_the_calculation():
    """No enabled schedule names it, so the window starts at the calculation.

    The precipitation skip guard -- the other half of this same Precipitation
    forecast days setting, and the module this reuses -- already anchors at the
    evaluation when no run start is named (skip_conditions.py:235). Abstaining
    here would leave the two halves of one dropdown diverged in a second place,
    which is the thing this change exists to end.
    Cost, stated: someone calculating at 03:00 and watering from an automation at
    20:00 gets a window anchored 17 h early -- bounded by one day, and the same
    trade the guard already makes.
    """
    coord = _calc_coordinator(
        forecast_weighting=True,
        use_weather_service=True,
        days=1,
        hourly=_hourly_covering_the_first_block(2.0),
    )
    _run_at(coord, None)

    data = await coord.calculate_module(_zone(), _weather(10.0), _days(0.0))

    # 2 mm/h over the first three hours -> 6 mm; a 10 mm deficit less 6 mm at
    # 60 mm/h -> 4 mm -> 240 s.
    assert data[const.ZONE_DURATION] == 240
    assert data[const.ZONE_IRRIGATION_TARGET_BUCKET] == pytest.approx(-6.0)


async def test_a_zone_no_schedule_names_still_refuses_an_uncovered_window(caplog):
    """The first_24h_covered refusal survives the fallback, and bounds it.

    With no hourly series nothing forecasts the hours between the evaluation and
    the first dated day, so the block is not covered and the weighting still
    abstains. That is what the fallback actually buys: it reaches zones whose
    client serves an hourly series, which all four do.
    """
    coord = _calc_coordinator(forecast_weighting=True, use_weather_service=True, days=1)
    _run_at(coord, None)

    data = await coord.calculate_module(_zone(), _weather(10.0), _days(8.0))

    assert data[const.ZONE_DURATION] == 600
    assert any("does not cover" in r.getMessage() for r in caplog.records), caplog.text
```

- [x] **Step 3: RED on the first, GREEN on the second**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_forecast_weighting_window.py -p _local_socket_unblock -q 2>&1 | tail -10
```

Expected: `test_a_zone_no_schedule_names_is_weighted_from_the_calculation` fails
with `assert 600 == 240` — it still abstains. The second already passes.

- [x] **Step 4: replace the abstention with the fallback**

In `calculation.py`'s weighting block, hoist the evaluation moment above the
branch, keeping the existing `dt_util` comment where it is:

```python
                evaluated_at = dt_util.utcnow()
```

then delete the `if run_start is None: … rain = None` branch and its debug line,
and put this immediately after Task 12's resolver call:

```python
                if run_start is None:
                    # No enabled schedule names this zone -- someone irrigating
                    # from their own automations. The window then starts at the
                    # calculation, which is what the skip guard does with this same
                    # setting when no run start is named (skip_conditions.py:235):
                    # for the common "calculate, then irrigate" pattern that is the
                    # right anchor, and abstaining turned an experimental feature
                    # silently off. Bounded by one day where the two moments are
                    # far apart, and first_24h_covered still refuses a window
                    # nothing forecast.
                    # siehe tests/test_forecast_weighting_window.py::
                    #   test_a_zone_no_schedule_names_is_weighted_from_the_calculation
                    #   und ::test_a_zone_no_schedule_names_still_refuses_an_uncovered_window
                    run_start = evaluated_at
                    _LOGGER.debug(
                        "[calculate-module]: no scheduled run resolves for zone "
                        "%s, so the forecast weighting measures from this "
                        "calculation",
                        zone.get(const.ZONE_ID),
                    )
```

and change the `expected_rain` call to `evaluated_at=evaluated_at`.

- [x] **Step 5: GREEN**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  tests/test_forecast_weighting_window.py tests/test_experimental_features.py \
  -p _local_socket_unblock -q 2>&1 | tail -5
```

Expected: all pass.

- [x] **Step 6: commit**

```bash
git add custom_components/irrigation_plus/calculation.py \
        tests/test_experimental_features.py tests/test_forecast_weighting_window.py
git commit -F - <<'EOF'
fix(weighting): weigh a zone with no schedule from the calculation

Matches the precipitation skip guard, which anchors at the evaluation when no run
start is named. Abstaining turned the feature silently off for anyone irrigating
from their own automations.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 16: the references come out

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (one comment)
- Modify: `tests/test_forecast_weighting_window.py` (module docstring)
- Modify: `tests/test_next_run_start_for_zone.py` (module docstring)

- [x] **Step 1: find every one**

```bash
git diff c5330c7f..HEAD | grep -nE 'Eifel-Joe|§'
```

Expected: the three added lines, nothing else.

- [x] **Step 2: replace them with the upstream issues**

`Eifel-Joe#21` --> `#159`, `Eifel-Joe#22` --> `#160`. Both already exist in the
upstream repository as bug reports, their titles are these same two defects, and
`#159` is already named in the pull request body — so this cites *his* issues,
which is what he asked for. No issue is opened anywhere in order to be citable.

- `calculation.py`: "and is the seam Eifel-Joe#22 is about to move" --> "and is the
  seam #160 is about to move"
- `tests/test_forecast_weighting_window.py:1`: "(Eifel-Joe#21)" --> "(#159)"
- `tests/test_next_run_start_for_zone.py:1`: "(Eifel-Joe#21)" --> "(#159)"

Also drop the branch-local SHA from
`tests/test_forecast_weighting_window.py`'s docstring — "Measured on 10bb8077"
becomes "Measured before the fix". A base commit of our own branch means nothing
upstream, and it has moved anyway.

- [x] **Step 3: check 1 — the diff**

```bash
git diff c5330c7f..HEAD | grep -cE 'Eifel-Joe|§'
```

Expected: `0`.

- [x] **Step 4: lint, both CI gates**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: both clean. `ruff`'s `I001` may want the import block re-sorted after
Task 12; let that land here.

- [x] **Step 5: commit**

```bash
git add -u
git commit -F - <<'EOF'
docs: cite the upstream issues rather than our own tracker

Nobody reading this repository can resolve the old references.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 17: reshape the history, verify in full, three reference checks

**Files:** none — history and verification only.

- [x] **Step 1: full suite, then the name diff that decides**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ \
  -p _local_socket_unblock -q 2>&1 | tail -4
```

Expected: `7 failed / 9 skipped / 367 errors`, `passed` up by the number of tests
added.

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ \
  -p _local_socket_unblock -q 2>&1 \
  | grep -E '^(FAILED|ERROR) tests/' | sed 's/ - .*//' | sort \
  > /d/Entwicklung/HASI/issue21-work/after-names.txt
diff /d/Entwicklung/HASI/pr174-work/baseline-names.txt \
     /d/Entwicklung/HASI/issue21-work/after-names.txt
```

Expected: **empty**. Two details, both measured on this branch at Task 10:

- The ` - …` suffix is stripped before sorting, per the rebaseline memory.
- The grep must anchor on `tests/`, not on `FAILED|ERROR` alone. `batch.py`'s own
  log lines start with `ERROR` and a looser filter pulled six of them in, which
  made a correct run look like nine new failures. The baseline file contains only
  `^(FAILED|ERROR) tests/` lines — verified, zero exceptions — so the extraction
  has to match it.

- [x] **Step 2: reshape into four commits whose content never named our tracker**

The three references were introduced as **added** lines by two of the original
commits, so `git show <sha> | grep Eifel-Joe` still matches on those two even
after Task 16. A correcting commit on top is not enough — that is what cost
`JustChr#174` a reshape.

```bash
git branch issue21-prereshape
git reset --soft c5330c7f
```

Then **three** commits. `scheduler.py` carries two unrelated changes — the
resolver (Tasks 1–3) and the dispatch anchors (Tasks 13–14) — and they must not
share a commit, or the anchors ship under the resolver's heading. Interactive
staging is not available here, so the split uses the marker from Task 12 Step 7
instead of `git add -p`:

```bash
# 1 — the resolver, with scheduler.py as it stood BEFORE the anchors
git checkout issue21-resolver-only -- custom_components/irrigation_plus/scheduler.py
git add custom_components/irrigation_plus/scheduler.py tests/test_next_run_start_for_zone.py
git commit -F - <<'EOF'
feat(scheduler): answer when a zone's next scheduled run begins, without pricing it

The forecast weighting runs inside the calculation, so anything it calls that
reads a zone's bucket or duration closes a loop around the number being computed.
This resolver touches recurrence resolution only, and a test that makes every
pricing call raise keeps it that way.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF

# 2 — the weighting itself
git add custom_components/irrigation_plus/calculation.py \
        tests/test_experimental_features.py tests/test_forecast_weighting_window.py
git commit -F - <<'EOF'
fix(weighting): price the forecast over the run's own window, not the list's head

The window was a positional slice of a list that starts tomorrow by contract, so
it priced calendar days from tomorrow whatever day and hour the run fell on. The
module that fixed this for the precipitation skip guard is reused rather than
copied, so the two halves of one setting cannot diverge again. A zone no schedule
names is measured from the calculation, which is what the guard does with the same
setting when no run start is named.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF

# 3 — the dispatch anchor, which restores the full scheduler.py
git checkout issue21-prereshape -- custom_components/irrigation_plus/scheduler.py
git add custom_components/irrigation_plus/scheduler.py \
        custom_components/irrigation_plus/auto_calc.py \
        custom_components/irrigation_plus/__init__.py \
        tests/test_before_run_anchor.py tests/test_auto_calc_mode.py
git commit -F - <<'EOF'
fix(weighting): a calculation inside a dispatch prices that run, not the next

Under the before-each-run calculation mode the calculation happens inside the
run's own dispatch, where the run-start resolver cannot answer for it: the
fired-occurrence guard has already moved past this occurrence, and the governing
bound resolves strictly after now. Both mechanisms measured at a full day late on
a daily schedule, including for the start-pinned path, which commits at the fire
rather than at a decision point. The dispatch now names its own moment.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

- [x] **Step 2b: nothing may be left over**

```bash
git status --short
```

Expected: **empty**. Anything remaining belongs to one of the three above — amend
that commit rather than adding a fourth.

- [x] **Step 3: prove the reshape changed nothing**

```bash
git diff issue21-prereshape..HEAD
```

Expected: **empty**. If not, the reshape lost something — stop and fix it.

- [x] **Step 4: the three reference checks**

```bash
# 1 — the diff
git diff c5330c7f..HEAD | grep -nE 'Eifel-Joe|§'
# 2 — the commit messages
git log c5330c7f..HEAD --format='%s%n%b' | grep -nE 'Eifel-Joe|§'
# 3 — the content of every single commit
for sha in $(git rev-list c5330c7f..HEAD); do
  echo "$sha: $(git show $sha | grep -cE 'Eifel-Joe|§')"
done
```

Expected: checks 1 and 2 print nothing. Check 3 prints `1` per commit — the
`Author:` line and nothing else. Any `2` means a reference is still inside a
commit's content; find it with `git show <sha> | grep -nE 'Eifel-Joe|§'`.

- [x] **Step 5: lint on the reshaped tree**

```bash
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: both clean.

- [x] **Step 6: re-run the probe, before and after**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe \
  /d/Entwicklung/HASI/issue21-work/probe_before_run_anchor.py
```

Expected: unchanged — two rows still `+1 day`. That is correct and is the point:
the resolver's own answer at dispatch is not what changed; what changed is that
nothing asks it there any more. Note this explicitly rather than reading it as a
failure.

- [x] **Step 7: STOP. Do not push.**

The push, the pull-request update and every word of the reply need approval in the
chat first. Bring to that conversation:

- the name diff (Step 1, empty), the reshape diff (Step 3, empty), the three check
  outputs (Step 4);
- that his option (ii) was **rejected with a measurement** — a plain start-time
  schedule records no fired occurrence, so there is nothing within
  `SAME_OCCURRENCE` to return, and the answer is still a day late;
- that the fix covers **one site more than the review named**
  (`_decide_and_run_start_pinned`, which commits at the fire by its own docstring);
- that the fallback he asked for is **accepted**, with the guard's own line as the
  reason, and that `first_24h_covered` bounds it to clients serving an hourly
  series;
- the apology owed for the references, first, not explained away.

---

## The live test, decided before it is promised

The weighting only runs when the weather service answers, and **PirateWeather
returns 429 on HA-Test** — `calculate_zone` produces nothing there, which is why
the `#174` live test used `run_zone duration:` instead. `run_zone` does not
recalculate, so it cannot exercise this path at all.

A live test of Phase R is therefore **not available** by the `#174` recipe. Say so
rather than staging something that looks like one. The observable criteria this
change is verified against, in order:

1. the empty name diff against the `c5330c7f` baseline (Task 17 Step 1);
2. the four tests that drive the real `_advance_past_fired_occurrence` and
   `_next_governing_time` (Tasks 13 and 14) — the machinery a live run would
   exercise;
3. the clock pin proven load-bearing by moving it (Task 11 Step 6).

If a live run is wanted anyway it needs a weather client that answers on HA-Test —
a second provider key, or Open-Meteo, which needs none. That is its own piece of
work and the user's decision, not something to improvise at the end.
