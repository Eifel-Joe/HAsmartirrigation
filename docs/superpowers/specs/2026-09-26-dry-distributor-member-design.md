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
| D1 | The witness comes from **inside `FlowMeter`**, as a new `metered_the_run()` accessor (credited a reading and declined none). | Deriving it locally from `_dist_measure_window`'s existing `last_live`, to keep `flow_metering.py` untouched while `JustChr#174` has it open. **That was the first design and the review measured it as a regression** — see §4.1's three inputs. The information the guard needs exists only inside the meter, so no local approximation is sound. |
| D2 | A dry member run is recorded `RUN_RESULT_FAILED` with `detail=FAULT_FLOW_NEVER_STARTED`. **No zone fault is raised.** | Raising `_set_zone_fault` + `_fire_zone_problem` like `#4` does. On the distributor path **nothing clears a zone fault** — all five `_clear_zone_fault` callers on `master` sit in the classic runner's own machinery (`irrigation.py:1601`, `:1777`, `:1953`, `:2131`, `:2239`) and `JustChr#173` adds two more, both in `self_closing.py`. A fault raised here would never end. Pairing it would make this PR carry `#3`'s finding as well as `#4`'s. |
| D3 | The dry branch passes a hard `0.0` to `_dist_credit_zone`, not the measured value. | Passing `measured` through. A rate sensor with a negative resting offset measures below zero (−0.2 L over a 600 s dry run, measured for `#4` §10.3); `depth_from_volume_native(-0.2)` would write the bucket **below** the level the run started from. |
| D4 | `_dist_read_flow` rejects non-finite values. | Leaving it. §4.4 — it keeps the function's own docstring true, and it stops a `nan` sensor holding the shared inlet open for the full extend cap (measured: 600 s -> 30 s). |
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
if delivered is not None and delivered <= 0 and not meter.metered_the_run():
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
   resting offset reads below zero on a dry run (`-0.4 L/min` across 30 s
   measures `-0.2`), and `== 0` would let it into the credit branch. On this
   guard the two are indistinguishable, because a meter that accounted for
   nothing has delivered exactly `0.0`; the comparison earns its keep one level
   up, in §3.2's `dry`.
3. **`delivered is None` stays `None`.** `None == 0.0` is `False`, so a meter
   that never read at all is untouched and still degrades to time-based.

**Why one term and not two.** The condition is `not meter.metered_the_run()`:
the meter credited at least one reading **and** declined none. `FlowMeter` holds
three distinguishable states and only the weakest was readable from outside —
"a numeric value arrived" (`_have_reading`, which `delivered()` gates on, and
which the valve-open seed satisfies on its own), "a reading was credited", and
"a reading was seen and refused". §4 is the whole argument, with the six measured
inputs that defeated the two weaker formulations this design went through.

**A `meter.saw_reset()` term stood beside it and was removed, because the
mutation that drops it kills nothing.** That is structural rather than a coverage
gap: `_saw_reset` is assigned in exactly one place, inside `_sample_totalizer`'s
near-zero branch, and `_declined` is set unconditionally just above the `if` that
guards it — so `saw_reset()` implies `not metered_the_run()`. A `NOT-TO-DO` at
the `_declined` assignment records that a caller depends on the two staying
together.

The classic runner reaches the same diversion from the other side
(`irrigation.py:1535`): it has no declined flag, so there `saw_reset()` is the
test rather than a redundant one.

**What this costs, measured:** a per-run counter whose reset falls inside the
window reads as declined, so its `0.0` degrades to the time-based credit and
never gets a dry verdict. That is correct rather than a gap — after a reset a
`0.0` cannot be told apart from a post-reset climb the retained baseline
swallowed, which is the 45 L case (`#4` measured: **45 L really delivered,
`delivered() == 0.0`, `saw_reset() == True`**) this guard exists for. A per-run
counter that *does* deliver is unaffected: its `delivered` is positive, so the
guard never looks.

**NOT-TO-DO:** do not fold this condition into `FlowMeter.delivered()`. Its
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

## 4. Why the witness has to come from inside `FlowMeter`

**This section replaces an earlier design that derived the witness locally, from
`_dist_measure_window`'s existing `last_live`. The review measured that it does
not work.** The reasoning is kept in full, because the failure is the interesting
part and the same mistake is available on every other metered path.

### 4.1 What was wrong with a local witness

`last_live` records the elapsed time of the most recent poll for which
`_dist_read_flow` returned a tuple. That is **not** the same as "the meter
credited something", and the difference is not an edge case. Three inputs, each
measured against the real `FlowMeter` through the real `_dist_measure_window`,
produce a `0.0` for a run in which water demonstrably flowed — and on the base
commit all three returned `None`, so the local witness was a **regression**:

| input | water that really flowed | `418ab8a0` | local witness |
|---|---|---|---|
| rate sensor at 12 L/min, live only every 5th poll (gap 25 s > `max_gap_s` 20 s) | the whole window | `None` | **`0.0`** |
| totalizer `100 → 60, 70, 80, 90` | 30 L | `None` | **`0.0`** |
| totalizer `45 → 8, 20, 30, 40` (per-run reset, first post-reset read above `near_zero` 4.5) | 32 L | `None` | **`0.0`** |

The mechanisms are three separate places where `FlowMeter` accepts a value and
then declines to price it:

1. `_sample_rate` (`flow_metering.py:162-166`) refuses to integrate when
   `dt > max_gap_s` — dropped samples must not be bridged with a recovered rate.
   `sample()` has already set `_have_reading` by then.
2. `_sample_totalizer`'s drop branch keeps the baseline and credits nothing when
   a fall is **not** near-zero. A counter that goes backwards 100 → 60 and climbs
   to 90 never passes its retained baseline.
3. The same branch's near-zero test is `max(1.0, 0.1 × last)`. A per-run counter
   whose first post-reset reading is *above* that floor never even sets
   `saw_reset`, so neither witness sees it.

Case 1 needs no exotic hardware: a flow sensor that is `unavailable` for four
consecutive polls between live reads is exactly the flapping-sensor mode the
dead-meter extend guard was written for (audit H1).

Left in, each of these becomes `RUN_RESULT_FAILED` / `flow_never_started` on a
run that watered, once §3.2 lands — **the same defect class as the critical that
`JustChr#174`'s first review missed, one abstraction level lower.** That review's
lesson was "carry the sister-path check down to the precondition"; the precondition
here turned out to be one level below the one the first attempt hardened.

### 4.2 The accessor

`FlowMeter` gains one read-only accessor and one flag, set at exactly the two
points where a reading is credited:

```python
    def metered_the_run(self) -> bool:
        """True iff this meter accounted for the whole run: it credited at
        least one reading and declined none.
        …
        Read it before ``end_rate_at`` — that method rewrites ``_delivered``
        afterwards and deliberately touches neither flag.
        """
        return self._priced and not self._declined
```

**Two flags, because "credited something" is not enough.** The first design
exposed only `_priced`, and the review measured that one credited interval
latches it for the whole run: two ordinary reads in front of any of the three
inputs above mask the rest of the window, so a pump that takes a poll to build
pressure behind a flapping sensor reports `0.0` across 10 L. `_declined` is the
other half — a post-seed reading the meter saw and refused to credit.

- `_priced` in `_sample_rate`'s in-gap branch, beside the `_delivered` increment,
  and in `_sample_totalizer`'s rising branch.
- `_declined` in `_sample_rate`'s `else` (the gap the meter will not integrate
  across) and unconditionally on `_sample_totalizer`'s drop, **above** the
  near-zero branch — a caller depends on that placement, see §3.1.
- Neither in the seed path (`if self._last is None`), which accounts for nothing.

An interval credited at 0 L counts as priced, and that is the point: a rate
sensor reading 0 every poll, or a totalizer holding its value, has *measured* the
dryness. Measured: both of those return `0.0` through the guard, so a genuinely
dry run is still written off; and a pressure surge at valve-open followed by an
empty cistern (`12, 0, 0, 0…`) is correctly written off too — the surge sample is
the seed, which prices nothing, and every interval after it is credited at 0.

### 4.3 The cost this design accepts

`flow_metering.py` is touched, which the first design existed to avoid because
`JustChr#174` also edits that file. The consequence is a small textual conflict
in `sample()`'s neighbourhood for whichever of the two merges second. That is
stated in the PR body so the maintainer is not surprised by it, and it is the
lesser evil: the alternative was shipping a known regression.

**`JustChr#174` has the same hole.** Its guard is
`d <= 0 and (meter.saw_reset() or not meter.saw_reading_after_open())`, and
`saw_reading_after_open()` is true for all three inputs in §4.1's table — it
records that a sample was *accepted*, not that one was *priced*. That PR is
already submitted, and `self_closing.py` is out of scope here, so this design does
not change it. **It is reported, not fixed.**

### 4.4 `_dist_read_flow` still rejects non-finite values

The `math.isfinite` guard stays, but its justification changed with the witness.
It is no longer needed to keep a witness honest — `metered_the_run()` cannot be
misled by a `nan`, because `FlowMeter.sample()` rejects the value before either
pricing path. Two independent reasons keep it:

1. **The docstring already promised it** — "None when unavailable/**non-numeric**"
   — and `float("nan")`/`float("inf")` parse.
2. **The dead-meter extend guard reads the same tuples.** A `nan` sensor is dead
   for metering, so it must release the shared inlet. Measured: with a `nan`
   sensor after the open read, `window=30, cap=600`, the inlet is held **600 s**
   without the guard and **30 s** with it.

The second is the real one, and it is a 20× improvement on a shared valve.

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
- **The same hole in `JustChr#174`.** Its `saw_reading_after_open()` records that
  a sample was accepted, not that one was priced, so all three of §4.1's inputs
  get past it too. That PR is already submitted and `self_closing.py` is out of
  scope here. **Reported, not fixed** (§4.3).
- **`irrigation.py`'s `_read_flow_sample`** has `_dist_read_flow`'s non-finite hole
  as well. Latent today — nothing on that path reads a timing-based witness — and
  in a file another PR owns. Reported.

---

## 7. Traps

- **`_dist_measure_window` is called on non-metering paths too.** No sensor and
  dead-from-start both return `None, window, False` before the meter exists. The
  evidence test sits after the loop and cannot see them.
- **`target` is never `0`.** It is bound only under `tv > 0`, so
  `stopped_early` cannot be true on a dry run. Verified at the call site
  (`distributor.py:1457-1466`), not assumed.
- **An interval credited at 0 L counts as priced, and must.** It is how a
  genuinely dry run is recognised. `metered_the_run()` is not "delivered > 0".
- **One credited interval does not vouch for the rest of the window.** The first
  accessor latched on the first credit and was defeated by two ordinary reads in
  front of any failing input — hence the second flag.
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
  time-based — the `#4` §10.1 case, on this path. The seed prices nothing, so
  `metered_the_run()` is false.
- **T4** a totalizer that reset mid-run still credits time-based
  (`saw_reset()`). Input `100, 100, 5, 7`: this one has PRICED an interval, so
  it is the pin that keeps `saw_reset()` from being dropped as redundant.
- **T5** a `nan` reading after the open read does **not** make the run dry.
- **T8** a rate sensor live only every fifth poll (gap 25 s > `max_gap_s` 20 s)
  at 12 L/min still credits time-based — §4.1 case 1, the flapping sensor. RED
  against the local-witness design, which returned `0.0`.
- **T9** a totalizer `100 → 60, 70, 80, 90` still credits time-based — §4.1
  case 2, 30 L of real climb below a retained baseline.
- **T10** a totalizer `45 → 8, 20, 30, 40` still credits time-based — §4.1
  case 3, a per-run reset whose first post-reset read clears `near_zero`.
- **T11** a rate sensor reading 0 every poll IS written off, and a totalizer
  holding `100, 100, 100, 100` is too — the controls that stop T8–T10's fix
  from disabling the feature. Plus `12, 0, 0, 0…`: a pressure surge at the open
  followed by an empty cistern is a dry run, because the surge is the seed and
  every interval after it is credited at 0.
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
whole guard, drop `_priced` from either credit site, drop `_declined` from either
refusal site, reduce `metered_the_run()` to `self._priced` alone, reduce it to
`self._delivered > 0`, flip the sweep's `<= 0` to `== 0`, move the dry test after
the `PARTIAL` test, drop `not dry` from the calibration gate, pass `measured`
instead of a hard `0.0`, remove the `isfinite` guard, downgrade the dry warning.
Each must kill at least one named test, **except** the guard's own `<= 0`, which
is provably unreachable there (a meter that accounted for nothing has delivered
exactly `0.0`, never a negative) — recorded as surviving, with the reason. The
matrix is what found the redundant `saw_reset()` term: its mutation killed
nothing, and the term was removed rather than a test invented for it.
**Revert every mutation with `git checkout -- <file>`.**
