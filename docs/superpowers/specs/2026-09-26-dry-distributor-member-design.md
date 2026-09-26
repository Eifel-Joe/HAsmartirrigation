# A dry distributor member run is not a delivery (`Eifel-Joe#53`)

- **Issue:** [`Eifel-Joe#53`](https://github.com/Eifel-Joe/HAsmartirrigation/issues/53)
  — `schwere:hoch`, `groesse:M`, `prod-scharf`, `typ:fehler`
- **Base commit:** `418ab8a0` (`upstream/master`, v2026.09.23), re-verified 2026-09-26
- **Branch:** `fix-a-dry-member-run-is-not-a-delivery`
- **Sister design:** `2026-09-26-self-closing-fault-lifecycle-design.md` §4, §10.1
  — the same defect on the self-closing path, shipped as
  [`JustChr#174`](https://github.com/JustChr/HAsmartirrigation/pull/174)

---

## 1. The problem

`distributor.py:747-749` collapses a live-but-dry meter to "no measurement":

```python
# Part B fail-safe: a live-but-dry meter delivered 0 L -> unreliable so the caller
# falls back to time-based crediting (spec: delivered <= 0 -> None).
reliable = delivered is not None and delivered > 0
return (delivered if reliable else None), elapsed, stopped_early
```

`None` is the caller's signal to credit from the **planned window** instead. So a
member zone behind an empty cistern gets:

- its bucket credited for the full planned volume (`_dist_credit_zone`'s
  time-based branch prices `_timed_volume_l(zone, planned)`),
- those litres added to `water_used_total`,
- `ZONE_LAST_IRRIGATION` stamped,
- and its run logged `COMPLETED`.

Nothing anywhere says no water arrived. The zone reads as satisfied, the next
calculation starts from a bucket that was never filled, and the deficit is gone
until the next rain resets the arithmetic.

Against a **broken** meter the collapse is a genuine fail-safe — that is why it
was written. Against a meter that watched the whole window and integrated
nothing it is the opposite: it credits water that never flowed.

The self-closing path had the identical line at `self_closing.py:365` and
`Eifel-Joe#4` removed it. This is that fix, on the path a Gardena-style
distributor waters through.

### 1.1 Why this path is sharp on the production installation

The production installation runs a Gardena 1197 distributor with member zones
(`hasi-prod-setup-snapshot`, `hasi-gardena-distributor-plan`). A distributor
waters its outlets in sequence from **one shared inlet**, so a dry supply is not
a per-zone accident — it takes out every outlet in the ring at once, and each one
is credited in full on the way past.

---

## 2. Decisions

| # | Decision | Alternative rejected |
|---|---|---|
| D1 | The "meter read after the valve-open seed" witness is derived **locally**, from `_dist_measure_window`'s existing `last_live`. | Stacking the branch on `JustChr#174` to use `FlowMeter.saw_reading_after_open()`. It is the same concept in one place, but the upstream PR could then not go out until `#174` merges — and `#174` has no review after two days. `flow_metering.py` is also on this session's do-not-touch list for exactly that reason. |
| D2 | A dry member run is recorded `RUN_RESULT_FAILED` with `detail=FAULT_FLOW_NEVER_STARTED`. **No zone fault is raised.** | Raising `_set_zone_fault` + `_fire_zone_problem` like `#4` does. On the distributor path **nothing clears a zone fault** — all five `_clear_zone_fault` callers on `master` sit in the classic runner's own machinery (`irrigation.py:1601`, `:1777`, `:1953`, `:2131`, `:2239`) and `JustChr#173` adds two more, both in `self_closing.py`. A fault raised here would never end. Pairing it would make this PR carry `#3`'s finding as well as `#4`'s. |
| D3 | The dry branch passes a hard `0.0` to `_dist_credit_zone`, not the measured value. | Passing `measured` through. A rate sensor with a negative resting offset measures below zero (−0.2 L over a 600 s dry run, measured for `#4` §10.3); `depth_from_volume_native(-0.2)` would write the bucket **below** the level the run started from. |
| D4 | `_dist_read_flow` rejects non-finite values. | Leaving it. See §4 — without it the new witness is unsound. |
| D5 | The cycle-level question stays out. | Deciding it here. `Eifel-Joe#55` owns it and needs a product decision first; it also touches `run_chain.py`, which is blocked. |

---

## 3. The fix

Three sites, all in `custom_components/irrigation_plus/distributor.py`.

### 3.1 `_dist_measure_window` — the collapse becomes an evidence test

```python
delivered = meter.delivered()
stopped_early = (
    target is not None and (delivered or 0.0) >= target and elapsed < cap
)
if delivered is not None and delivered <= 0 and (
    last_live <= 0.0 or meter.saw_reset()
):
    delivered = None
return delivered, elapsed, stopped_early
```

Three properties this ordering has to keep:

1. **`stopped_early` is computed from the raw value, before the test.** Its
   behaviour is then byte-identical to today's. (Structurally the two cannot
   co-occur anyway: `target` is bound only under `flow_sensor and tv > 0 and
   can_stop`, so `stopped_early` requires `delivered >= target > 0`. The order
   is kept so that stays true without depending on that argument.)
2. **`<= 0`, not `== 0`** — `#4` §10.3, measured: a rate sensor's negative
   resting offset reads below zero on a dry run, and `== 0` would let it into
   the credit branch.
3. **`delivered is None` stays `None`.** `None == 0.0` is `False`, so a meter
   that never read at all is untouched and still degrades to time-based.

**Why the two exceptions:**

- `last_live <= 0.0` — **the meter never read after the valve-open seed.**
  `_dist_measure_window` feeds the open reading in at `at=0.0`
  (`meter.sample(reading[0], reading[1], reading[2], 0.0)`), so `_have_reading`
  is true from the first second and `delivered()` never returns `None` again
  whatever the sensor does next. A sensor that answered once at the open and
  then went unavailable is otherwise indistinguishable from one that watched the
  whole run and saw nothing. `last_live` already tracks exactly this — it is
  initialised to `0.0` and set to `elapsed` on every live poll, and `elapsed` is
  strictly positive inside the loop.
- `meter.saw_reset()` — **a totalizer reset the meter cannot price.** The
  distributor resolves its counter type read-only through
  `flow_learn_resolve(...)`, which sends an unlearned `auto` to the
  over-credit-safe `lifetime`. That KEEPS the pre-reset baseline, so a per-run
  counter's post-reset climb never rises above it and measures `0.0` while real
  water flowed. `#4` measured this case: **45 L really delivered,
  `delivered() == 0.0`, `saw_reset() == True`.** The classic runner diverts it to
  a time-based credit *before* its dry branch (`irrigation.py:1536`).

**NOT-TO-DO:** do not fold either condition into `FlowMeter.delivered()`. Its
`0.0` contract is what the crediting callers price a genuinely dry run with;
only a caller that writes a run OFF needs the stricter evidence.

### 3.2 The sweep — a dry run is a failure

`_dist_measure_window` has exactly **one** consumer (`distributor.py:1504`),
which is the whole reason this fix is smaller than `#4`'s five call sites. The
other two `_dist_credit_zone` callers never see a meter: the observed-external
path (`:894`) passes no `measured_l` at all.

```python
dry = measured is not None and measured <= 0
run_result = (
    const.RUN_RESULT_FAILED
    if dry
    else const.RUN_RESULT_PARTIAL
    if (measured is not None and target is not None and measured < target)
    else const.RUN_RESULT_COMPLETED
)
```

**The dry test must come first and must not mention `target`.** Both halves
matter:

- *First*, because Review-M-1's `PARTIAL` test would otherwise swallow it: a dry
  run with a target set satisfies `measured < target` and would log `PARTIAL`.
- *Without `target`*, because a member with no target volume — a can't-stop
  member, or `tv == 0` — would otherwise fall through to `COMPLETED`. That is
  the majority of the Part A configuration.

The credit call then becomes:

```python
await self._dist_credit_zone(
    zone,
    actual_seconds,
    measured_l=0.0 if dry else measured,
    planned_seconds=window,
    result=run_result,
    detail=const.FAULT_FLOW_NEVER_STARTED if dry else None,
    ceiling=(...unchanged...),
)
```

and the calibration advisory gains `not dry`:

```python
if not can_stop and measured is not None and not dry and not duration_override:
```

A run that delivered nothing says nothing about the hardware's throughput. Its
own guard (`irrigation.py:1285`, `FLOW_CAL_MIN_SAMPLE_L` ≈ 6.7 L) already
refuses a `0.0`, so this is defence rather than repair — but that floor is
derived from two tuning constants, and a future tuning that lowered it would
make this the caller that feeds 0 L over a full window in as a real rate.

### 3.3 `_dist_credit_zone` — a `detail` parameter

`_record_run` already takes `detail: str | None` (`irrigation.py:2935`);
`_dist_credit_zone` is the only thing in the way. One keyword-only parameter,
defaulting to `None`, passed straight through.

---

## 4. The precondition: `last_live` has to be a sound witness

`_dist_read_flow`'s docstring promises "None when unavailable/**non-numeric**",
but `float("nan")` and `float("inf")` both parse, so a sensor reporting `nan`
returns a tuple. `FlowMeter.sample()` then **rejects** it
(`flow_metering.py:150`, `if not math.isfinite(raw)`), silently.

Today that mismatch is harmless. The moment `last_live` becomes the witness it
is not: a `nan` read sets `last_live` without the meter having accepted
anything, so a sensor stuck at `nan` after the open read reports
`saw_after_open == True` with `delivered() == 0.0` — and the run is written off
as dry. **Exactly the false FAILED the guard exists to prevent.**

```python
try:
    value = float(state.state)
except (ValueError, TypeError):
    return None
if not math.isfinite(value):
    return None  # NaN/inf: not a number, and FlowMeter would drop it anyway
```

`import math` joins the module header. This brings `_dist_read_flow` in line
with its own docstring and with `FlowMeter.sample()`, and it is the sister-path
check carried down to the **precondition** rather than stopped at the branch —
the mistake `#4`'s review caught (`#4` §10.1).

Intended side effect: a `nan` sensor now counts as dead, so the dead-meter
extend guard (`elapsed - last_live >= dead_gap`) stops holding the shared inlet
open on it. That is the behaviour the guard was written for.

---

## 5. What a dry member completion does, and what it deliberately does not

With `measured_l=0.0`:

1. **`volume_l = 0.0`, `depth = _depth_from_volume_native(zone, 0.0) = 0`**, so
   `new_bucket = pre_bucket + 0`, and the ceiling clamp cannot move it in either
   direction: below the ceiling it does not fire, above it the existing
   `max(float(ceiling), pre_bucket)` returns `pre_bucket` unchanged — the clamp
   was already written so a low ceiling can never turn a run into a withdrawal
   (`test_credit_ceiling.py::test_a_distributor_sweep_never_takes_credit_away`).
   **The bucket is left exactly where the run found it, whatever the ceiling.**
2. **There is no credit to reverse.** Unlike the self-closing path, the sweep
   writes the bucket in one place only — `_dist_credit_zone`, *after* measuring.
   No optimistic pre-credit exists, so `#4`'s `RUN_PRE_BUCKET` anchor and the
   `no_anchor` branch its review removed cannot arise here at all.
3. **`water_used_total` is unchanged.** `add_to_total=True` with `volume_l=0.0`
   adds zero; left as it is, so the diff shows only what changed.
4. **`ZONE_LAST_IRRIGATION` is not stamped.** `_stamp_run_finalized` stamps it
   only for `volume_l > 0`.
5. **The run log entry says `failed` / `flow_never_started`.**
6. **No zone fault** (D2), so no `_fire_zone_problem` and no
   `_dist_mark_uncertain` either — the ring's *position* is not in doubt. The
   inlet opened, it advanced, it closed. Only the water is missing.
7. **The sweep continues.** The dry branch returns nothing and breaks nothing:
   the remaining outlets, `_dist_close_inlet`, the master window and the cycle
   persistence all run as before. This is the trap `#4` §4.3 step 5 names, and
   the answer here is that there is no early return to get wrong.
8. **No `EVENT_IRRIGATE_FINISHED`.** The distributor path never fired it (its
   only `bus.async_fire` is `_dist_notify`, `:198`), so unlike `#4` there is no
   `problems` list to fill.

---

## 6. Out of scope

- **The cycle-level question.** Outlet 1 dry means outlets 2..n are dry, so a
  scheduled sweep will write off every member in the ring one by one. Whether a
  dry supply should abort the cycle is `Eifel-Joe#55` — a product decision, and
  it touches `run_chain.py`, which the chain PR blocks. **This design makes the
  per-member record truthful; it does not decide what the cycle does about it.**
- **The classic runner's dead-after-seed blind spot** — `Eifel-Joe#54`.
- **`_stamp_run_finalized` zeroing the displayed duration when
  `pre_bucket >= 0`.** Reachable when `ZONE_BUCKET_THRESHOLD` is positive, since
  the sweep gate is `bucket < threshold`, not `bucket < 0`. Pre-existing and
  **not made worse**: today the time-based credit lifts the bucket above zero
  anyway, so the duration is zeroed on a dry run either way. Left alone.
- **i18n and the frontend.** `flow_never_started` already has a label in all
  eight languages on `master` — verified, one hit per file in
  `frontend/localize/languages/*.json`. No `npm run build`, no dist bundles.
- **`FlowMeter` itself.** Untouched, by D1.

---

## 7. Traps

- **`_dist_measure_window` is called on non-metering paths too.** No sensor and
  dead-from-start both return `None, window, False` before the meter exists. The
  evidence test sits after the loop and cannot see them.
- **`target` is never `0`.** It is bound only under `tv > 0`, so
  `stopped_early` cannot be true on a dry run. Pinned, not assumed (§8 T5).
- **22 test sites stub `_sc_finish_flow` as a 2-tuple** — that was `#4`'s
  constraint. `_dist_measure_window` returns a 3-tuple and keeps returning one;
  the shape does not change, so the stubs are irrelevant here. Do not "improve"
  the return into a 4-tuple.
- **Fault counts depend on the test SELECTION, not only on the code.** The same
  three files give 51 errors as a subset and 13 in the full run. Only the full
  run with a name `diff` against the baseline on **this** base commit decides.
- **Revert mutations with `git checkout -- <file>`, never by back-substitution.**

---

## 8. End-to-end criterion

**On HA-Test**, a distributor whose inlet flow sensor reads `0` runs a sweep for
a member zone with a deficit:

| | before the fix | after the fix |
|---|---|---|
| run log | `completed` | **`failed`, `flow_never_started`** |
| bucket | credited to the run target | **unchanged** |
| `water_used_total` | + planned litres | **unchanged** |
| `last_irrigation` | stamped | **not stamped** |

That is the live proof. It is the same observable set `#4` was proved with
(`docs/superpowers/reconstructed/2026-09-26-valve-safety-live-*.md`), on the
distributor path, and the three `sensor.wasser_*_flow` sensors on HA-Test
already sit at `0` — the case is present, not simulated.

**Unit-level pins** the implementation must produce:

- **T1** a live-but-dry member run is recorded `failed` / `flow_never_started`
  with the bucket unchanged — RED on `master` (logs `completed`, bucket
  credited).
- **T2** a member with **no** target volume is also recorded `failed` (guards
  the `target`-independence of the dry test).
- **T3** a sensor that read only at the valve-open seed still credits
  time-based — the `#4` §10.1 case, on this path.
- **T4** a totalizer that reset mid-run still credits time-based
  (`saw_reset()`).
- **T5** a `nan` reading after the open read does **not** make the run dry
  (§4, and it fails without the `isfinite` guard).
- **T6** a measured run that delivered water is still `completed`, and one below
  a set target is still `partial` — Review-M-1 unbroken.
- **T7** a dry run is not offered as a calibration sample.

---

## 9. Test baseline

Measured on the base commit `418ab8a0` in its own worktree
(`D:/Entwicklung/HASI/issue53-work/base`), full suite, and cross-checked against
`issue3-work/baseline-names.txt` — which was measured on the same commit, so the
two must agree. Numbers and the name list go into the plan when the run lands;
the rule is that only a **full run with a name `diff`** counts, never a subset
(`rebaseline-when-the-base-moves`).

Gates before the PR:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Plus a mutation matrix over the new guards — at minimum: drop the
`last_live <= 0.0` term, drop the `saw_reset()` term, flip `<= 0` to `== 0`,
move the dry test after the `PARTIAL` test, drop `not dry` from the calibration
gate, remove the `isfinite` guard. Each must kill at least one named test.
**Revert every mutation with `git checkout -- <file>`.**
