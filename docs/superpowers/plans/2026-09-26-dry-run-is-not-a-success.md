# Plan 2 of 2 — A run that delivered nothing is not a success (`Eifel-Joe#4`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A self-closing run whose live flow sensor measured 0.0 litres over the
whole window is reported and not credited, instead of being booked as a
completed run for its full planned volume.

**Architecture:** Delete the collapse. `_sc_finish_flow` stops turning a
live-but-dry `0.0` into `None` and returns it raw, the way
`_observed_finish_flow` already does. The early-stop path maps it back for
itself in one line; the completion path treats it as the failure it is. The
bucket reversal then falls out of the existing measured branch —
`pre_bucket + 0 = pre_bucket` — with no new arithmetic.

**Tech Stack:** Python 3.12, pytest + pytest-homeassistant-custom-component,
black, ruff.

**Spec:** `docs/superpowers/specs/2026-09-26-self-closing-fault-lifecycle-design.md` §4, §5.

**Stacks on Plan 1** (`docs/superpowers/plans/2026-09-26-fault-pairing-and-clearing.md`).
Task 2 below edits the `_clear_zone_fault` line Plan 1 Task 2 added — do not
start this plan until that one is committed and green.

**Base commit:** `418ab8a0` + Plan 1. **Baseline after Plan 1:** 7 failed /
3258 passed / 9 skipped / 349 errors.

**Test command (from this worktree — there is no local `.venv` here):**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/self_closing.py` | flow finalisation + run finalisation | `_sc_finish_flow` returns `d` raw; `async_stop_self_closing` insulates itself; `_sc_finish_run` grows the dry branch |
| `tests/test_self_closing.py` | self-closing behaviour | 7 new tests |

No new constant, no new record field, no migration. `const.FAULT_FLOW_NEVER_STARTED`
already exists and is what the classic runner uses for this exact state.

---

### Task 1: A live-but-dry meter says 0.0, and the early stop is insulated from it

Both halves ship together: removing the collapse without the early-stop line
would make a run stopped five seconds in credit zero litres.

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:365` and `:950`
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the two failing tests**

Append to `tests/test_self_closing.py`:

```python
async def test_a_live_but_dry_meter_reports_zero_not_nothing(monkeypatch):
    """A counter that never moves over a whole run is not a missing
    measurement: the meter was alive and integrated nothing - a dry cistern, a
    closed main, a blocked filter. Collapsing that to None made the caller fall
    back to the time-based volume and credit a zone that received nothing."""
    import custom_components.irrigation_plus.self_closing as scmod

    monkeypatch.setattr(scmod, "async_track_time_interval", Mock(return_value=Mock()))

    c = _coord()
    zone = _zone(
        **{
            const.ZONE_FLOW_SENSOR: "sensor.beet_flow",
            const.ZONE_FLOW_COUNTER_TYPE: const.FLOW_COUNTER_LIFETIME,
        }
    )
    store_zone = dict(zone)
    c.store.get_zone = Mock(side_effect=lambda zid: store_zone)
    current = {"st": _flow_state(0)}
    c.hass.states.get = Mock(side_effect=lambda eid: current["st"])

    await c._sc_start_flow_sampling(zone)
    for at in (15.0, 30.0, 45.0):
        c._sc_sample_flow(2, at)  # the counter never moves

    measured, _end = c._sc_finish_flow(2)

    assert measured == 0.0, "a live meter that integrated nothing must say 0.0"


async def test_an_early_stop_with_a_dry_meter_still_credits_time_based():
    """A run stopped five seconds in reads 0.0 L because the water has not
    reached the sensor yet, not because the cistern is empty. The completion
    path treats a 0.0 as a failure; this one must not - the same reason the
    classic runner gates its dry branch on `not stopped` (irrigation.py:1580)."""
    c = _coord()
    run = {
        const.RUN_ZONE_ID: 2,
        const.RUN_STARTED: "2026-06-30T08:00:00+00:00",
        const.RUN_PLANNED_SECONDS: 600.0,
        const.RUN_PLANNED_MM: 4.0,
        const.RUN_PRE_BUCKET: -5.0,
        const.RUN_CREDITED: True,
    }
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [run]}
    )
    c.store.get_zone = Mock(return_value=_zone(**{const.ZONE_BUCKET: -1.0}))
    c._sc_finish_flow = Mock(return_value=(0.0, {}))
    c._sc_elapsed = Mock(return_value=300.0)
    c._timed_volume_l = Mock(return_value=10.0)
    # Consulted only by the measured branch, which a stop must not take here.
    c._credited_depth_native = Mock(return_value=99.0)

    await c.async_stop_self_closing(2)

    assert c._record_run.await_args.kwargs["volume_l"] == 10.0
    c._credited_depth_native.assert_not_called()
```

- [x] **Step 2: Run them and confirm both fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q -k "live_but_dry or early_stop_with_a_dry_meter"
```

Expected: **2 failed.**

- The first on `assert None == 0.0 : a live meter that integrated nothing must
  say 0.0`.
- The second on `assert 0.0 == 10.0`. It stubs `_sc_finish_flow` to `(0.0, {})`
  itself, so it does not wait for the first fix: today's
  `async_stop_self_closing` takes the measured branch on that `0.0`, credits a
  measured zero and consults `_credited_depth_native`. Both of its assertions
  fail.

Record which assertion each one actually failed on.

- [x] **Step 3: Write the implementation**

(a) In `self_closing.py`, `_sc_finish_flow`, replace the final two lines:

```python
        measured = d if (d is not None and d > 0) else None
        return measured, self._flow_learn_end_changes(zone, meter, open_start_l)
```

with:

```python
        # Wurzel: 0.0 is an ANSWER, not a missing one - the meter was alive the
        #   whole run and integrated nothing. Collapsed to None it was
        #   indistinguishable from a dead sensor, so _sc_finish_run fell back to
        #   the time-based volume: a zone that received nothing had its bucket
        #   credited in full, its litres added to water_used_total and its run
        #   logged as completed. The dry-cistern case, silent.
        # Fix: return d as the meter reported it. None still means no numeric
        #   reading was ever seen; 0.0 means a live meter measured nothing.
        #   _observed_finish_flow already returns it this way, decided after the
        #   phantom-open incident - the two flow paths now say the same thing
        #   with the same value.
        # NOT-TO-DO: do not read a falsy `measured` as "no measurement" at any
        #   caller. That is the same collapse one level up, and it re-opens this
        #   bug. The two callers that care each say so at their own line.
        # siehe test_self_closing.py::
        # test_a_live_but_dry_meter_reports_zero_not_nothing
        return d, self._flow_learn_end_changes(zone, meter, open_start_l)
```

(b) In `self_closing.py`, `async_stop_self_closing`, immediately after the
existing `measured, end_changes = self._sc_finish_flow(zone_id, run)`:

```python
        # An early stop reads 0.0 for a reason that is not a dry cistern: the
        # water has not reached the sensor yet. _sc_finish_flow no longer
        # collapses that (see its return), so this path collapses it for itself
        # and keeps the time-based credit below byte-identical to before.
        # The completion twin does the opposite and treats it as the failure it
        # is - _sc_finish_run's dry branch. Same split as the classic runner,
        # whose dry branch is gated on `not stopped` (irrigation.py:1580).
        # siehe test_self_closing.py::
        # test_an_early_stop_with_a_dry_meter_still_credits_time_based
        if measured is not None and measured <= 0:
            measured = None
```

- [x] **Step 4: Run the two tests, then the whole file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q
```

Expected: the whole file passes. **If any pre-existing test turns red here, read
it before touching it** — the question is whether it models a state the code can
actually reach (memory `narrowing-exposes-impossible-fixtures`). Record each red
test and the verdict.

- [x] **Step 5: Run every file that exercises a flow path**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_credit_ceiling.py tests/test_flow_meter.py tests/test_flow_calibration.py tests/test_service_watch.py tests/test_opensprinkler.py tests/test_batch.py -p _local_socket_unblock -q
```

Expected: all pass.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(flow): a live meter that measured nothing says 0.0, not nothing

_sc_finish_flow collapsed a live-but-dry 0.0 into None, which is what a
DEAD sensor returns. The caller could not tell them apart and fell back
to the time-based volume for both, so the dry-cistern case - valve
reported open, no water moved - credited the bucket in full, added the
planned litres to water_used_total and logged a completed run. Silently:
the warning beside it is gated on `d is None`.

Returned raw now, as _observed_finish_flow has returned it since the
phantom-open incident. The early-stop path collapses it for itself in
one line and is unchanged: a run stopped five seconds in reads 0.0
because the water has not reached the sensor, which is the same reason
the classic runner gates its dry branch on `not stopped`.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: A dry completion is reported as the failure it is

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (`_sc_finish_run`)
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the two failing tests**

Append to `tests/test_self_closing.py`:

```python
def _dry_finish_coord():
    """A self-closing run about to finalise with a live meter that read 0.0."""
    c = _coord()
    c._set_zone_fault = Mock()
    c._clear_zone_fault = Mock()
    c.async_write_watered_bucket = AsyncMock()
    c._flow_calibration_check = AsyncMock()
    c._sc_finish_flow = Mock(return_value=(0.0, {}))
    c._credited_depth_native = Mock(return_value=0.0)
    c._timed_volume_l = Mock(return_value=20.0)  # must NOT reach the record
    c.store.get_zone = Mock(
        return_value=_zone(
            **{
                const.ZONE_BUCKET: 0.0,  # the optimistic open credit, satisfied
                const.ZONE_MAXIMUM_BUCKET: 24.0,
                const.ZONE_LINKED_ENTITY: "valve.beet",
            }
        )
    )
    c.store.async_get_config = AsyncMock(
        return_value={
            const.CONF_ACTIVE_VALVE_RUNS: [
                {
                    const.RUN_ZONE_ID: 2,
                    const.RUN_PLANNED_SECONDS: 600.0,
                    const.RUN_PRE_BUCKET: -2.0,
                }
            ]
        }
    )
    return c


async def test_a_dry_run_is_recorded_as_a_failure_and_raises_the_fault():
    """The leading case of Eifel-Joe#4: a dry cistern behind a live sensor. The
    run was credited optimistically at open and measured nothing, so it is a
    failed run - the same verdict and the same constant the classic metered
    runner reaches for this state (irrigation.py:1586)."""
    c = _dry_finish_coord()

    await c._sc_finish_run(2)

    kwargs = c._record_run.await_args.kwargs
    assert kwargs["result"] == const.RUN_RESULT_FAILED
    assert kwargs["detail"] == const.FAULT_FLOW_NEVER_STARTED
    assert kwargs["volume_l"] == 0.0
    c._set_zone_fault.assert_called_once_with(2, const.FAULT_FLOW_NEVER_STARTED)
    # The optimistic credit is reversed to the level the run started from, so
    # the deficit survives and the zone comes due again.
    c.async_write_watered_bucket.assert_awaited_once_with(2, -2.0)


async def test_a_dry_run_does_not_clear_the_zone_fault_it_just_raised():
    """The one line Eifel-Joe#4 shares with Eifel-Joe#3: a completed run clears
    the fault, and a dry one must not - it would put out the lamp it just lit.
    The chain and the deferred calculation still run: _sc_finish_run is a link,
    unlike the classic runner, and returning early here strands the cycle."""
    c = _dry_finish_coord()
    c._chain_advance_for_run = AsyncMock()
    c.async_run_deferred_calculation = AsyncMock()

    await c._sc_finish_run(2)

    c._clear_zone_fault.assert_not_called()
    c._chain_advance_for_run.assert_awaited_once()
    c.async_run_deferred_calculation.assert_awaited_once()
```

- [x] **Step 2: Run them and confirm both fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q -k "dry_run_is_recorded or dry_run_does_not_clear"
```

Expected: **2 failed.** The first on `'completed' != 'failed'`, the second on
`Expected '_clear_zone_fault' to not have been called. Called 1 times`.

- [x] **Step 3: Write the implementation**

In `_sc_finish_run`, after the existing
`measured, end_changes = self._sc_finish_flow(zone_id, run)` block (the
`if end_changes:` update), insert:

```python
        # A live meter that integrated nothing across the whole window: the
        # valve reported open and no water moved. Not a missing measurement,
        # which is None and still falls back to the time-based volume below.
        dry = measured is not None and measured <= 0
```

The bucket branch below needs **no change**: for a dry run
`pre_bucket + self._credited_depth_native(zone, 0.0)` is `pre_bucket`, and the
clamp cannot move it because the pre-run level was at or below the run's ceiling
by construction. The absolute reconcile that branch already performs *is* the
reversal.

Then replace Plan 1's unconditional clear with:

```python
        if dry:
            # The classic runner's verdict for this exact state, with its
            # constant, so the run log, the problem sensor and a user's
            # automation read one vocabulary (irrigation.py:1586 / :2123).
            # NOT-TO-DO: no early return. The classic runner may return out of
            #   its dry branch because it is not a link in a chain;
            #   _sc_finish_run is, and leaving here strands the rest of the
            #   cycle and a deferred calculation with it.
            # siehe test_self_closing.py::
            # test_a_dry_run_does_not_clear_the_zone_fault_it_just_raised
            self._set_zone_fault(zone_id, const.FAULT_FLOW_NEVER_STARTED)
            self._fire_zone_problem(
                zone_id,
                zone,
                zone.get(const.ZONE_LINKED_ENTITY),
                const.FAULT_FLOW_NEVER_STARTED,
            )
        else:
            self._clear_zone_fault(zone_id)
```

In the `_record_run(` call, change the `result=` line and add a `detail=` line
directly below `actual_s=`:

```python
            result=(const.RUN_RESULT_FAILED if dry else const.RUN_RESULT_COMPLETED),
```
```python
            detail=const.FAULT_FLOW_NEVER_STARTED if dry else None,
```

And in the `_sc_fire(const.EVENT_IRRIGATE_FINISHED, ...)` payload, replace
`"problems": [],` with:

```python
                "problems": (
                    [{"zone_id": zone_id, "reason": const.FAULT_FLOW_NEVER_STARTED}]
                    if dry
                    else []
                ),
```

- [x] **Step 4: Run the tests, then the file**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q
```

Expected: the whole file passes, including Plan 1's
`test_a_completed_run_clears_the_zone_fault` — a measured 2.26 L is not dry, so
it still takes the `else`.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a run that delivered nothing is a failed run

With the collapse gone, _sc_finish_run can finally see the case it was
mis-booking: the valve reported open for its whole window and the live
flow sensor measured 0.0 L. It was recorded completed, for the full
planned volume, with the bucket left satisfied - so a zone behind a dry
cistern looked watered and was not due again until the weather reopened
it.

Recorded failed now, with FAULT_FLOW_NEVER_STARTED - the classic metered
runner's constant for the identical state, so the run log, the problem
sensor and a user automation read one vocabulary. The bucket reversal
needs no new arithmetic: the measured branch reconciles absolutely from
RUN_PRE_BUCKET, and pre_bucket + 0 is pre_bucket.

No early return, deliberately. The classic runner can return out of its
dry branch; _sc_finish_run is a link in the chain, and leaving here
would strand the rest of the cycle.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: A dry run does not feed the calibration advisory

`_flow_calibration_check`'s own guard is `measured_l is None`
(`irrigation.py:1268`). A `0.0` now walks straight past it and is priced as an
observed rate of 0 L/min against the configured throughput.

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (`_sc_finish_run`)
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_self_closing.py`:

```python
async def test_a_dry_run_is_not_a_calibration_sample():
    """_flow_calibration_check short-circuits on `measured_l is None`, so until
    Task 1 a dry run never reached it. A 0.0 walks past that guard and would be
    banked as an observed rate of 0 L/min - dragging the mean down until the
    advisory recommends a throughput the hardware never had."""
    c = _dry_finish_coord()

    await c._sc_finish_run(2)

    c._flow_calibration_check.assert_not_awaited()
```

- [x] **Step 2: Run it and confirm it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_dry_run_is_not_a_calibration_sample -p _local_socket_unblock -q
```

Expected: **1 failed**, `Expected '_flow_calibration_check' to not have been
awaited. Awaited 1 times.`

- [x] **Step 3: Write the implementation**

In `_sc_finish_run`, wrap the existing `await self._flow_calibration_check(...)`
call (keeping its long existing comment block above it untouched):

```python
        # NOT a sample when the run was dry: this prices litres over minutes,
        # and 0 L over a full window reads as a real rate of 0 L/min. Its own
        # `measured_l is None` guard used to catch this case for free, and
        # stopped the moment 0.0 became a value (see _sc_finish_flow).
        if not dry:
            await self._flow_calibration_check(
                zone, measured, planned_s if actual_s is None else actual_s
            )
```

- [x] **Step 4: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_flow_calibration.py tests/test_flow_cal_sample_floor.py -p _local_socket_unblock -q
```

Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(flow-cal): a dry run is not a throughput sample

_flow_calibration_check short-circuits on `measured_l is None`, which
caught the dry case for free while 0.0 was being collapsed. Now that 0.0
is a value, it walks past that guard and is banked as an observed rate of
0 L/min - pulling the mean down run after run until the advisory
recommends a throughput the hardware never had.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Without a pre-run anchor, leave the bucket alone

The existing measured branch takes `float(run.get(const.RUN_PRE_BUCKET) or 0)`.
For a record persisted before that field existed, a dry run would write the
bucket to `0` — marking the zone satisfied and erasing the very deficit this
plan exists to keep.

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (`_sc_finish_run`)
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_self_closing.py`:

```python
async def test_a_dry_run_without_a_pre_bucket_anchor_leaves_the_bucket_alone():
    """A run persisted before RUN_PRE_BUCKET existed (an upgrade mid-run) has no
    level to reverse to. `or 0` would write the bucket to 0 and mark the zone
    satisfied - erasing the deficit this whole fix exists to keep. Leave the
    optimistic credit where it stands; the fault and the failed record still
    carry the news."""
    c = _dry_finish_coord()
    c.store.async_get_config = AsyncMock(
        return_value={
            const.CONF_ACTIVE_VALVE_RUNS: [
                {const.RUN_ZONE_ID: 2, const.RUN_PLANNED_SECONDS: 600.0}
            ]
        }
    )

    await c._sc_finish_run(2)

    c.async_write_watered_bucket.assert_not_awaited()
    # Still reported, which is the half that does not depend on the anchor.
    c._set_zone_fault.assert_called_once_with(2, const.FAULT_FLOW_NEVER_STARTED)
    assert c._record_run.await_args.kwargs["result"] == const.RUN_RESULT_FAILED
```

- [x] **Step 2: Run it and confirm it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_dry_run_without_a_pre_bucket_anchor_leaves_the_bucket_alone -p _local_socket_unblock -q
```

Expected: **1 failed**, `Expected 'async_write_watered_bucket' to not have been
awaited. Awaited 1 times.` (it was awaited with `(2, 0.0)` — the erasure).

- [x] **Step 3: Write the implementation**

In `_sc_finish_run`, directly below the `dry = ...` line from Task 2:

```python
        # The reversal needs the level the run started from. A record persisted
        # before RUN_PRE_BUCKET existed (an upgrade mid-run) has none, and the
        # `or 0` below would then write the bucket to 0 - marking the zone
        # SATISFIED and erasing the deficit this fix exists to keep, which is
        # worse than leaving the optimistic credit in place. The fault and the
        # failed record do not depend on the anchor and still fire.
        # siehe test_self_closing.py::
        # test_a_dry_run_without_a_pre_bucket_anchor_leaves_the_bucket_alone
        no_anchor = dry and run.get(const.RUN_PRE_BUCKET) is None
```

and change the bucket branch's condition and add its sibling:

```python
        if measured is not None and not no_anchor:
            pre_bucket = float(run.get(const.RUN_PRE_BUCKET) or 0)
            nb = pre_bucket + self._credited_depth_native(zone, measured)
            nb = min(nb, run_credit_ceiling(run, zone))
            await self.async_write_watered_bucket(zone_id, nb)
            zone = self.store.get_zone(zone_id) or zone
            volume_l = measured
        elif measured is not None:
            volume_l = measured  # 0.0; the bucket stays where the open put it
        else:
            volume_l = self._timed_volume_l(zone, planned_s)
```

(The first branch's body is unchanged — only its condition, plus the new `elif`.)

- [x] **Step 4: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_credit_ceiling.py -p _local_socket_unblock -q
```

Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a dry run with no pre-run anchor keeps its bucket

The measured branch reads RUN_PRE_BUCKET with `or 0`. For a run
persisted before that field existed, reversing a dry run would have
written the bucket to 0 - marking the zone satisfied and erasing exactly
the deficit this fix exists to keep, which is worse than leaving the
optimistic credit alone. The fault and the failed record do not depend on
the anchor and still fire.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Pin that a resumed run is never called dry

`Eifel-Joe#4` asked for a marker that the sampler ran the whole run, so a
restart could not be mistaken for a dry cistern. Decision D5 declines it,
because the verdict is taken where a resumed run has no meter at all. That is an
argument. This is the measurement.

**Files:**
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the test**

Append to `tests/test_self_closing.py`:

```python
async def test_a_run_resumed_after_a_restart_is_never_called_dry():
    """Eifel-Joe#4 asked for a marker that the sampler ran the whole run. It is
    not built, and this is why: _sc_meters is in-memory only, and
    async_resume_self_closing_runs re-arms the cleanup, the master hold and the
    valve watcher but never _sc_start_flow_sampling. So the pop in
    _sc_finish_flow finds nothing and the function is out before `d` is read -
    a resumed run cannot be dry.

    The marker would be needed if the verdict were taken at the caller on
    `measured is None`. Mutate `dry` to `not measured` and this test goes red,
    which is the whole argument in one assertion. If it ever fails for another
    reason, build the marker."""
    c = _coord()
    c._set_zone_fault = Mock()
    c._flow_calibration_check = AsyncMock()
    c._timed_volume_l = Mock(return_value=20.0)
    c.store.get_zone = Mock(
        return_value=_zone(
            **{const.ZONE_FLOW_SENSOR: "sensor.beet_flow", const.ZONE_BUCKET: -2.0}
        )
    )
    c.store.async_get_config = AsyncMock(
        return_value={
            const.CONF_ACTIVE_VALVE_RUNS: [
                {
                    const.RUN_ZONE_ID: 2,
                    const.RUN_PLANNED_SECONDS: 600.0,
                    const.RUN_PRE_BUCKET: -2.0,
                }
            ]
        }
    )
    # The restart: a fresh process has an empty meter map, and nothing on the
    # resume path refills it. _sc_finish_flow is NOT stubbed here - the real one
    # is the thing under test.
    assert c._sc_meters() == {}

    await c._sc_finish_run(2)

    c._set_zone_fault.assert_not_called()
    assert c._record_run.await_args.kwargs["result"] == const.RUN_RESULT_COMPLETED
```

- [x] **Step 2: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_run_resumed_after_a_restart_is_never_called_dry -p _local_socket_unblock -q
```

Expected: **1 passed.** A pin, so its RED is the mutation in Step 3.

- [x] **Step 3: Prove the pin bites**

Temporarily change the `dry` line in `_sc_finish_run` from

```python
        dry = measured is not None and measured <= 0
```

to

```python
        dry = not measured
```

— the exact mistake the marker was meant to guard against. Re-run:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_run_resumed_after_a_restart_is_never_called_dry -p _local_socket_unblock -q
```

Expected: **1 failed**, `Expected '_set_zone_fault' to not have been called.
Called 1 times.` Revert the line.

- [x] **Step 4: Confirm the mutation is reverted**

```bash
git diff --stat custom_components/irrigation_plus/self_closing.py
```

Expected: **no output.**

- [x] **Step 5: Commit**

```bash
git add tests/test_self_closing.py
git commit -F - <<'EOF'
test(self-closing): pin that a resumed run is never called dry

Eifel-Joe#4 asked for a marker that the sampler ran the whole run, so a
restart could not read as a dry cistern. It is not built, because the
verdict is taken where a resumed run has no meter at all: _sc_meters is
in-memory, async_resume_self_closing_runs never restarts the sampler, and
_sc_finish_flow returns before `d` is read. That was an argument; this is
the measurement. Writing the verdict as `not measured` - the mistake the
marker would have covered - turns it red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Gates

- [x] **Step 1: Full suite**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no > /d/Entwicklung/HASI/issue3-work/after-plan2.txt 2>&1; tail -3 /d/Entwicklung/HASI/issue3-work/after-plan2.txt
```

Expected: `7 failed, 3265 passed, 9 skipped, ..., 349 errors` - Plan 1's 3258
**+7**, being exactly the seven new tests.

**MEASURED: exactly that** - `7 failed, 3265 passed, 9 skipped, 10 warnings,
349 errors in 272.19s`, first run, no regression to chase.

- [x] **Step 2: Diff the failure names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue3-work && grep -E "^(FAILED|ERROR) " after-plan2.txt | sed 's/ - .*$//' | sort > after-plan2-names.txt && diff baseline-names.txt after-plan2-names.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`.

**MEASURED: `IDENTICAL`, 356 names both sides.**

- [x] **Step 3: Lint**

```bash
cd /d/Entwicklung/HASI/issue3-work/wt && uvx black --check custom_components/irrigation_plus/ && uvx ruff check custom_components/irrigation_plus/
```

Expected: `68 files would be left unchanged.` and `All checks passed!`

**MEASURED: `69 files would be left unchanged.` and `All checks passed!`** -
69 because of `actuate.py`, added upstream after this plan was written.

- [x] **Step 4: Mutation matrix**

Apply, run, revert. One at a time, reverting with `git checkout -- <file>`
(Plan 1 measured why a reverse text replacement is not safe). Driver:
`D:/Entwicklung/HASI/issue3-work/matrix2.py`.

**MEASURED - all eight killed, three counts differing from the prediction:**

| # | measured | killed |
|---|---|---|
| M1 | **1 failed** (predicted >=4) | `..._a_live_but_dry_meter_reports_zero_not_nothing` |
| M2 | **2 failed** (predicted 1) | `..._an_early_stop_with_a_dry_meter_...` + the existing `test_self_closing_early_stop_bucket_reconciles_from_pre_bucket` |
| M3 | **2 failed** (predicted 1) | `..._a_run_resumed_after_a_restart_is_never_called_dry` + the existing `test_restart_after_the_run_finished_finalises_it` |
| M4 | 4 failed, as predicted | all four dry-completion tests |
| M5 | 1 failed, as predicted | `..._a_dry_run_is_not_a_calibration_sample` |
| M6 | 1 failed, as predicted | `..._without_a_pre_bucket_anchor_leaves_the_bucket_alone` |
| M7 | 2 failed, as predicted | `..._is_recorded_as_a_failure_...` + `..._without_a_pre_bucket_anchor_...` |
| M8 | 1 failed, as predicted | `..._does_not_clear_the_zone_fault_it_just_raised` |

**M1 is the one worth knowing.** The prediction assumed the dry-completion
tests would fall with it; they do not, because each stubs `_sc_finish_flow` to
return `(0.0, {})` and never reaches the real one. So the collapse itself is
covered by exactly one test - the unit test written for it in Task 1. That is
enough, and it is deliberate (the completion tests are about the completion,
not about the meter), but anyone re-collapsing `0.0` will be stopped by one
test and no other.

M2 and M3 are the opposite surprise: an existing test guards each of those
paths as well, so the new pins are not load-bearing alone.

| # | Mutation | Command | Expected |
|---|---|---|---|
| M1 | Restore the collapse: `return (d if (d is not None and d > 0) else None), ...` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | ≥4 failed: the 0.0 test plus all three dry-completion tests |
| M2 | Delete the early-stop insulation in `async_stop_self_closing` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._early_stop_with_a_dry_meter...`) |
| M3 | `dry = measured is not None and measured <= 0` → `dry = not measured` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (the Task 5 restart pin) |
| M4 | `dry = ...` → `dry = False` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 4 failed (both Task 2 tests, Task 3, Task 4) |
| M5 | Drop the `if not dry:` around `_flow_calibration_check` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._not_a_calibration_sample`) |
| M6 | Drop `and not no_anchor` from the bucket branch | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._without_a_pre_bucket_anchor...`) |
| M7 | Swap `RUN_RESULT_FAILED` for `RUN_RESULT_COMPLETED` in the dry record | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 2 failed (Task 2's first test, Task 4's) |
| M8 | Replace the `else: self._clear_zone_fault(zone_id)` with an unconditional clear | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._does_not_clear_the_zone_fault...`) |

- [x] **Step 5: Confirm the tree is clean**

```bash
git status --short && git diff --stat
```

Expected: no modified tracked files.

- [x] **Step 6: Sister-path check (global CLAUDE.md)**

`distributor.py:747-749` carries the identical collapse for member zones. It is
out of scope by decision (spec §6) and gets its own issue — **not** a silent
omission. Confirm the file is untouched:

```bash
git diff --stat 418ab8a0 -- custom_components/irrigation_plus/distributor.py
```

Expected: **no output.**

**MEASURED: no output** - `distributor.py` untouched. The whole change is one
production file and three test files:
`self_closing.py +125/-8`, `test_self_closing.py +284`,
`test_opensprinkler.py +24`, `test_master.py +5`.

- [x] **Step 7: Record the measured numbers**

Done inline above. Misses: the lint file count (69, not 68) and three mutation
counts (M1 lower, M2 and M3 higher), each explained where it sits. The RED
messages again read `Expected 'mock' ...` rather than naming the method, since
the doubles are unnamed `Mock()`s.

- [x] **Step 8: Commit the plan's measured state**

```bash
git add docs/superpowers/plans/2026-09-26-dry-run-is-not-a-success.md
git commit -m "docs(plan): plan 2 measured - $(date +%F)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## What this plan does NOT do

- No new constant, no new run-record field, no migration (D5, D6).
- Nothing in `distributor.py`, though it has the same collapse (spec §6).
- No chain or cycle abort when the cistern reads dry (D4) — own issue.
- **The live test is not in this plan.** Spec §8 names the end-to-end criterion
  for both halves; it runs on HA-Test after the code review, as its own phase,
  and HA-Prod only on explicit release. A green suite is not the criterion.
- The upstream PRs are separate, approval-gated steps. Do not push, do not run
  `gh pr create`.
