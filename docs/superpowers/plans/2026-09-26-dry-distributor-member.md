# A dry distributor member run is not a delivery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `distributor.py` crediting a member zone for water a live flow meter watched the whole window and never measured.

**Architecture:** `_dist_measure_window`'s `0.0 -> None` collapse becomes an evidence test — a `0.0` survives as a real answer unless the meter never read after the valve-open seed (`last_live`) or saw a totalizer reset it cannot price (`meter.saw_reset()`). Its single consumer, the sweep, then records that answer as `RUN_RESULT_FAILED` / `flow_never_started` with no credit instead of falling back to the planned-window estimate. No zone fault is raised, because the distributor path has nowhere that clears one.

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest + pytest-homeassistant-custom-component, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-09-26-dry-distributor-member-design.md`
**Issue:** [`Eifel-Joe#53`](https://github.com/Eifel-Joe/HAsmartirrigation/issues/53)
**Base commit:** `418ab8a0` · **Branch:** `fix-a-dry-member-run-is-not-a-delivery`

---

## Measured baseline (do not re-derive)

Full suite on `418ab8a0` in its own worktree (`D:/Entwicklung/HASI/issue53-work/base`):

```
7 failed, 3254 passed, 9 skipped, 10 warnings, 349 errors in 329.59s
```

- Non-passing test names: **356**, in `D:/Entwicklung/HASI/issue53-work/baseline-names.txt`.
- Cross-checked `diff`-identical against `issue3-work/baseline-names.txt`, measured
  independently on the same commit. The base has not moved.
- Extraction pattern — **the loose one is wrong**, it picks up a captured log line
  (`ERROR    custom_components.irrigation_plus.batch:batch.py:304 …`) and yields 357:

```bash
grep -E "^(FAILED|ERROR) tests[/\\]" <run-output> | sed 's/ - .*$//' | sort -u
```

**Expected end state: 3254 + 10 new tests = 3264 passed, and the 356 names
`diff`-identical.** Task 1 inverts an existing test in place, so it adds no name. The
ten: two in Task 2/3, two in Task 4, two in Task 6, three in Task 7, one in Task 8.

## Measured FlowMeter behaviour (do not re-derive)

`DISTRIBUTOR_FLOW_POLL_SECONDS == 5`, so a 30 s window is 6 polls after the seed.

| input | `delivered()` | `saw_reset()` |
|---|---|---|
| rate `12.0 L/min` at the seed only, then unavailable | `0.0` | `False` |
| rate `0.0 L/min` live across the whole window | `0.0` | `False` |
| totalizer `100, 100, 5, 7` (`auto -> lifetime`) | `0.0` | `True` |
| totalizer `100, 102, 5, 7` (`auto -> lifetime`) | `2.0` | `True` |
| rate `-0.4 L/min` live across 30 s | `-0.2` | `False` |
| **any** single seed sample (`-0.4`, `-99`, `0`, `12` L/min; `-5`, `100` L) | `0.0` | `False` |

The first row is the whole reason the `last_live` witness exists: a sensor plainly
showing 12 L/min at the open, then dead, is byte-identical to a dry cistern at the
meter's own interface. The `-0.2` row is why the sweep's comparison is `<= 0` and why
the credit call passes a hard `0.0`.

**The last row settles where `<= 0` is load-bearing and where it is not.** A meter with
only the seed sample delivers *exactly* `0.0` whatever it read — a rate has no interval
to integrate over, a totalizer has no climb above its own baseline. So inside
`_dist_measure_window`, where the guard only fires when the witness has failed,
`delivered <= 0` and `delivered == 0` cannot be told apart: that mutation is
**unreachable**, not untested (Task 10, M3a). The comparison that carries real weight is
the sweep's `dry = measured <= 0`, which is what stops a live `-0.2` from reaching
`_dist_credit_zone` and writing the bucket *below* where the run started (Task 7, M3b).

## Test command (verbatim, from a worktree — there is no `.venv` here)

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/distributor.py` | outlet-ring cycle engine | Modify: `import math`; `_dist_read_flow` (~643); `_dist_measure_window` (~665, ~743-749); `_dist_credit_zone` (~977); the sweep (~1504-1552) |
| `tests/test_distributor.py` | `_dist_measure_window` / `_dist_read_flow` unit level | Modify: invert 1 test (~741), add 4 |
| `tests/test_distributor_dispatch.py` | the sweep, with `_dist_measure_window` mocked | Modify: widen 8 stub signatures, add 3 |

No other file changes. No i18n, no `npm run build`, no dist bundles — `flow_never_started`
already has a label in all eight `frontend/localize/languages/*.json`.

---

### Task 1: A live meter's `0.0` survives as an answer

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:665-749`
- Test: `tests/test_distributor.py:741-749`

- [x] **Step 1: Invert the test that pins the collapse**

Replace the whole existing test at `tests/test_distributor.py:741`:

```python
async def test_measure_window_zero_flow_healthy_sensor_is_unreliable():
    # A live meter reading 0 the whole window (dry pipe / stuck valve) is unreliable
    # -> None (fall back to time-based crediting), NOT a credited 0 L. Part B fail-safe.
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(0.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured is None
    assert actual == 30
    assert stopped is False
```

with:

```python
async def test_measure_window_zero_flow_live_meter_measures_zero():
    # Eifel-Joe#53: a meter that watched the whole window and integrated nothing has
    # ANSWERED — 0.0, not "no measurement". Collapsed to None (the old Part B
    # fail-safe) the caller fell back to the planned-window credit, so a member zone
    # behind an empty cistern was credited in full and logged as completed.
    # The two states that produce a 0.0 WITHOUT having measured the run stay None and
    # have their own tests below.
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(0.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured == 0.0
    assert actual == 30
    assert stopped is False
```

- [x] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py::test_measure_window_zero_flow_live_meter_measures_zero -p _local_socket_unblock -v
```

Expected: **FAIL**, `assert None == 0.0`.

This is the only existing test that goes red. The three neighbours asserting
`measured is None` (`:609` no sensor, `:619` unavailable-from-start, `:711` dead
sensor) all return before the meter exists and are untouched — confirm in Step 4.

- [x] **Step 3: Delete the collapse**

In `_dist_measure_window`, replace:

```python
        delivered = meter.delivered()
        stopped_early = (
            target is not None and (delivered or 0.0) >= target and elapsed < cap
        )
        # Part B fail-safe: a live-but-dry meter delivered 0 L -> unreliable so the caller
        # falls back to time-based crediting (spec: delivered <= 0 -> None).
        reliable = delivered is not None and delivered > 0
        return (delivered if reliable else None), elapsed, stopped_early
```

with:

```python
        delivered = meter.delivered()
        # Bound from the RAW value, before the evidence test below, so its behaviour
        # is unchanged. (The two cannot co-occur anyway: `target` is bound only under
        # `tv > 0`, so this needs delivered >= target > 0. The order keeps that true
        # without leaning on the argument.)
        stopped_early = (
            target is not None and (delivered or 0.0) >= target and elapsed < cap
        )
        return delivered, elapsed, stopped_early
```

Also fix the docstring's `delivered` bullet (~line 675), whose old wording states a
root cause that no longer exists:

```python
        - ``delivered`` — measured litres, or None to fall back to time-based crediting
          (no sensor / dead meter / unreliable reading).
```

becomes:

```python
        - ``delivered`` — measured litres, or None to fall back to time-based
          crediting. ``0.0`` is a MEASUREMENT (a live meter that integrated nothing:
          the dry-cistern case) and the caller writes the run off on it. None means
          nothing was measured: no sensor, a meter that never read, a meter that read
          ONLY at the valve-open seed, or a totalizer reset it cannot price.
```

- [x] **Step 4: Run the test and its neighbours**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass.** Specifically `test_measure_window_no_sensor_returns_none`,
`test_measure_window_unavailable_falls_back_none`,
`test_measure_window_dead_sensor_sleeps_window_not_cap` and
`test_measure_window_sensor_dies_mid_extend_stops_before_cap` are still green — if any
went red, the collapse was doing work beyond the dry case and this plan is wrong.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "fix(distributor): a live meter's 0.0 is an answer, not a missing one

Eifel-Joe#53. The collapse made a dry cistern indistinguishable from a broken
sensor, so the sweep credited the planned window.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: A meter that read only at the valve-open seed has not measured the run

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:~743`
- Test: `tests/test_distributor.py` (append after the Task 1 test)

- [ ] **Step 1: Write the failing test**

```python
async def test_measure_window_sensor_dead_after_open_read_is_not_dry():
    # Eifel-Joe#53 / the review finding on Eifel-Joe#4 (spec 10.1): the window feeds the
    # valve-open reading into the meter at at=0.0, so _have_reading is true from the
    # first second and delivered() never returns None again whatever the sensor does
    # next. A RATE sensor showing 12 L/min at the open and then going unavailable has
    # no second sample to integrate against, so it measures exactly 0.0 — measured,
    # byte-identical to the dry cistern above. `last_live` is the only thing that
    # separates them, and it stays at its 0.0 seed value.
    c, d = _flow_host()
    calls = {"n": 0}

    def _drive(_sensor):
        calls["n"] += 1
        return _state(12.0, "L/min") if calls["n"] == 1 else None  # seed, then dead

    c.hass.states.get = Mock(side_effect=_drive)
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured is None  # no evidence -> time-based, as before the fix
    assert actual == 30
    assert stopped is False
```

- [ ] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py::test_measure_window_sensor_dead_after_open_read_is_not_dry -p _local_socket_unblock -v
```

Expected: **FAIL**, `assert 0.0 is None` — Task 1 deleted the collapse that used to hide this.

- [ ] **Step 3: Add the witness**

In `_dist_measure_window`, insert between `stopped_early` and the `return`:

```python
        # Wurzel: a 0.0 is only an ANSWER when the meter was in a position to answer.
        #   The valve-open seed above (meter.sample(..., 0.0)) makes _have_reading true
        #   from the first second, so delivered() never returns None again — a sensor
        #   that answered once at the open and then died reports 0.0 exactly like a
        #   meter that watched the run and saw no water. Measured: a rate sensor
        #   showing 12 L/min at the seed and then unavailable measures 0.0, because a
        #   single sample has no interval to integrate over.
        # Fix: `last_live` already records the elapsed time of the most recent LIVE
        #   read and is seeded to 0.0, so `last_live <= 0.0` IS "never read after the
        #   open". Without evidence the value goes back to None and the caller keeps
        #   its time-based credit, exactly as before this change.
        # NOT-TO-DO: do not fold this into FlowMeter.delivered(). Its 0.0 contract is
        #   what the crediting callers price a genuinely dry run with; only the caller
        #   that writes a run OFF needs the stricter evidence. (The self-closing path
        #   exposes the same test as FlowMeter.saw_reading_after_open(); it is derived
        #   locally here so this fix does not depend on that unmerged change.)
        # siehe tests/test_distributor.py::
        #   test_measure_window_sensor_dead_after_open_read_is_not_dry
        if delivered is not None and delivered <= 0 and last_live <= 0.0:
            delivered = None
        return delivered, elapsed, stopped_early
```

`<= 0` and not `== 0`: a rate sensor with a negative resting offset measures below
zero — `-0.4 L/min` across 30 s measures `-0.2`, and `== 0` would let it reach the
credit branch.

- [ ] **Step 4: Run the test and the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass**, including the Task 1 test (its sensor is live on every poll,
so `last_live == 30.0`).

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "fix(distributor): a meter that read only at the valve open has not measured

Eifel-Joe#53. The open seed makes _have_reading true from second 0, so a sensor
that died straight after it reported 0.0 like a dry cistern.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: A totalizer reset the meter cannot price is not a dry run

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:~743`
- Test: `tests/test_distributor.py` (append after the Task 2 test)

- [ ] **Step 1: Write the failing test**

```python
async def test_measure_window_totalizer_reset_is_not_dry():
    # Eifel-Joe#53 / spec 10.1's second case: the distributor resolves its counter type
    # read-only, so an unlearned `auto` becomes the over-credit-safe `lifetime`, which
    # KEEPS the pre-reset baseline. A per-run counter that resets mid-run therefore
    # climbs back from 0 without ever passing the baseline and measures 0.0 while real
    # water flowed — Eifel-Joe#4 measured 45 L delivered against a delivered() of 0.0.
    # The sister case (100 -> 102 -> 5 -> 7, above) measures 2.0 and is unaffected:
    # only a reset that leaves NOTHING credited looks dry.
    c, d = _flow_host()
    vals = iter([100.0, 100.0, 5.0, 7.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals, 7.0), "L"))
    measured, actual, stopped = await c._dist_measure_window(d, 15)
    assert measured is None  # saw_reset() -> no evidence -> time-based
    assert stopped is False
```

- [ ] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py::test_measure_window_totalizer_reset_is_not_dry -p _local_socket_unblock -v
```

Expected: **FAIL**, `assert 0.0 is None`. The reads are live, so Task 2's
`last_live` witness is satisfied and does not catch this.

- [ ] **Step 3: Add the reset term**

Change the condition added in Task 2 from:

```python
        if delivered is not None and delivered <= 0 and last_live <= 0.0:
```

to:

```python
        if delivered is not None and delivered <= 0 and (
            last_live <= 0.0 or meter.saw_reset()
        ):
```

and extend the comment block's `Wurzel` with the second state (amend, do not stack a
second block on top — the block documents one condition):

```python
        #   A second state does the same: a totalizer reset this meter cannot price.
        #   flow_learn_resolve sends an unlearned `auto` to the over-credit-safe
        #   `lifetime`, which KEEPS the pre-reset baseline, so a per-run counter's
        #   post-reset climb never rises above it. Measured on the self-closing path:
        #   45 L really delivered, delivered() == 0.0, saw_reset() == True. The classic
        #   runner diverts this to a time-based credit BEFORE its dry branch
        #   (irrigation.py:1536).
        # siehe tests/test_distributor.py::test_measure_window_totalizer_reset_is_not_dry
```

- [ ] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass**, including `test_measure_window_counter_drop_keeps_baseline`
(measures `2.0`, so `delivered <= 0` is false and the term never fires) and
`test_dist_measure_window_per_run_counter` (measures `8.0`).

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "fix(distributor): a totalizer reset it cannot price is not a dry run

Eifel-Joe#53. auto resolves to lifetime, which keeps the pre-reset baseline, so a
per-run counter measures 0.0 across a run that really watered.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: A non-numeric reading is not a witness

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:14-20` (`import math`), `:643-664`
- Test: `tests/test_distributor.py` (append after the Task 3 test)

- [ ] **Step 1: Write the failing test**

```python
async def test_measure_window_nan_after_open_read_is_not_dry():
    # Eifel-Joe#53, the precondition of Task 2's witness: _dist_read_flow promises
    # "None when unavailable/non-numeric", but float("nan") parses, so a nan sensor
    # returned a tuple and set `last_live` — while FlowMeter.sample() silently REJECTED
    # the same value (flow_metering.py, `if not math.isfinite(raw)`). The witness then
    # said "the meter read after the open" about a reading the meter threw away, and a
    # sensor stuck at nan had its run written off as dry. The sister-path check carried
    # down to the precondition, which is the level Eifel-Joe#4's review found missing.
    c, d = _flow_host()
    calls = {"n": 0}

    def _drive(_sensor):
        calls["n"] += 1
        return _state(12.0, "L/min") if calls["n"] == 1 else _state(float("nan"), "L/min")

    c.hass.states.get = Mock(side_effect=_drive)
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured is None
    assert stopped is False


def test_read_flow_rejects_non_finite():
    # Same root, at the unit: nan and inf are not numbers, and the docstring already
    # said so. FlowMeter would drop them anyway; the tuple is what misleads `last_live`.
    c, d = _flow_host()
    for bad in ("nan", "inf", "-inf"):
        s = Mock()
        s.state = bad
        s.attributes = {"unit_of_measurement": "L/min"}
        c.hass.states.get = Mock(return_value=s)
        assert c._dist_read_flow("sensor.inlet_flow") is None, bad
    c.hass.states.get = Mock(return_value=_state(3.5, "L/min"))
    assert c._dist_read_flow("sensor.inlet_flow") == (3.5, "L/min", None)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_distributor.py::test_measure_window_nan_after_open_read_is_not_dry" "tests/test_distributor.py::test_read_flow_rejects_non_finite" -p _local_socket_unblock -v
```

Expected: **both FAIL.** The first `assert 0.0 is None` (the nan reads set
`last_live` to 30.0 while contributing nothing), the second
`assert (nan, 'L/min', None) is None`.

- [ ] **Step 3: Reject non-finite readings**

Add to the import block at the top of `distributor.py`, alphabetically after `logging`:

```python
import math
```

In `_dist_read_flow`, replace:

```python
        try:
            value = float(state.state)
        except (ValueError, TypeError):
            return None
```

with:

```python
        try:
            value = float(state.state)
        except (ValueError, TypeError):
            return None
        # Wurzel: float("nan") and float("inf") PARSE, so a sensor reporting either
        #   returned a tuple from a function whose docstring promises None for
        #   "non-numeric" — while FlowMeter.sample() rejected the very same value
        #   (flow_metering.py, `if not math.isfinite(raw)`). Harmless until
        #   _dist_measure_window started reading `last_live` as evidence that the meter
        #   had read after the valve-open seed: a nan set the witness without the meter
        #   accepting anything, and the run was written off as dry.
        # Fix: reject here, so a caller can trust that a tuple reached the meter.
        # NOT-TO-DO: do not special-case it in the window's loop instead. The
        #   dead-meter extend guard reads the same `last_live`, and a nan sensor IS
        #   dead for metering — it must stop holding the shared inlet open, which only
        #   happens if the read returns None here.
        # siehe tests/test_distributor.py::test_read_flow_rejects_non_finite
        if not math.isfinite(value):
            return None
```

- [ ] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "fix(distributor): a nan reading is not a flow reading

Eifel-Joe#53. float('nan') parsed, so it set the after-open witness while the
FlowMeter rejected the same value — a nan sensor read as a dry run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Widen the eight `_dist_credit_zone` stubs (enabling, no behaviour change)

**Files:**
- Modify: `tests/test_distributor_dispatch.py` lines 1327, 1371, 1507, 1551, 1593, 1824, 1917, 1995

Task 6 gives `_dist_credit_zone` a `detail` keyword. Eight test stubs enumerate its
signature exhaustively and would raise `TypeError: unexpected keyword argument
'detail'` — measured, all eight share the identical prefix, so this is one
substitution applied eight times. Do it **before** Task 6, or the suite breaks between
two commits.

- [ ] **Step 1: Substitute**

```bash
sed -i 's/lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None:/lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None, **_kw:/g' tests/test_distributor_dispatch.py
```

- [ ] **Step 2: Verify exactly eight sites changed and nothing else**

```bash
git diff --numstat tests/test_distributor_dispatch.py
grep -c "ceiling=None, \*\*_kw:" tests/test_distributor_dispatch.py
```

Expected: `8	8	tests/test_distributor_dispatch.py` and a count of `8`.

- [ ] **Step 3: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass**, unchanged — `**_kw` only widens what the stubs accept.

- [ ] **Step 4: Commit**

```bash
git add tests/test_distributor_dispatch.py
git commit -m "test(distributor): let the credit-zone stubs accept keywords they ignore

Eight stubs enumerated _dist_credit_zone's signature, so any new keyword broke
them. Preparation for the detail keyword.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `_dist_credit_zone` carries a run-log detail

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:977-1045`
- Test: `tests/test_distributor.py` (append after the Task 4 tests)

- [ ] **Step 1: Write the failing test**

```python
async def test_credit_zone_passes_detail_to_record_run():
    # Eifel-Joe#53: the sweep needs to say WHY a run failed, and _record_run already
    # takes `detail` — _dist_credit_zone was the only thing in the way.
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c.async_write_watered_bucket = AsyncMock()
    c._stamp_run_finalized = AsyncMock()
    c._record_run = AsyncMock()
    c._depth_from_volume_native = Mock(return_value=0.0)
    await c._dist_credit_zone(
        {const.ZONE_ID: 7, const.ZONE_BUCKET: -3.0},
        60,
        measured_l=0.0,
        result=const.RUN_RESULT_FAILED,
        detail=const.FAULT_FLOW_NEVER_STARTED,
    )
    assert c._record_run.await_args.kwargs["result"] == const.RUN_RESULT_FAILED
    assert c._record_run.await_args.kwargs["detail"] == const.FAULT_FLOW_NEVER_STARTED


async def test_credit_zone_dry_leaves_the_bucket_and_the_total_alone():
    # Eifel-Joe#53, spec 5.1/5.3/5.4 — the three observable values the live test reads,
    # pinned here through the REAL _dist_credit_zone rather than a mock of it:
    # a 0.0 credit must leave the bucket exactly where the run found it, add nothing to
    # water_used_total, and not stamp last_irrigation. The ceiling is deliberately set
    # BELOW the pre-run bucket to prove the clamp cannot turn the run into a withdrawal.
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c.async_write_watered_bucket = AsyncMock()
    c._stamp_run_finalized = AsyncMock()
    c._record_run = AsyncMock()
    c._depth_from_volume_native = Mock(return_value=0.0)
    await c._dist_credit_zone(
        {const.ZONE_ID: 7, const.ZONE_BUCKET: -3.0, const.ZONE_STATE: "automatic"},
        60,
        measured_l=0.0,
        planned_seconds=60,
        result=const.RUN_RESULT_FAILED,
        detail=const.FAULT_FLOW_NEVER_STARTED,
        ceiling=-5.0,
    )
    c.async_write_watered_bucket.assert_awaited_once_with(7, -3.0)  # unchanged
    c._stamp_run_finalized.assert_awaited_once_with(7, 0.0)  # 0 L -> no stamp
    assert c._record_run.await_args.kwargs["volume_l"] == 0.0  # nothing to the total
```

- [ ] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -k "credit_zone_passes_detail or credit_zone_dry_leaves" -p _local_socket_unblock -v
```

Expected: **both FAIL**, `TypeError: _dist_credit_zone() got an unexpected keyword
argument 'detail'`.

- [ ] **Step 3: Add the parameter**

In the signature, after `result`:

```python
        result: str = const.RUN_RESULT_COMPLETED,
        detail: str | None = None,
```

and in the `_record_run` call, after `result=result`:

```python
            result=result,
            detail=detail,
```

Add one line to the docstring, after the `planned_seconds` sentence:

```python
        ``detail`` is the run-log reason a non-completion carries (the dry-run fault
        constant); None for every ordinary credit.
```

- [ ] **Step 4: Run the test and both distributor files**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_credit_ceiling.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): let a member run record why it failed

Eifel-Joe#53. _record_run already took detail; _dist_credit_zone did not pass one.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The sweep records a dry member run as failed and credits nothing

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:1506-1530`
- Test: `tests/test_distributor_dispatch.py` (append at end of file)

- [ ] **Step 1: Write the two failing tests**

```python
async def test_sweep_records_a_dry_member_run_as_failed():
    """Eifel-Joe#53: a live meter that measured 0.0 across the window means no water
    reached the member zone. The run must be logged FAILED with flow_never_started and
    credited NOTHING — before the fix the 0.0 was collapsed to None and the sweep
    credited the whole planned window, so an empty cistern read as a full delivery."""
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._dist_measure_window = AsyncMock(return_value=(0.0, 60, False))
    credited = {}
    c._dist_credit_zone = AsyncMock(
        side_effect=lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None, detail=None, **_kw: credited.update(
            measured=measured_l, result=result, detail=detail
        )
    )
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {
                "id": 7,
                "distributor_id": 0,
                "outlet_number": 1,
                "duration": 60,
                "bucket": -3,
                "bucket_threshold": 0,
                "state": "automatic",
            }
        ]
    )
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited["result"] == const.RUN_RESULT_FAILED
    assert credited["detail"] == const.FAULT_FLOW_NEVER_STARTED
    # A hard 0.0, never the measured value: a rate sensor's negative resting offset
    # measures -0.2 over a dry run, and a negative depth would write the bucket BELOW
    # the level the run started from.
    assert credited["measured"] == 0.0


async def test_sweep_records_a_dry_member_run_as_failed_without_a_target():
    """Eifel-Joe#53: the dry test must not be gated on a volume target. A member with
    no target — a can't-stop member, or one whose target volume is 0 — is the majority
    of the Part A configuration, and keying the failure on `measured < target` would
    log it COMPLETED."""
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._metered_target_volume = Mock(return_value=0.0)  # no target
    c._dist_measure_window = AsyncMock(return_value=(0.0, 60, False))
    credited = {}
    c._dist_credit_zone = AsyncMock(
        side_effect=lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None, detail=None, **_kw: credited.update(
            result=result, detail=detail
        )
    )
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {
                "id": 7,
                "distributor_id": 0,
                "outlet_number": 1,
                "duration": 60,
                "bucket": -3,
                "bucket_threshold": 0,
                "state": "automatic",
            }
        ]
    )
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited["result"] == const.RUN_RESULT_FAILED
    assert credited["detail"] == const.FAULT_FLOW_NEVER_STARTED


async def test_sweep_treats_a_negative_measurement_as_dry():
    """Eifel-Joe#53 / spec 10.3: a rate sensor with a negative resting offset integrates
    BELOW zero across a dry run — -0.4 L/min over 30 s measures -0.2, measured on the
    real FlowMeter. `dry = measured == 0` would miss it, and the negative depth would
    reach _dist_credit_zone and write the bucket BELOW the level the run started from,
    turning a failed run into a withdrawal. This is the test that kills M3b."""
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._dist_measure_window = AsyncMock(return_value=(-0.2, 60, False))
    credited = {}
    c._dist_credit_zone = AsyncMock(
        side_effect=lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None, detail=None, **_kw: credited.update(
            measured=measured_l, result=result
        )
    )
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {
                "id": 7,
                "distributor_id": 0,
                "outlet_number": 1,
                "duration": 60,
                "bucket": -3,
                "bucket_threshold": 0,
                "state": "automatic",
            }
        ]
    )
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited["result"] == const.RUN_RESULT_FAILED
    assert credited["measured"] == 0.0  # the -0.2 never reaches the credit
```

- [ ] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -k "dry_member_run or negative_measurement" -p _local_socket_unblock -v
```

Expected: **all three FAIL** — none of them reaches `RUN_RESULT_FAILED`. Read the
actual value out of each failure rather than assuming which of `COMPLETED` / `PARTIAL`
it was: that depends on whether `_metered_target_volume` bound a target in the mocks,
and the point of the tests is only that it is not `FAILED`. The third also shows
`measured == -0.2` reaching the credit.

- [ ] **Step 3: Branch the sweep**

Replace the `run_result` block and the credit call (`distributor.py:1508-1528`):

```python
                # Review-M-1: a metered run that ended BELOW a set target volume is a
                # partial (under-)delivery, not a completion. Key on the measured volume
                # directly (not `stopped_early`), so a target reached on the very last
                # poll — where `elapsed == cap` exits the loop before the early-stop
                # break — still logs COMPLETED. A time-based fallback (measured is None)
                # can't tell, so it stays COMPLETED.
                run_result = (
                    const.RUN_RESULT_PARTIAL
                    if (
                        measured is not None
                        and target is not None
                        and measured < target
                    )
                    else const.RUN_RESULT_COMPLETED
                )
                await self._dist_credit_zone(
                    zone,
                    actual_seconds,
                    measured_l=measured,
```

with:

```python
                # Wurzel (Eifel-Joe#53): _dist_measure_window used to collapse a
                #   live-but-dry meter's 0.0 to None, and None here means "credit the
                #   planned window". A member zone behind an empty cistern was
                #   therefore credited in full, its litres added to water_used_total,
                #   last_irrigation stamped and the run logged COMPLETED.
                # Fix: a measured 0.0 is the answer "no water arrived" — log the run
                #   FAILED with its reason and credit nothing. There is no optimistic
                #   pre-credit on this path to reverse: the sweep writes the bucket
                #   only in _dist_credit_zone, after measuring, so measured_l=0.0
                #   leaves the bucket exactly where the run found it.
                # NOT-TO-DO: do not gate `dry` on `target`. A can't-stop member, or one
                #   whose target volume is 0, has target None — that is most of the
                #   Part A configuration, and it would log COMPLETED.
                # NOT-TO-DO: do not raise a zone fault here. Nothing on the distributor
                #   path CLEARS one — all five _clear_zone_fault callers sit in the
                #   classic runner's own machinery — so it would never end.
                # siehe tests/test_distributor_dispatch.py::
                #   test_sweep_records_a_dry_member_run_as_failed
                #   test_sweep_records_a_dry_member_run_as_failed_without_a_target
                #   test_sweep_treats_a_negative_measurement_as_dry
                # `<= 0`, not `== 0`: a rate sensor with a negative resting offset
                # integrates below zero on a dry run (-0.4 L/min over 30 s measures
                # -0.2, measured), and `== 0` would send that negative depth into the
                # credit — a failed run that writes the bucket DOWN.
                dry = measured is not None and measured <= 0
                # Review-M-1: a metered run that ended BELOW a set target volume is a
                # partial (under-)delivery, not a completion. Key on the measured volume
                # directly (not `stopped_early`), so a target reached on the very last
                # poll — where `elapsed == cap` exits the loop before the early-stop
                # break — still logs COMPLETED. A time-based fallback (measured is None)
                # can't tell, so it stays COMPLETED. `dry` is tested FIRST: a dry run
                # with a target set satisfies `measured < target` and would log PARTIAL.
                run_result = (
                    const.RUN_RESULT_FAILED
                    if dry
                    else const.RUN_RESULT_PARTIAL
                    if (
                        measured is not None
                        and target is not None
                        and measured < target
                    )
                    else const.RUN_RESULT_COMPLETED
                )
                await self._dist_credit_zone(
                    zone,
                    actual_seconds,
                    # A hard 0.0, not `measured`: a rate sensor with a negative resting
                    # offset measures -0.2 L across a dry run (measured), and that
                    # depth would write the bucket BELOW the pre-run level.
                    measured_l=0.0 if dry else measured,
                    detail=const.FAULT_FLOW_NEVER_STARTED if dry else None,
```

- [ ] **Step 4: Run the tests and the whole file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass**, including the three Review-M-1 tests
(`test_sweep_logs_partial_when_cap_hit_without_target` measures `5.0`,
`test_sweep_logs_completed_when_target_reached_at_cap` and
`test_sweep_logs_completed_when_target_reached` measure above their targets — none is
dry, so `run_result` is unchanged for all three).

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor_dispatch.py
git commit -m "fix(distributor): a dry member run is recorded failed, not credited

Eifel-Joe#53. A member zone behind an empty cistern had its bucket credited for
the full planned window and its run logged completed.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: A dry run is not a calibration sample

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:~1545`
- Test: `tests/test_distributor_dispatch.py` (append at end of file)

- [ ] **Step 1: Write the failing test**

```python
async def test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample():
    """Eifel-Joe#53: a run that delivered nothing says nothing about the hardware's
    throughput. The advisory's own floor (FLOW_CAL_MIN_SAMPLE_L, ~6.7 L) already
    refuses a 0.0, so this is defence — but that floor is derived from two tuning
    constants, and a future tuning that lowered it would make this the caller that
    feeds 0 L over a full window in as a real observed rate."""
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._metered_target_volume = Mock(return_value=0.0)  # can't-stop member, no target
    c._dist_measure_window = AsyncMock(return_value=(0.0, 60, False))
    c._dist_credit_zone = AsyncMock()
    c._dist_flow_calibration_check = AsyncMock()
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {
                "id": 7,
                "distributor_id": 0,
                "outlet_number": 1,
                "duration": 60,
                "bucket": -3,
                "bucket_threshold": 0,
                "state": "automatic",
            }
        ]
    )
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    c._dist_flow_calibration_check.assert_not_awaited()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py::test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample -p _local_socket_unblock -v
```

Expected: **FAIL** — `Expected '_dist_flow_calibration_check' to not have been awaited.
Awaited 1 times.` The gate is `measured is not None`, and a dry run's `0.0` passes it.

- [ ] **Step 3: Add `not dry` to the gate**

Replace:

```python
                if not can_stop and measured is not None and not duration_override:
```

with:

```python
                # `not dry` (Eifel-Joe#53): a run that delivered nothing is not a
                # sample of the valve's rate, and a caller that KNOWS that should not
                # offer it. The advisory's own floor already refuses a 0.0
                # (irrigation.py:1285, FLOW_CAL_MIN_SAMPLE_L ~6.7 L) — this is defence
                # against a future tuning of the two constants that floor derives from.
                # siehe tests/test_distributor_dispatch.py::
                #   test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample
                if (
                    not can_stop
                    and measured is not None
                    and not dry
                    and not duration_override
                ):
```

- [ ] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor_dispatch.py
git commit -m "fix(distributor): a dry run is not a throughput sample

Eifel-Joe#53. With the 0.0 no longer collapsed, the calibration advisory's
measured-is-not-None gate let a dry run through.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Full suite, name diff, lint

**Files:** none modified.

- [ ] **Step 1: Run the FULL suite — a subset does not count**

```bash
cd /d/Entwicklung/HASI/issue53-work/wt
TMP=/d/Entwicklung/HASI/issue53-work/tmp TEMP=/d/Entwicklung/HASI/issue53-work/tmp \
  /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ \
  -p _local_socket_unblock -q --no-header -p no:cacheprovider \
  > /d/Entwicklung/HASI/issue53-work/after-full.txt 2>&1; tail -3 /d/Entwicklung/HASI/issue53-work/after-full.txt
```

Expected: `7 failed, 3264 passed, 9 skipped, … 349 errors` — baseline `3254` plus the
**10** new tests (Task 1 inverts one in place, so it is not a new name). Any other
number means read the diff in Step 2 before touching code.

- [ ] **Step 2: Diff the non-passing names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue53-work
grep -E "^(FAILED|ERROR) tests[/\\]" after-full.txt | sed 's/ - .*$//' | sort -u > after-names.txt
diff baseline-names.txt after-names.txt && echo "IDENTISCH — keine Regression"
```

Expected: **no output from `diff`.** A single added name is a regression; the fault
count alone cannot show it, because the same three files give 51 errors as a subset and
13 in a full run.

- [ ] **Step 3: Lint — the two that gate CI, on the component only**

```bash
cd /d/Entwicklung/HASI/issue53-work/wt
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: `… files left unchanged` (or reformatted — then re-run the affected test
file) and `All checks passed!`.

- [ ] **Step 4: Commit any reformat, then record the numbers in this plan**

Append the measured totals under "Measured baseline". Commit:

```bash
git add -A
git commit -m "docs(plan): record the measured suite totals and the name diff

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Mutation matrix — eight mutations, each with a named outcome

**Files:** none permanently modified.

Mutation proof is mandatory. **Revert every mutation with `git checkout --
custom_components/irrigation_plus/distributor.py`, never by back-substitution** — an
ambiguous anchor once left M1 live and silently corrupted M2 and M3. And a mutation
that kills nothing may be the WRONG mutation: check first whether it can reach the
behaviour at all, before suspecting the test.

- [ ] **Step 1: Run each mutation, record which test dies**

| # | Mutation | Must kill |
|---|---|---|
| M1 | `if delivered is not None and delivered <= 0 and (last_live <= 0.0 or meter.saw_reset()):` → drop `last_live <= 0.0 or ` | `test_measure_window_sensor_dead_after_open_read_is_not_dry`, `test_measure_window_nan_after_open_read_is_not_dry` |
| M2 | same line → drop ` or meter.saw_reset()` | `test_measure_window_totalizer_reset_is_not_dry` |
| M3a | same line → `delivered == 0` instead of `delivered <= 0` | **nothing — and that is the correct outcome.** See Step 2. |
| M3b | the sweep's `dry = measured is not None and measured <= 0` → `== 0` | `test_sweep_treats_a_negative_measurement_as_dry` |
| M4 | `dry = …` moved AFTER the `run_result` block, and `RUN_RESULT_FAILED if dry` dropped from the ternary | `test_sweep_records_a_dry_member_run_as_failed`, `…_without_a_target` |
| M5 | drop `and not dry` from the calibration gate | `test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample` |
| M6 | drop `if not math.isfinite(value): return None` | `test_read_flow_rejects_non_finite`, `test_measure_window_nan_after_open_read_is_not_dry` |
| M7 | `measured_l=0.0 if dry else measured` → `measured_l=measured` | `test_sweep_treats_a_negative_measurement_as_dry` (its `credited["measured"] == 0.0`) |

For each:

```bash
cd /d/Entwicklung/HASI/issue53-work/wt
# apply the mutation with an editor, then:
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py -p _local_socket_unblock -q
git checkout -- custom_components/irrigation_plus/distributor.py
git diff --stat   # MUST be empty before the next mutation
```

- [ ] **Step 2: M3a survives, and it must — do not go hunting for a test**

M3a kills nothing, and the reason is measured rather than assumed. The guard it mutates
fires **only when the after-open witness has already failed**, which means the meter
holds exactly one sample, the valve-open seed. A rate sensor then has no interval to
integrate over and a totalizer no climb above its own baseline, so `delivered()` is
*exactly* `0.0` — for every input tried: `-0.4`, `-99`, `0`, `12` L/min and `-5`, `100`
L all return `0.0`. `<= 0` and `== 0` are therefore indistinguishable at that line.

**This is the "a mutation that kills nothing may be the wrong mutation" case.** The
comparison is kept `<= 0` for consistency with the sweep's and with the self-closing
twin, not because a test can tell. The comparison that carries the weight is M3b, one
level up, where a *live* negative measurement really does reach the credit.

Record M3a in the matrix as **survives, unreachable, with this reasoning** — not as a
coverage gap, and not as a reason to add a test that cannot distinguish the two.

- [ ] **Step 3: Commit the matrix result into this plan**

Write the six outcomes (killed / survived, and which test) into a `## Mutation matrix`
section at the end of this file, then:

```bash
git add docs/superpowers/plans/2026-09-26-dry-distributor-member.md
git commit -m "docs(plan): record the mutation matrix results

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## After the plan: what still has to happen

These are **not** implementation tasks; they follow the task-loop's later phases and
each needs its own chat approval.

1. **Review** — `superpowers:requesting-code-review`, then
   `superpowers:receiving-code-review`. The review that mattered on `Eifel-Joe#4`
   found the precondition one level above the branch, so point the reviewer at
   §4 of the spec specifically.
2. **Live test on HA-Test** — throwaway pre-release, installed via HACS.
   **`production` is not touched.** The criterion is spec §8's four observable
   values. HA-Test restart is pre-approved by rule but must still be announced;
   HA-Prod needs chat approval.
   Clear HA-Test's Grace Test flow-sensor field first (it currently holds
   `flow_sensor` + `throughput 4` and sits on a fault), or every run there is dry
   for the wrong reason and the test proves nothing.
3. **Archive the design history** (project rule P1) onto `archive/design-history`
   **before** any branch deletion.
4. **Push / PR / issue comment** — each needs chat approval. The PR body must state
   that **an existing test was inverted**
   (`test_measure_window_zero_flow_healthy_sensor_is_unreliable` →
   `test_measure_window_zero_flow_live_meter_measures_zero`), that
   `Eifel-Joe#55` owns the cycle-level question, and that the witness is derived
   locally rather than from `FlowMeter.saw_reading_after_open()` so the change does
   not depend on the unmerged `JustChr#174`.
