# A dry distributor member run is not a delivery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `distributor.py` crediting a member zone for water a live flow meter watched the whole window and never measured.

**Architecture:** `_dist_measure_window`'s `0.0 -> None` collapse becomes an evidence test — a `0.0` survives as a real answer unless the meter failed to account for the run (`FlowMeter.metered_the_run()`: it credited a reading and declined none) or saw a totalizer reset it cannot price (`meter.saw_reset()`). Its single consumer, the sweep, then records that answer as `RUN_RESULT_FAILED` / `flow_never_started` with no credit instead of falling back to the planned-window estimate. No zone fault is raised, because the distributor path has nowhere that clears one.

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

**Expected end state: 3254 + 20 new tests = 3274 passed, and the 356 names
`diff`-identical.** Task 1 inverts an existing test in place, so it adds no name. The
seventeen: two in Tasks 2/3, two in Task 4, **seven in Task 4b** (four in
`test_distributor.py`, three in `test_flow_meter.py`), two in Task 6, three in Task 7,
one in Task 8.

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
| `custom_components/irrigation_plus/flow_metering.py` | the shared `FlowMeter` engine | Modify (Task 4b, superseded by 4c): two flags in `__init__` — `_priced` at the two credit sites, `_declined` at the two refusal sites — plus the `metered_the_run()` accessor |
| `tests/test_flow_meter.py` | `FlowMeter` unit level | Modify (Task 4b): add 3 |
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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py::test_measure_window_sensor_dead_after_open_read_is_not_dry -p _local_socket_unblock -v
```

Expected: **FAIL**, `assert 0.0 is None` — Task 1 deleted the collapse that used to hide this.

- [x] **Step 3: Add the witness**

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

- [x] **Step 4: Run the test and the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass**, including the Task 1 test (its sensor is live on every poll,
so `last_live == 30.0`).

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py::test_measure_window_totalizer_reset_is_not_dry -p _local_socket_unblock -v
```

Expected: **FAIL**, `assert 0.0 is None`. The reads are live, so Task 2's
`last_live` witness is satisfied and does not catch this.

- [x] **Step 3: Add the reset term**

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

- [x] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass**, including `test_measure_window_counter_drop_keeps_baseline`
(measures `2.0`, so `delivered <= 0` is false and the term never fires) and
`test_dist_measure_window_per_run_counter` (measures `8.0`).

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_distributor.py::test_measure_window_nan_after_open_read_is_not_dry" "tests/test_distributor.py::test_read_flow_rejects_non_finite" -p _local_socket_unblock -v
```

Expected: **both FAIL.** The first `assert 0.0 is None` (the nan reads set
`last_live` to 30.0 while contributing nothing), the second
`assert (nan, 'L/min', None) is None`.

- [x] **Step 3: Reject non-finite readings**

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

- [x] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/distributor.py tests/test_distributor.py
git commit -m "fix(distributor): a nan reading is not a flow reading

Eifel-Joe#53. float('nan') parsed, so it set the after-open witness while the
FlowMeter rejected the same value — a nan sensor read as a dry run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

---

### Task 4b: The witness comes from inside the meter

**Why this task exists:** Tasks 2–4 built the witness from `last_live`, the elapsed
time of the most recent poll that returned a tuple. The review measured that as a
**regression**, not an approximation — three inputs return `0.0` for a run that
delivered water, where `418ab8a0` returned `None`:

| input | real water | `418ab8a0` | after Tasks 1–4 |
|---|---|---|---|
| rate 12 L/min, live only every 5th poll (gap 25 s > `max_gap_s` 20 s) | whole window | `None` | **`0.0`** |
| totalizer `100 → 60, 70, 80, 90` | 30 L | `None` | **`0.0`** |
| totalizer `45 → 8, 20, 30, 40` | 32 L | `None` | **`0.0`** |

All three are `FlowMeter` accepting a value and then declining to price it:
`_sample_rate` refuses to integrate across a gap wider than `max_gap_s`;
`_sample_totalizer`'s drop branch keeps its baseline and credits nothing; and that
branch's `near_zero` floor (`max(1.0, 0.1 × last)`) misses a per-run reset whose
first post-reset read clears it. `_have_reading` cannot tell any of them apart, and
neither can a witness built from reading *timings*. See spec §4.

Once Task 7 lands, each becomes `RUN_RESULT_FAILED` on a run that watered — the
same defect class as the critical `JustChr#174`'s first review missed.

**Files:**
- Modify: `custom_components/irrigation_plus/flow_metering.py` (init flag, two credit sites, one accessor)
- Modify: `custom_components/irrigation_plus/distributor.py` (the guard + two comment blocks)
- Test: `tests/test_distributor.py`, `tests/test_flow_meter.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_distributor.py`, after `test_read_flow_rejects_non_finite`:

```python
async def test_measure_window_rate_gap_wider_than_max_gap_is_not_dry():
    # Eifel-Joe#53, spec 4.1 case 1 — the flapping sensor. _sample_rate refuses to
    # integrate when dt exceeds max_gap_s (4 polls = 20 s), because bridging dropped
    # samples with a recovered rate would over-credit. The poll loop still saw a live
    # reading, so a timings-based witness is satisfied while the meter priced NOTHING.
    # 12 L/min flowed the whole window; measured against the real FlowMeter, the old
    # last_live witness returned 0.0 here and 418ab8a0 returned None.
    c, d = _flow_host()
    seq = [12.0] + [None, None, None, None, 12.0] * 2 + [None, None]
    it = iter(seq)
    c.hass.states.get = Mock(
        side_effect=lambda s: (lambda v: None if v is None else _state(v, "L/min"))(
            next(it, None)
        )
    )
    measured, actual, stopped = await c._dist_measure_window(d, 60)
    assert measured is None
    assert stopped is False


async def test_measure_window_totalizer_below_retained_baseline_is_not_dry():
    # Eifel-Joe#53, spec 4.1 case 2. near_zero = max(1.0, 0.1*100) = 10, so the drop to
    # 60 is a glitch and not a reset: saw_reset() stays False, the baseline 100 is kept,
    # and the 60 -> 90 climb (30 L of real water) never passes it. delivered() is 0.0
    # with every read live, so neither the timings witness nor saw_reset() catches it.
    c, d = _flow_host()
    vals = iter([100.0, 60.0, 70.0, 80.0, 90.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals, 90.0), "L"))
    measured, actual, stopped = await c._dist_measure_window(d, 20)
    assert measured is None
    assert stopped is False


async def test_measure_window_per_run_reset_above_near_zero_is_not_dry():
    # Eifel-Joe#53, spec 4.1 case 3. near_zero = max(1.0, 0.1*45) = 4.5, and the first
    # read after the reset is 8 — ABOVE the floor, so the reset saw_reset() exists for
    # is invisible. 32 L really flowed (8 -> 40) below the retained baseline of 45.
    c, d = _flow_host()
    vals = iter([45.0, 8.0, 20.0, 30.0, 40.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals, 40.0), "L"))
    measured, actual, stopped = await c._dist_measure_window(d, 20)
    assert measured is None
    assert stopped is False


async def test_measure_window_a_priced_zero_is_still_dry():
    # Eifel-Joe#53, the CONTROL for the three tests above: tightening the witness must
    # not disable the feature. An interval credited at 0 L counts as priced, and that is
    # how a genuinely dry run is recognised — priced_anything() is not "delivered > 0".
    # Three shapes, all dry, all must stay 0.0:
    #   a rate sensor reading 0 every poll,
    #   a totalizer holding its value (100, 100, ...),
    #   a pressure surge at the open then nothing — the surge is the SEED, which prices
    #   nothing, and every interval after it is credited at 0. This last one is the
    #   issue's leading case, an empty cistern behind a valve that still thumps.
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(0.0, "L/min"))
    assert (await c._dist_measure_window(d, 30))[0] == 0.0

    c, d = _flow_host()
    c.hass.states.get = Mock(side_effect=lambda s: _state(100.0, "L"))
    assert (await c._dist_measure_window(d, 20))[0] == 0.0

    c, d = _flow_host()
    surge = iter([12.0])
    c.hass.states.get = Mock(
        side_effect=lambda s: _state(next(surge, 0.0), "L/min")
    )
    assert (await c._dist_measure_window(d, 30))[0] == 0.0
```

And append to `tests/test_flow_meter.py`, which unit-tests `FlowMeter` directly (match
that file's existing construction style for the meter):

```python
def test_priced_anything_separates_accepted_from_credited():
    # Eifel-Joe#53: delivered() gates on _have_reading, which a single valve-open seed
    # already satisfies — so a 0.0 cannot be read as "measured dry" without knowing
    # whether anything was ever CREDITED. The two states are different, and only this
    # accessor exposes the second one.
    m = FlowMeter("lifetime", max_gap_s=20)
    assert m.priced_anything() is False  # nothing sampled yet
    m.sample(12.0, "L/min", None, 0.0)  # the valve-open seed prices nothing
    assert m.delivered() == 0.0  # _have_reading is already true
    assert m.priced_anything() is False
    m.sample(12.0, "L/min", None, 100.0)  # gap 100 s > max_gap_s -> not integrated
    assert m.priced_anything() is False
    m.sample(12.0, "L/min", None, 105.0)  # gap 5 s -> integrated
    assert m.priced_anything() is True


def test_priced_anything_counts_an_interval_credited_at_zero():
    # A rate of 0 across a live interval IS a measurement — it is what a genuinely dry
    # run looks like, and the guard must be able to write that run off.
    m = FlowMeter("lifetime", max_gap_s=20)
    m.sample(0.0, "L/min", None, 0.0)
    m.sample(0.0, "L/min", None, 5.0)
    assert m.delivered() == 0.0
    assert m.priced_anything() is True


def test_priced_anything_is_false_for_a_totalizer_below_its_baseline():
    # A counter that fell below its retained baseline and climbed back part of the way
    # has its climb credited NOWHERE, so the run was not priced.
    m = FlowMeter("lifetime")
    for i, v in enumerate([100.0, 60.0, 70.0, 80.0, 90.0]):
        m.sample(v, "L", "total_increasing", i * 5.0)
    assert m.delivered() == 0.0
    assert m.priced_anything() is False
    # ... while a totalizer that merely holds its value HAS been priced, at 0 L.
    m2 = FlowMeter("lifetime")
    for i in range(4):
        m2.sample(100.0, "L", "total_increasing", i * 5.0)
    assert m2.delivered() == 0.0
    assert m2.priced_anything() is True
```

- [x] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_flow_meter.py -p _local_socket_unblock -q
```

Expected: the three `..._is_not_dry` tests FAIL with `assert 0.0 is None`; the three
`test_priced_anything_*` tests FAIL with `AttributeError: 'FlowMeter' object has no
attribute 'priced_anything'`. `test_measure_window_a_priced_zero_is_still_dry` **passes
already** — it is a control, and it must still pass at the end.

- [x] **Step 3: Give `FlowMeter` the accessor**

In `flow_metering.py`'s `__init__`, after the `_saw_reset` line:

```python
        self._saw_reset = False  # a totalizer near-zero drop was observed this run
        # Wurzel: `_have_reading` (which delivered() gates on) is satisfied by the
        #   valve-open seed alone, so a 0.0 could not be told apart from a meter that
        #   ACCEPTED readings and priced none of them — a rate whose gap exceeded
        #   max_gap_s, a totalizer that fell below its retained baseline. A caller that
        #   wrote a run off on a 0.0 therefore wrote off runs that really watered:
        #   measured, 12 L/min across a window whose sensor flapped every 5th poll.
        # Fix: latch this wherever a reading is actually CREDITED, and expose it
        #   separately (see priced_anything). Never set on the seed path or on a drop
        #   the meter declines to price.
        # NOT-TO-DO: do not make delivered() return None in those cases instead. Its
        #   0.0 contract is what the crediting callers price a genuinely dry run with.
        # siehe test_flow_meter.py::test_priced_anything_separates_accepted_from_credited
        self._priced = False  # at least one reading was credited this run
```

In `_sample_rate`, inside the branch that credits:

```python
            if self._max_gap_s is None or dt <= self._max_gap_s:
                self._delivered += rate * dt / 60.0
                self._priced = True
```

In `_sample_totalizer`, inside the rising branch:

```python
        if litres >= self._last:  # rising: credit the true climb
            self._delivered += litres - self._last
            self._last = litres
            self._priced = True
            return
```

And the accessor, directly above `saw_reset`:

```python
    def priced_anything(self) -> bool:
        """True iff at least one reading was actually CREDITED this run.

        Distinct from the reading that ``delivered()`` gates on: a single
        valve-open seed satisfies that one and prices nothing. A meter can accept
        readings and credit none of them — a rate whose inter-sample gap exceeded
        ``max_gap_s``, a totalizer that fell below its retained baseline and
        climbed back part of the way. Only a caller that writes a run OFF on the
        strength of a ``0.0`` needs that difference.

        An interval credited at 0 L DOES count: that is what a genuinely dry run
        looks like, and the caller has to be able to recognise it.
        """
        return self._priced
```

- [x] **Step 4: Switch the guard, and rewrite both comment blocks**

In `_dist_measure_window`, change the condition's third term from
`(last_live <= 0.0 or meter.saw_reset())` to
`(not meter.priced_anything() or meter.saw_reset())`.

**Then rewrite the comment block above it.** Its current `Wurzel`/`Fix` describe
`last_live` as the witness, and that description is now false — this project treats a
comment whose root cause no longer matches as worse than none. Replace the block with:

```python
        # Wurzel: a 0.0 is only an ANSWER when the meter priced something. The
        #   valve-open seed above (meter.sample(..., 0.0)) makes the meter's
        #   have-a-reading state true from the first second, so delivered() never
        #   returns None again whatever the sensor does next — and a meter can accept
        #   readings and credit NONE of them. Measured against the real FlowMeter, all
        #   three of these return 0.0 for a run that delivered water, and all three
        #   returned None before this change:
        #     rate 12 L/min, live only every 5th poll -> _sample_rate will not
        #       integrate across a gap wider than max_gap_s;
        #     totalizer 100 -> 60,70,80,90 -> the drop is not near-zero, so the
        #       baseline is kept and 30 L of climb is credited nowhere;
        #     totalizer 45 -> 8,20,30,40 -> a per-run reset whose first post-reset
        #       read clears near_zero (4.5), so saw_reset() never trips either.
        # Fix: ask the meter what it CREDITED, not when it last answered.
        #   priced_anything() is false for every case above and true for a dry run
        #   that was really measured (an interval credited at 0 L counts). saw_reset()
        #   stays beside it and is NOT redundant: a totalizer reading 100,100,5,7
        #   prices the flat interval at 0 L, so only saw_reset() catches the reset
        #   after it. The classic runner makes the same diversion before its own dry
        #   branch (irrigation.py:1536).
        # NOT-TO-DO: do not derive this from the poll loop's own timings. That was the
        #   first design (a `last_live <= 0.0` test) and it is what the three inputs
        #   above defeat: the loop sees a live tuple, the meter throws the value away.
        # NOT-TO-DO: do not fold either term into FlowMeter.delivered(). Its 0.0
        #   contract is what the crediting callers price a genuinely dry run with.
        # siehe tests/test_distributor.py::
        #   test_measure_window_sensor_dead_after_open_read_is_not_dry
        #   test_measure_window_totalizer_reset_is_not_dry
        #   test_measure_window_rate_gap_wider_than_max_gap_is_not_dry
        #   test_measure_window_totalizer_below_retained_baseline_is_not_dry
        #   test_measure_window_per_run_reset_above_near_zero_is_not_dry
        #   test_measure_window_a_priced_zero_is_still_dry
```

**And rewrite `_dist_read_flow`'s block**, whose `Wurzel` currently says the nan hole
matters because it misleads `last_live`. It no longer does — `FlowMeter.sample()`
rejects a nan before either pricing path, so `priced_anything()` cannot be fooled by
one. The guard stays for two other reasons; replace that block with:

```python
        # Wurzel: float("nan") and float("inf") PARSE, so a sensor reporting either
        #   returned a tuple from a function whose docstring promises None for
        #   "non-numeric". FlowMeter.sample() rejects the same value anyway
        #   (flow_metering.py, `if not math.isfinite(raw)`), so nothing was
        #   mis-credited — but the poll loop reads these tuples for a second purpose.
        # Fix: reject here, so the function keeps its own contract and every caller
        #   can treat a tuple as a reading the meter will accept.
        # Beleg: the dead-meter extend guard keys on the gap since the last tuple, so
        #   a nan sensor used to look alive and hold the shared inlet open for the
        #   whole extend cap. Measured, window 30 / cap 600: 600 s without this guard,
        #   30 s with it.
        # NOT-TO-DO: do not special-case it in the window's poll loop instead — the
        #   extend guard would still have to repeat the test, and a nan sensor IS dead
        #   for metering on every path that reads it.
        # siehe tests/test_distributor.py::test_read_flow_rejects_non_finite
```

- [x] **Step 5: Run both files, then the three distributor files**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_flow_meter.py -p _local_socket_unblock -q
```

Expected: **all pass.** `tests/test_flow_meter.py` is 45 tests before this task and 48
after; `tests/test_distributor.py` is 56 before and 60 after. If anything in
`test_flow_meter.py` went red, the `_priced` flag was latched in the wrong place —
report it rather than adjusting the test.

Then check the other consumers of `FlowMeter`, which this task did not intend to
change (the flag is additive, nothing reads it yet except the distributor):

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_flow_calibration.py tests/test_flow_units.py tests/test_observed_watering.py -p _local_socket_unblock -q
```

Expected: unchanged from before this task. Note the count before you start.

- [x] **Step 6: Lint and commit**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/flow_metering.py custom_components/irrigation_plus/distributor.py tests/test_distributor.py tests/test_flow_meter.py
git commit -F - <<'EOF'
fix(flow): ask the meter what it credited, not when it last answered

Eifel-Joe#53. A witness built from the poll loop's timings is not sound: three
measured inputs have FlowMeter accept a reading and price none of it, and all
three then look identical to a dry cistern -- a rate whose gap exceeds
max_gap_s, a totalizer below its retained baseline, and a per-run reset whose
first post-reset read clears near_zero.

FlowMeter latches whether a reading was ever CREDITED and exposes it as
priced_anything(). An interval credited at 0 L counts, so a genuinely dry run is
still recognised. saw_reset() stays: 100,100,5,7 prices the flat interval, so
only it catches the reset that follows.

<ATTRIBUTION>
EOF
```

Then tick Task 4b's six checkboxes and `git commit --amend --no-edit`.

---

### Task 5: Widen the eight `_dist_credit_zone` stubs (enabling, no behaviour change)

**Files:**
- Modify: `tests/test_distributor_dispatch.py` lines 1327, 1371, 1507, 1551, 1593, 1824, 1917, 1995

Task 6 gives `_dist_credit_zone` a `detail` keyword. Eight test stubs enumerate its
signature exhaustively and would raise `TypeError: unexpected keyword argument
'detail'` — measured, all eight share the identical prefix, so this is one
substitution applied eight times. Do it **before** Task 6, or the suite breaks between
two commits.

- [x] **Step 1: Substitute**

```bash
sed -i 's/lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None:/lambda z, s, measured_l=None, planned_seconds=None, result=None, ceiling=None, **_kw:/g' tests/test_distributor_dispatch.py
```

- [x] **Step 2: Verify exactly eight sites changed and nothing else**

```bash
git diff --numstat tests/test_distributor_dispatch.py
grep -c "ceiling=None, \*\*_kw:" tests/test_distributor_dispatch.py
```

Expected: `8	8	tests/test_distributor_dispatch.py` and a count of `8`.

- [x] **Step 3: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass**, unchanged — `**_kw` only widens what the stubs accept.

- [x] **Step 4: Commit**

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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py -k "credit_zone_passes_detail or credit_zone_dry_leaves" -p _local_socket_unblock -v
```

Expected: **both FAIL**, `TypeError: _dist_credit_zone() got an unexpected keyword
argument 'detail'`.

- [x] **Step 3: Add the parameter**

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

- [x] **Step 4: Run the test and both distributor files**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_credit_ceiling.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the two failing tests**

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

- [x] **Step 2: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -k "dry_member_run or negative_measurement" -p _local_socket_unblock -v
```

Expected: **all three FAIL** — none of them reaches `RUN_RESULT_FAILED`. Read the
actual value out of each failure rather than assuming which of `COMPLETED` / `PARTIAL`
it was: that depends on whether `_metered_target_volume` bound a target in the mocks,
and the point of the tests is only that it is not `FAILED`. The third also shows
`measured == -0.2` reaching the credit.

- [x] **Step 3: Branch the sweep**

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

- [x] **Step 4: Run the tests and the whole file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass**, including the three Review-M-1 tests
(`test_sweep_logs_partial_when_cap_hit_without_target` measures `5.0`,
`test_sweep_logs_completed_when_target_reached_at_cap` and
`test_sweep_logs_completed_when_target_reached` measure above their targets — none is
dry, so `run_result` is unchanged for all three).

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py::test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample -p _local_socket_unblock -v
```

Expected: **FAIL** — `Expected '_dist_flow_calibration_check' to not have been awaited.
Awaited 1 times.` The gate is `measured is not None`, and a dry run's `0.0` passes it.

- [x] **Step 3: Add `not dry` to the gate**

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

- [x] **Step 4: Run the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: **all pass.**

- [x] **Step 5: Commit**

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

- [x] **Step 1: Run the FULL suite — a subset does not count**

```bash
cd /d/Entwicklung/HASI/issue53-work/wt
TMP=/d/Entwicklung/HASI/issue53-work/tmp TEMP=/d/Entwicklung/HASI/issue53-work/tmp \
  /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ \
  -p _local_socket_unblock -q --no-header -p no:cacheprovider \
  > /d/Entwicklung/HASI/issue53-work/after-full.txt 2>&1; tail -3 /d/Entwicklung/HASI/issue53-work/after-full.txt
```

Expected: `7 failed, 3271 passed, 9 skipped, … 349 errors` — baseline `3254` plus the
**17** new tests (Task 1 inverts one in place, so it is not a new name). Any other
number means read the diff in Step 2 before touching code.

- [x] **Step 2: Diff the non-passing names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue53-work
grep -E "^(FAILED|ERROR) tests[/\\]" after-full.txt | sed 's/ - .*$//' | sort -u > after-names.txt
diff baseline-names.txt after-names.txt && echo "IDENTISCH — keine Regression"
```

Expected: **no output from `diff`.** A single added name is a regression; the fault
count alone cannot show it, because the same three files give 51 errors as a subset and
13 in a full run.

- [x] **Step 3: Lint — the two that gate CI, on the component only**

```bash
cd /d/Entwicklung/HASI/issue53-work/wt
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: `… files left unchanged` (or reformatted — then re-run the affected test
file) and `All checks passed!`.

- [x] **Step 4: Commit any reformat, then record the numbers in this plan**

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

- [x] **Step 1: Run each mutation, record which test dies**

| # | Mutation | Must kill |
|---|---|---|
| M1 | the guard → drop `not meter.priced_anything() or ` | `test_measure_window_sensor_dead_after_open_read_is_not_dry`, `..._nan_after_open_read_is_not_dry`, `..._rate_gap_wider_than_max_gap_is_not_dry`, `..._totalizer_below_retained_baseline_is_not_dry`, `..._per_run_reset_above_near_zero_is_not_dry` |
| M2 | same line → drop ` or meter.saw_reset()` | `test_measure_window_totalizer_reset_is_not_dry` — **the pin that proves `priced_anything()` does not subsume it** (`100,100,5,7` prices the flat interval) |
| M2a | drop `self._priced = True` from `_sample_rate` | `test_measure_window_a_priced_zero_is_still_dry`, `test_priced_anything_counts_an_interval_credited_at_zero` — a dry rate run would stop being written off, i.e. the feature silently disables |
| M2b | drop `self._priced = True` from `_sample_totalizer` | `test_measure_window_a_priced_zero_is_still_dry`, `test_priced_anything_is_false_for_a_totalizer_below_its_baseline` |
| M3a | same line → `delivered == 0` instead of `delivered <= 0` | **nothing — and that is the correct outcome.** See Step 2. |
| M3c | `priced_anything()` returns `self._delivered > 0` instead of `self._priced` | `test_measure_window_a_priced_zero_is_still_dry`, `test_priced_anything_counts_an_interval_credited_at_zero` — guards the one misreading that would look like a simplification and would disable the whole feature |
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

- [x] **Step 2: M3a survives, and it must — do not go hunting for a test**

M3a kills nothing, and the reason is measured rather than assumed. The guard it mutates
fires only when the meter priced nothing, and a meter that priced nothing has a
`_delivered` of *exactly* `0.0` — every increment to it happens at one of the two sites
that also latch `_priced`. A negative `delivered` therefore always comes with
`priced_anything() == True`, so `<= 0` and `== 0` are indistinguishable at that line.
(Measured on the earlier design for the same reason: a seed-only meter returns `0.0`
for every input tried — `-0.4`, `-99`, `0`, `12` L/min and `-5`, `100` L.)

**This is the "a mutation that kills nothing may be the wrong mutation" case.** The
comparison is kept `<= 0` for consistency with the sweep's and with the self-closing
twin, not because a test can tell. The comparison that carries the weight is M3b, one
level up, where a *live* negative measurement really does reach the credit.

Record M3a in the matrix as **survives, unreachable, with this reasoning** — not as a
coverage gap, and not as a reason to add a test that cannot distinguish the two.

- [x] **Step 3: Commit the matrix result into this plan**

Write the six outcomes (killed / survived, and which test) into a `## Mutation matrix`
section at the end of this file, then:

```bash
git add docs/superpowers/plans/2026-09-26-dry-distributor-member.md
git commit -m "docs(plan): record the mutation matrix results

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4c: A run is written off only when the meter accounted for all of it

**Why this task exists.** Task 4b asked the meter "did you price *anything*?" The final
review measured that one priced interval latches the flag for the whole run, so a single
ordinary interval at the start masks a whole window of flow the meter then refused to
price. Verified against the real `FlowMeter` at the distributor's own 5 s cadence — each
of these is the corresponding §4.1 case with two ordinary reads in front of it:

| input (one reading per 5 s poll) | real water | `418ab8a0` | after Task 4b |
|---|---|---|---|
| rate `0, 0,` then live only every 5th poll at `12 L/min` | ~10 L | `None` | **`0.0`** |
| totalizer `100, 100,` then `60, 70, 80, 90` | 30 L | `None` | **`0.0`** |
| totalizer `45, 45,` then `8, 20, 30, 40` | 32 L | `None` | **`0.0`** |

Case 1 needs only a pump that takes more than one poll to build pressure plus the
flapping sensor the dead-meter extend guard was written for. This is the same defect
class as §4.1 one step further out, and a regression against the base commit.

**The correct question is not "did the meter price anything" but "did the meter account
for this run".** So the accessor is replaced rather than supplemented: `priced_anything()`
becomes `metered_the_run()`, true only when something was priced **and** nothing was
declined. Verified by prototype (reverted again): all three composites above become
`None`, all four dry controls stay `0.0` — a rate reading 0 every poll, a flat totalizer,
a pressure surge at the open (`12, 0, 0, …`), and `100, 100, 5, 7` via `saw_reset()` —
and the 266 tests of the five affected files stay green.

**Files:**
- Modify: `custom_components/irrigation_plus/flow_metering.py`
- Modify: `custom_components/irrigation_plus/distributor.py` (the guard + its comment)
- Test: `tests/test_flow_meter.py`, `tests/test_distributor.py`

- [x] **Step 1: Rewrite the three `FlowMeter` pins and add the declined ones**

In `tests/test_flow_meter.py`, **replace** the three `test_priced_anything_*` tests added
by Task 4b with these four. The concept changed, so they are rewritten, not extended:

```python
def test_metered_the_run_separates_accepted_from_credited():
    # Eifel-Joe#53: delivered() gates on having A reading, which a single valve-open seed
    # already satisfies — so a 0.0 cannot be read as "measured dry" without knowing
    # whether the meter accounted for the run. These are different states.
    m = FlowMeter("lifetime", max_gap_s=20)
    assert m.metered_the_run() is False  # nothing sampled yet
    m.sample(12.0, "L/min", None, 0.0)  # the valve-open seed prices nothing
    assert m.delivered() == 0.0  # having-a-reading is already satisfied
    assert m.metered_the_run() is False
    m.sample(12.0, "L/min", None, 100.0)  # gap 100 s > max_gap_s -> declined
    assert m.metered_the_run() is False
    m.sample(12.0, "L/min", None, 105.0)  # gap 5 s -> credited
    assert m.metered_the_run() is False  # ... but that earlier gap is not forgotten


def test_metered_the_run_counts_an_interval_credited_at_zero():
    # A rate of 0 across a live interval IS a measurement — it is what a genuinely dry
    # run looks like, and the caller must be able to write that run off.
    m = FlowMeter("lifetime", max_gap_s=20)
    m.sample(0.0, "L/min", None, 0.0)
    m.sample(0.0, "L/min", None, 5.0)
    assert m.delivered() == 0.0
    assert m.metered_the_run() is True


def test_metered_the_run_is_false_for_a_totalizer_below_its_baseline():
    # A counter that fell below its retained baseline and climbed back part of the way
    # has its climb credited NOWHERE, so the run was not accounted for.
    m = FlowMeter("lifetime")
    for i, v in enumerate([100.0, 60.0, 70.0, 80.0, 90.0]):
        m.sample(v, "L", "total_increasing", i * 5.0)
    assert m.delivered() == 0.0
    assert m.metered_the_run() is False
    # ... while a totalizer that merely holds its value HAS been accounted for, at 0 L.
    m2 = FlowMeter("lifetime")
    for i in range(4):
        m2.sample(100.0, "L", "total_increasing", i * 5.0)
    assert m2.delivered() == 0.0
    assert m2.metered_the_run() is True


def test_one_credited_interval_does_not_excuse_the_rest_of_the_run():
    # THE point of this accessor over a plain "priced anything" latch: an ordinary
    # interval at the start must not vouch for a window the meter then refuses to price.
    # A pump that takes a poll to build pressure gives exactly this shape.
    m = FlowMeter("lifetime", max_gap_s=20)
    m.sample(0.0, "L/min", None, 0.0)
    m.sample(0.0, "L/min", None, 5.0)  # one ordinary interval, credited at 0 L
    assert m.metered_the_run() is True
    m.sample(12.0, "L/min", None, 35.0)  # gap 30 s > max_gap_s: 12 L/min credited NOWHERE
    assert m.delivered() == 0.0
    assert m.metered_the_run() is False
    # Same shape on a totalizer: a flat interval, then a drop it keeps the baseline over.
    m2 = FlowMeter("lifetime")
    m2.sample(100.0, "L", "total_increasing", 0.0)
    m2.sample(100.0, "L", "total_increasing", 5.0)
    assert m2.metered_the_run() is True
    m2.sample(60.0, "L", "total_increasing", 10.0)
    assert m2.metered_the_run() is False
```

- [x] **Step 2: Add the three composite pins at the distributor level**

Append to `tests/test_distributor.py`:

```python
async def test_measure_window_an_early_priced_interval_does_not_excuse_the_window():
    # Eifel-Joe#53: the same three inputs as the three ..._is_not_dry tests above, each
    # with two ordinary reads in front of it. A "priced anything" latch is satisfied by
    # those two and writes the rest of the window off; the meter must account for the
    # WHOLE run. Measured: 418ab8a0 returned None for all three.
    # 1. a pump that takes a poll to build pressure, behind a flapping sensor
    c, d = _flow_host()
    seq = [0.0, 0.0] + [None, None, None, None, 12.0] * 2 + [None, None]
    it = iter(seq)
    c.hass.states.get = Mock(
        side_effect=lambda s: (lambda v: None if v is None else _state(v, "L/min"))(
            next(it, None)
        )
    )
    assert (await c._dist_measure_window(d, 70))[0] is None

    # 2. a totalizer that reads flat, then falls below its retained baseline and climbs
    c, d = _flow_host()
    vals = iter([100.0, 100.0, 60.0, 70.0, 80.0, 90.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals, 90.0), "L"))
    assert (await c._dist_measure_window(d, 50))[0] is None

    # 3. the same, with a per-run reset whose first post-reset read clears near_zero
    c, d = _flow_host()
    vals = iter([45.0, 45.0, 8.0, 20.0, 30.0, 40.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals, 40.0), "L"))
    assert (await c._dist_measure_window(d, 50))[0] is None
```

- [x] **Step 3: Run them and watch them fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_flow_meter.py tests/test_distributor.py -p _local_socket_unblock -q
```

Expected: the four `test_metered_the_run_*` tests fail with
`AttributeError: 'FlowMeter' object has no attribute 'metered_the_run'`, and
`test_measure_window_an_early_priced_interval_does_not_excuse_the_window` fails with
`assert 0.0 is None`.

- [x] **Step 4: Latch the declined readings and replace the accessor**

In `flow_metering.py`'s `__init__`, **replace** Task 4b's `_priced` line and its comment
block with the two flags and a much shorter note — the explanation belongs on the
accessor, and this spot is where `JustChr#174` adds its own field, so every line here is
conflict surface:

```python
        # Two halves of "did this meter account for the run?" — see metered_the_run.
        self._priced = False  # a reading was credited
        self._declined = False  # a post-seed reading was seen and NOT credited
```

In `_sample_rate`, give the existing max-gap comment its `else`:

```python
            if self._max_gap_s is None or dt <= self._max_gap_s:
                self._delivered += rate * dt / 60.0
                self._priced = True
            else:
                # gap too large (dropped/unavailable samples) — do not credit the
                # recovered rate across it (would over-credit); just advance the clock.
                # The reading was still SEEN, so the run is no longer fully accounted
                # for: whatever flowed across the gap is credited nowhere.
                self._declined = True
```

In `_sample_totalizer`, mark the kept-baseline drop — every path below the rising branch
credits nothing:

```python
        # A drop credits nothing, by either branch below, so the climb back up is lost
        # and the run is no longer fully accounted for.
        self._declined = True
        if litres <= self._near_zero():
```

And replace the `priced_anything()` accessor with:

```python
    def metered_the_run(self) -> bool:
        """True iff this meter accounted for the whole run: it credited at least one
        reading and declined none.

        Distinct from the have-a-reading state that ``delivered()`` gates on, which a
        single valve-open seed already satisfies. A meter can accept readings and
        credit none of them — a rate whose inter-sample gap exceeded ``max_gap_s``, a
        totalizer that fell below its retained baseline — and one credited interval
        does not vouch for the rest of the window.

        An interval credited at 0 L DOES count as accounted for: that is what a
        genuinely dry run looks like, and the caller has to be able to recognise it.

        Only a caller that writes a run OFF on the strength of a ``0.0`` needs this;
        ``delivered()``'s ``0.0`` contract is what the crediting callers price a dry run
        with. **Read it before ``end_rate_at``** — that method rewrites ``_delivered``
        afterwards (it can zero it, and it can add a bounded tail) and deliberately does
        not touch either flag, so the two stop agreeing once it has run.
        """
        return self._priced and not self._declined
```

- [x] **Step 5: Switch the guard and correct its comment**

In `_dist_measure_window`, change `not meter.priced_anything()` to
`not meter.metered_the_run()`, and in the comment block above it replace the `Fix:`
paragraph's first sentence and add the missing case. The block must stop claiming that
"priced anything" is the test, and must name the fourth input:

```python
        # Fix: ask the meter whether it accounted for the RUN, not whether it ever
        #   priced anything. metered_the_run() is false for every case above and for a
        #   fourth the first attempt missed — two ordinary reads in front of any of them
        #   latch a plain "priced" flag and write the rest of the window off. It is true
        #   for a dry run that was really measured (an interval credited at 0 L counts).
        #   saw_reset() stays beside it and is NOT redundant: a totalizer reading
        #   100,100,5,7 credits the flat interval and declines nothing, so only
        #   saw_reset() catches the reset after it. The classic runner makes the same
        #   diversion before its own dry branch (irrigation.py:1535).
```

Also correct `irrigation.py:1536` to `irrigation.py:1535` wherever the block cites it —
`:1535` is the `if measured <= 0 and meter.saw_reset():` itself; `:1536` is its first
comment line.

- [x] **Step 6: Verify**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_flow_meter.py tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_self_closing.py tests/test_observed_watering.py -p _local_socket_unblock -q
```

Expected: **all pass.** The prototype measured **266 passed** across these five files
with one fewer test than this task adds, so expect **268**: `test_flow_meter.py` 48 → 49
(three rewritten in place, one added), `test_distributor.py` 62 → 63.

`grep -rn "priced_anything" custom_components/ tests/` must come back **empty** — the old
accessor is replaced, not left beside the new one.

- [x] **Step 7: Lint and commit**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/flow_metering.py custom_components/irrigation_plus/distributor.py tests/test_flow_meter.py tests/test_distributor.py
git commit -F - <<'EOF'
fix(flow): one credited interval does not vouch for the whole run

Eifel-Joe#53. priced_anything() latched on the first credited reading, so two
ordinary reads in front of any of the three inputs it was built for masked the
rest of the window: a pump that takes a poll to build pressure behind a flapping
sensor measured 0.0 across 10 L, and both totalizer shapes did the same.

Replaced by metered_the_run() -- credited at least one reading and declined none.
An interval credited at 0 L still counts, so a genuinely dry run is still
recognised; the three composites now fall back to time-based as they did before
the branch. saw_reset() stays: 100,100,5,7 declines nothing.

<ATTRIBUTION>
EOF
```

Then tick Task 4c's seven checkboxes and `git commit --amend --no-edit`.

---

### Task 11: A dry run says so in the log

**Why.** The dry branch is completely silent: no warning, no problem sensor, no chip, no
event (spec D2 deliberately raises no zone fault, because nothing on the distributor path
ever clears one). A user whose notifications are bound to `zone_problem`, or who does not
open the History tab per zone, learns nothing except that "Last irrigation" stopped
advancing.

This codebase has already answered this question twice, in the two other paths that
cannot raise a fault, and both chose a `_LOGGER.warning` — with the reason written down:

- `self_closing.py:356` — *"a persistently dead/misconfigured sensor would otherwise
  degrade to time-based SILENTLY. Surface it ONCE per run at finalize (the
  fire-and-forget run has no dry fault to raise)."*
- `observed_watering.py::_observed_flag_dead_sensor` — *"Log-only by design — a zone has
  no per-run transient problem flag, and self-closing does the same."*

Both of those only degrade to a time estimate. This branch writes the run **off**, a
stronger statement that deserves at least as much visibility. `_LOGGER` is already in the
module.

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py` (the dry branch)
- Test: `tests/test_distributor_dispatch.py`

- [x] **Step 1: Write the failing test**

```python
async def test_sweep_warns_when_it_writes_a_member_run_off(caplog):
    """Eifel-Joe#53: the dry branch raises no zone fault (spec D2 — nothing on this path
    ever clears one), so a WARNING is the only thing that reaches a user who is not
    reading the per-zone history. The two sibling paths that cannot raise a fault log
    one for the weaker case of merely degrading to a time estimate."""
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._dist_measure_window = AsyncMock(return_value=(0.0, 60, False))
    c._dist_credit_zone = AsyncMock()
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
    with caplog.at_level(logging.WARNING):
        await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert any(
        r.levelname == "WARNING" and "no water" in r.message.lower()
        for r in caplog.records
    ), [r.message for r in caplog.records]
```

`import logging` may already be at the top of the test file — check before adding it.

- [x] **Step 2: Run it and watch it fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py::test_sweep_warns_when_it_writes_a_member_run_off -p _local_socket_unblock -v
```

Expected: **FAIL** — the assertion's list of captured messages contains no such warning.

- [x] **Step 3: Log it, once, on the dry branch**

Directly after the `dry = …` assignment:

```python
                if dry:
                    # The run is recorded FAILED and credited nothing, and spec D2
                    # raises no zone fault here because NOTHING on the distributor path
                    # clears one (all five _clear_zone_fault callers sit in the classic
                    # runner's own machinery), so a fault would stay red after the
                    # cistern was refilled. A warning is therefore the only thing that
                    # reaches a user who is not reading the per-zone run log.
                    # NOT-TO-DO: do not promote this to a zone fault without adding a
                    #   clearing site to this path first — see spec D2.
                    # The two sibling paths that cannot raise a fault log the same way
                    # for the weaker case of merely degrading to a time estimate
                    # (self_closing.py:356, observed_watering's dead-sensor flag).
                    # siehe tests/test_distributor_dispatch.py::
                    #   test_sweep_warns_when_it_writes_a_member_run_off
                    _LOGGER.warning(
                        "Distributor '%s' outlet %s (zone %s): the flow meter watched "
                        "the whole %.0f s window and measured no water; recording the "
                        "run as failed and crediting nothing",
                        distributor.get("name"),
                        current,
                        zid,
                        actual_seconds,
                    )
```

Check the surrounding scope for the exact names of the outlet and zone variables
(`current`, `zid`) before writing them in — use whatever that block already holds.

- [x] **Step 4: Verify**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py -p _local_socket_unblock -q
```

Expected: all pass, `test_distributor_dispatch.py` 80 → 81.

- [x] **Step 5: Lint and commit**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/distributor.py tests/test_distributor_dispatch.py
git commit -F - <<'EOF'
feat(distributor): say in the log that a member run was written off

Eifel-Joe#53. The dry branch raises no zone fault on purpose -- nothing on this
path clears one -- which left it entirely silent: no warning, no sensor, no
event. The two sibling paths that also cannot raise a fault both log a warning
for the weaker case of merely degrading to a time estimate.

<ATTRIBUTION>
EOF
```

Then tick Task 11's five checkboxes and `git commit --amend --no-edit`.
---

## Measured results

### Suite, on the finished branch

```
7 failed, 3274 passed, 9 skipped, 10 warnings, 349 errors in 331.13s
```

Baseline was `3254` passed on `418ab8a0`, so **+20**: `test_distributor.py` 52 -> 63,
`test_distributor_dispatch.py` 76 -> 81, `test_flow_meter.py` 45 -> 49. (One existing
test was inverted in place rather than added, and Task 4c rewrote three of Task 4b's.)
The 356 non-passing names are **`diff`-identical** to `baseline-names.txt`:

```
$ diff baseline-names.txt after-names.txt && echo IDENTISCH
IDENTISCH
```

`uvx black --check` -> 69 files unchanged. `uvx ruff check` -> All checks passed!

### Mutation matrix — final guard

Driver: `D:/Entwicklung/HASI/issue53-work/mutate3.py`. Every mutation reverted with
`git checkout -- <file>`; the driver asserts a clean tree before each row and **exits**
if one is dirty, so a silently failed revert cannot corrupt the next mutation. It did
refuse once, correctly, when a change was still uncommitted.

| # | mutation | outcome |
|---|---|---|
| M1 | remove the guard entirely | **KILLED (7)** — all seven `..._is_not_dry` / `..._does_not_excuse_the_window` tests |
| M2a | drop `_priced` from `_sample_rate` | **KILLED (3)** |
| M2b | drop `_priced` from `_sample_totalizer` | **KILLED (3)** |
| M2c | drop `_declined` from `_sample_rate` | **KILLED (3)** |
| M2d | drop `_declined` from `_sample_totalizer` | **KILLED (3)** |
| M3a | guard's `<= 0` → `== 0` | **SURVIVED, as predicted** — unreachable: a meter that accounted for nothing has delivered exactly `0.0` |
| M3b | sweep's `dry` `<= 0` → `== 0` | **KILLED (1)** `test_sweep_treats_a_negative_measurement_as_dry` |
| M3c | `metered_the_run()` → `_delivered > 0` | **KILLED (6)** |
| M3d | `metered_the_run()` → `self._priced` alone | **KILLED (4)** — this is exactly the Task 4b defect, now pinned |
| M4 | drop `RUN_RESULT_FAILED if dry` | **KILLED (3)** |
| M5 | drop `and not dry` from the calibration gate | **KILLED (1)** |
| M6 | drop the `isfinite` guard | **KILLED (1)** |
| M7 | `measured_l=measured` instead of `0.0 if dry` | **KILLED (1)** |
| M8 | downgrade the dry warning to `debug` | **KILLED (1)** |

**Thirteen killed, one survived by construction.**

### What the matrix found: a redundant term

An earlier round had a second guard term, `or meter.saw_reset()`, and **its mutation
killed nothing.** That was not a missing test but a structural fact: `_saw_reset` is
assigned in exactly one place, inside `_sample_totalizer`'s near-zero branch, and
`_declined` is set unconditionally just above the `if` that guards it — so
`saw_reset()` implies `not metered_the_run()`. The term was **removed** rather than a
test invented to justify it, and a `NOT-TO-DO` at the `_declined` assignment records
that a caller depends on the two staying together (`bd7930f6`).

This is the recorded trap working as intended: *a mutation that kills nothing may be the
wrong mutation — check whether it can reach the behaviour at all before suspecting the
test.* Here it could not, and the code was what needed changing.

### Defects this plan itself carried, found during execution

1. **Tasks 2–4's witness was unsound.** `last_live` records that `_dist_read_flow`
   returned a tuple, not that the meter credited anything. Three measured inputs
   regressed against the base commit. Replaced in Task 4b (spec §4.1).
2. **Task 4b's replacement was still too weak.** `priced_anything()` latched on the
   first credited reading, so two ordinary reads in front of any of those three inputs
   masked the rest of the window. Replaced in Task 4c by `metered_the_run()`.
3. **Task 5's `sed` was incomplete.** Its pattern required the second lambda parameter to
   be named `s`; three further stubs use `w` (one in `test_distributor_dispatch.py`, two
   in `test_distributor_cycle.py`). The `8	8` numstat and the grep count of `8` both
   confirmed the substitution did what it claimed — neither could show the pattern was
   too narrow.
4. **Task 8's test was vacuous as written.** It used `_dist(id=0, current_outlet=1)`,
   whose default `watering_mode` is `CLASSIC`, which makes `can_stop` unconditionally
   true — so the `not can_stop` gate short-circuits and the calibration check is never
   reached, dry or not. It passed *before* the fix. Corrected to
   `watering_mode=const.WATERING_MODE_SERVICE` and genuine RED confirmed first.
5. **The plan's own next-step instruction was inverted.** It told a future session to
   write into the PR body that the change avoids `flow_metering.py` — in a diff where
   that file is visibly modified. Found by the final review.
6. **M3a's recorded reasoning over-claimed.** `_delivered` has five write sites and the
   two inside `end_rate_at` latch neither flag, so the invariant holds on this path only
   (the distributor never calls it; `self_closing.py:350` is its sole caller). Scoped in
   `metered_the_run()`'s docstring and in the M3a row.

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
   `Eifel-Joe#55` owns the cycle-level question, and — **the part that changed
   mid-branch** — that `flow_metering.py` **is** touched and will therefore conflict
   with the maintainer's own open `JustChr#174`, which edits the same `__init__` field
   list. Say so plainly rather than letting him find it: the first design avoided that
   file and was measured as a regression (spec §4.1), so the conflict is the lesser
   evil. Also report, without fixing, that `#174`'s own `saw_reading_after_open()` has
   the same hole, and that `metered_the_run()` must be read **before** `end_rate_at`
   — which `#174`'s path does call.
