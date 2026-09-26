# A self-closing zone's fault has a whole life: it is set, and a good run ends it

Design for `Eifel-Joe#3` (valve safety 1) and `Eifel-Joe#4` (valve safety 2),
which stacks on it. Base commit: `418ab8a0` (`upstream/master`, v2026.09.23).

Former designations: `PR C1` / `PR C2` of the work order of 2026-09-21.

---

## 1. The problem

Three defects, one theme: the self-closing family of runners (self-closing
proper, batch, OpenSprinkler) can *raise* a zone fault but can never *end* one,
and the one condition that should raise the loudest fault — a run that
delivered nothing — is instead booked as a success.

### 1.1 One unpaired site (`#3`)

Seven sites announce a zone problem on the bus. Six of them also record the
fault so the problem sensor lights:

| site | `_set_zone_fault` | `_fire_zone_problem` |
|---|---|---|
| `batch.py:184/185` | yes | yes |
| `batch.py:217/218` | yes | yes |
| `batch.py:297/298` | yes | yes |
| `irrigation.py:1116/1117` | yes | yes |
| `run_watch.py:1031/1032` | yes | yes |
| `self_closing.py:547/548` | yes | yes |
| **`self_closing.py:646`** | **no** | yes |

`self_closing.py:646` fires `PROBLEM_VALVE_DID_NOT_OPEN` — the confirm poll saw
the valve stay off, the run is aborted, the credit reversed — and leaves the
problem sensor dark. A user automation bound to the bus event hears it; a user
looking at the dashboard does not.

### 1.2 Nothing ever clears (`#3`)

`_clear_zone_fault` has five callers, all in `irrigation.py`, all on the classic
metered or rotating path (`:1601`, `:1777`, `:1953`, `:2131`, `:2239`). Not one
lies on a path a self-closing, batch or OpenSprinkler run can reach.

So a fault raised on such a zone — by the unresolvable station at
`self_closing.py:547`, by the batch sites, by `_watch_give_up` at
`run_watch.py:1031` — stays lit forever. No later good run puts it out. The only
cure is an HA restart, because `_zone_faults` lives in memory.

That is not only a lamp. `skip_conditions.py:136` publishes the fault map into
the dashboard outlook, `binary_sensor.py:331` drives the per-zone problem
sensor, and `binary_sensor.py:440` the hub's. A user automation that holds off
irrigation while a zone reports a problem never releases it again.

### 1.3 A dry run is booked as a success (`#4`)

`_sc_finish_flow` (`self_closing.py:365`) ends with

```python
measured = d if (d is not None and d > 0) else None
```

`FlowMeter.delivered()` distinguishes two states that this line does not:
`None` means no numeric reading was ever seen (dead or misconfigured sensor),
`0.0` means the meter was alive all run and integrated nothing
(`flow_metering.py:249-254`: "A live-but-dry meter returns 0.0"). The leading
case for `0.0` is the one that matters in the field: **a dry cistern behind a
live flow sensor.**

The warning just above at `:354` is gated on `d is None and sensor`, so it does
not fire for it. And with `measured` collapsed to `None`, `_sc_finish_run` takes
the no-measurement branch:

- the bucket keeps the full optimistic credit written at open,
- `volume_l` becomes `self._timed_volume_l(zone, planned_s)` — the full planned
  litres — and `add_to_total=True` adds them to `water_used_total`,
- the run is recorded `RUN_RESULT_COMPLETED`.

A zone that received nothing is recorded as fully watered, its deficit is wiped,
and it is not due again until the weather re-opens it. Nothing is logged.

The other two flow paths already get this right in their own way. The classic
metered runner has the exact concept (`irrigation.py:1580-1592`): "Valve opened
but the flow sensor never registered any flow — failed run: do not credit the
bucket, flag a fault so the deficit persists." `observed_watering` returns `0.0`
as `0.0` deliberately (`observed_watering.py:233-239`), after the phantom-open
incident. Self-closing is the outlier.

---

## 2. Decisions

Taken with the user on 2026-09-26, each recorded with the alternative it beat.

| # | Decision | Rejected alternative |
|---|---|---|
| D1 | **Report and do not credit.** A dry completion mirrors the classic runner: fault, `RUN_RESULT_FAILED`, bucket back to its pre-run level, nothing added to the total. | Report only (fault + event, credit unchanged). Rejected: the false booking is the actual harm; reporting it while keeping it would leave the three flow paths inconsistent for no gain. |
| D2 | **Clear at each success site.** `_clear_zone_fault` goes into `_sc_finish_run` and `async_stop_self_closing`, the way the classic runner places it. | Centrally in `_record_run` keyed on the result. Rejected: it would also fire for `RUN_RESULT_OBSERVED` and `RUN_RESULT_SKIPPED`, where clearing is wrong or at least unexamined — a much larger regression surface for a bugfix. |
| D3 | **One spec, two plans.** | Two specs. Rejected: the shared question (what a good run does to the fault, what a dry one does) would be answered twice and drift. |
| D4 | **The chain keeps advancing** after a dry run. Aborting the whole cycle when the cistern reads empty is new cross-zone policy and gets its own issue. | Abort the chain. Rejected here as scope creep on a bugfix, and it would touch `run_chain.py`, which is blocked by PR 2 until `JustChr#165` merges. |
| D5 | **No sampler marker.** The restart case is already excluded by `_sc_finish_flow`'s early return; a pin test proves it. | Build the marker anyway. Rejected: a record field plus legacy-record handling, for a need that cannot be demonstrated. See §5. |
| D6 | **Reuse `FAULT_FLOW_NEVER_STARTED`.** | A self-closing-specific constant. Rejected: an automation listening for `flow_never_started` today would not see the self-closing case, and self-closing zones are the majority. ~~Fault reasons are passed through unlocalised — there are no i18n entries to add.~~ **Wrong, corrected after review:** `panels.zones.fault.*` is a localised catalogue in all eight languages (`frontend/localize/languages/`, NOT `translations/`, which is where this was checked). `flow_never_started` happens to be in it already; `valve_did_not_open` was not, so §3.1's fault fell back to the generic text and had to be added — see §10. |

---

## 3. The fault's life (`#3`)

### 3.1 Pair the unpaired site

`self_closing.py:646` gains `_set_zone_fault(zone_id, const.PROBLEM_VALVE_DID_NOT_OPEN)`
immediately before its `_fire_zone_problem`, spelled as `:547` already spells it.
Seven sites, seven pairs.

### 3.2 Two clearing sites cover three modes

`_clear_zone_fault` goes into exactly two functions:

- `_sc_finish_run`, before `_record_run(result=RUN_RESULT_COMPLETED)`,
- `async_stop_self_closing`, before `_record_run(result=RUN_RESULT_PARTIAL)`.

Both placements copy the classic runner: it clears before the record on
completion (`irrigation.py:1601`) and on a partial alike
(`_record_rotating_stop`, `:1777`; the rotating partial at `:1953`).

Two sites are enough for all three modes because batch and OpenSprinkler runs
finalise through the same two functions — verified, not assumed:

| mode | completion | partial / stop |
|---|---|---|
| self-closing | `self_closing.py:429` | `self_closing.py:996` |
| batch | `batch.py:756` | `batch.py:557`, `batch.py:663` |
| OpenSprinkler | `run_watch.py:982`, `:1012` | `run_watch.py:984`, `:1014`, `:1028` |

So the five set sites named in the issue's scope — `batch.py:184/217/297`,
`run_watch.py:1031`, `self_closing.py:547` — all become clearable without a line
in `batch.py` or `run_watch.py`.

### 3.3 Two places that must NOT clear, both pinned

**`_watch_give_up` (`run_watch.py:1026-1032`)** calls
`async_stop_self_closing(...)` and only *then* `_set_zone_fault(zid, reason)`.
With §3.2 in place the stop clears first and the next line sets the new fault:
the net result is right, the ordering is load-bearing, and nothing in the code
says so. A later refactor that hoists the set above the stop would swallow the
fault silently. **Pin:** after `_watch_give_up`, the zone carries the
`station_never_ran` fault.

**The dry path of §4.** A dry completion must not reach the clear.

---

## 4. A dry run (`#4`)

### 4.1 Delete the collapse rather than route around it

`_sc_finish_flow` stops collapsing and returns `d` as the meter reported it:

```python
-        measured = d if (d is not None and d > 0) else None
-        return measured, self._flow_learn_end_changes(zone, meter, open_start_l)
+        # 0.0 is an ANSWER, not a missing one: the meter was alive all run and
+        # integrated nothing. Returned as 0.0 exactly as _observed_finish_flow
+        # returns it, so the two flow paths say the same thing with the same
+        # value. None still means no numeric reading was ever seen.
+        return d, self._flow_learn_end_changes(zone, meter, open_start_l)
```

**Rejected: a third `dry` element in the tuple.** It was the first design, and
measurement killed it. 22 test sites across 9 files stub this method as a
two-tuple (`Mock(return_value=(None, {}))`), so a third element forces 22
mechanical edits -- noise in a bugfix PR. And no test pins the collapse at all:
the one test that reads the return directly (`tests/test_self_closing.py:1223`)
measures a totalizer reaching 18 L. Deleting the special case is smaller than
adding a channel beside it, and it removes the divergence from
`_observed_finish_flow` instead of documenting it.

Only two production sites read the value -- `self_closing.py:406`
(`_sc_finish_run`) and `:950` (`async_stop_self_closing`), both edited here. The
other three discard it (`:286`, `:641`, `:761`).

**Three consequences the change forces, each with its own test:**

1. **`_flow_calibration_check` no longer short-circuits on `measured_l is None`.**
   **Measured after review: it does not actually matter.** A second guard
   (`irrigation.py:1285`) rejects anything below `FLOW_CAL_MIN_SAMPLE_L`, about
   6.7 L, so a `0.0` was already refused. The dry path skips the call anyway,
   as defence: that floor is derived from two tuning constants
   (`FLOW_CAL_METER_RESOLUTION_L / FLOW_CAL_DEVIATION`) and a future tuning that
   lowered it would make this caller the one feeding 0 L in as a rate. The guard
   is kept, its justification corrected.
2. **`async_stop_self_closing` must keep today's behaviour.** One line reading a
   `0.0` back as "no measurement", or an early stop credits zero litres -- the
   case §4.2 exists to protect.
3. ~~**A record with no `RUN_PRE_BUCKET`.**~~ **Built, then removed after
   review — see §10.** It guarded a state no record written by this process can
   reach (a live in-memory meter proves the record is this process's, and both
   writers set the field), and where it could fire it was incoherent:
   `_stamp_run_finalized` re-reads the bucket, found the un-reversed optimistic
   credit at `>= 0` and zeroed the displayed duration, so the zone read
   "satisfied, duration 0" beside a run logged FAILED. A `NOT-TO-DO` now stands
   in its place.

### 4.2 Act on the completion path only

Only `_sc_finish_run` treats a `0.0` as a dry run. `async_stop_self_closing`
maps it back to "no measurement" (§4.1 consequence 2), and the three callers that
merely discard a meter (`self_closing.py:286`, `:641`, `:761`) never look.

This mirrors the classic runner's `not stopped` guard
(`irrigation.py:1580`), and the reason is the same: a run stopped five seconds
in reads `0.0` litres because the water has not reached the sensor yet, not
because the cistern is empty. Raising a dry fault on every early stop would make
the fault worthless.

### 4.3 What a dry completion does

In `_sc_finish_run`, when `dry` is true:

1. **Reverse the credit — which the existing measured branch already does.**
   With the collapse gone, `nb = pre_bucket + self._credited_depth_native(zone, 0.0)`
   is `pre_bucket`, and `min(pre_bucket, ceiling)` cannot move it, because the
   pre-run level was by construction at or below the run's ceiling. No new
   arithmetic, and no extra guard (§4.1 consequence 3).
2. **Record the failure.** `result=RUN_RESULT_FAILED` and
   `detail=const.FAULT_FLOW_NEVER_STARTED`. `volume_l` is already `0.0` from the
   measured branch, so `add_to_total` is left exactly as it is -- adding zero is
   the same either way, and not touching it keeps the diff to what changed.
3. **Raise the fault.** `_set_zone_fault(zone_id, const.FAULT_FLOW_NEVER_STARTED)`
   plus `_fire_zone_problem`, and **not** `_clear_zone_fault`. This is the single
   line `#4` shares with `#3`.
4. **`_stamp_run_finalized(zone_id, 0.0)` stays and needs no special case.** It
   stamps `ZONE_LAST_IRRIGATION` only for `volume_l > 0`, and it zeroes the
   displayed duration only when the bucket is `>= 0` — which step 1 has just
   pushed back to the deficit. Both branches decline on their own. **This holds
   only because step 1 always reverses**; it was the removed no-anchor branch,
   which did not, that made this claim false for itself (§10).
5. **The chain and the deferred calculation still run.**
   `async_run_deferred_calculation` and `_chain_advance_for_run` stay on the
   path. The classic runner may `return` out of its dry branch because it is not
   a link in a chain; `_sc_finish_run` is one, and an early return there strands
   the rest of the cycle and leaves a deferred calculation pending. **This is the
   trap of this fix.**
6. `EVENT_IRRIGATE_FINISHED` still fires, but carries the reason in `problems`
   instead of `[]` — the only case in which that list was ever meant to be
   filled.
7. **`_flow_calibration_check` is skipped**, and this is not optional: with
   `measured` now `0.0` rather than `None`, its own guard no longer catches it and
   it would price 0 litres over the planned minutes as a real observed rate.

### 4.4 Why batch runs cannot trip this

`batch.py` never calls `_sc_start_flow_sampling`, so a batch run has no meter and
`_sc_finish_flow` returns before `d` is read. The dry path is reachable only by a
self-closing run with a flow sensor, and by an OpenSprinkler run whose sampler
`run_watch.py:827` started at the observed start.

---

## 5. The marker the issue asked for, and why it is not built

`Eifel-Joe#4` asks for "a marker that the sampler ran for the whole run",
reasoning that the check would otherwise report a dry run after every restart
because `async_resume_self_closing_runs` does not restart the sampler.

The premise about the sampler is correct — that function re-arms the cleanup,
re-takes the master hold and re-adopts the valve watcher, and never restarts
sampling. The conclusion does not follow for the placement chosen in §4.1:

- `_sc_meters()` is pure in-memory state (`self_closing.py:236-243`), so a
  restart loses every meter;
- `_sc_finish_flow` opens with `entry = self._sc_meters().pop(zone_id, None)`
  and returns on a missing entry **before `d` is ever read**.

A resumed run therefore returns `dry=False` by construction. The marker would be
needed only if the decision were taken at the caller on `measured is None`,
which is exactly the placement §4.1 avoids.

This is an argument, so it gets a measurement: a pin test that resumes a run
across a restart and asserts the finish raises no fault. If that test fails, D5
is wrong and the marker comes back.

---

## 6. Out of scope

- **`distributor.py:747-749` carries the identical collapse** for member zones
  ("a live-but-dry meter delivered 0 L -> unreliable so the caller falls back to
  time-based crediting"). Same defect, same harm. Deliberately not in this
  commit; it gets its own issue so the two PRs stay reviewable.
- **Aborting a chain or cycle when the cistern reads dry** (D4) — own issue.
- The remaining divergence between the three flow paths beyond the dry case.
- `run_chain.py` (PR 2 pending), `live_estimate.py` (`Eifel-Joe#22` waiting on
  `JustChr#168`), `calculation.py` (`JustChr#172` in review). None is touched.

---

## 7. Traps

1. **Do not `return` early from the dry branch** (§4.3 step 5). The classic
   runner's shape does not transfer: `_sc_finish_run` advances the chain.
2. **`_watch_give_up`'s ordering** (§3.3) becomes load-bearing the moment the
   clear lands in `async_stop_self_closing`.
3. **The `0.0` / `None` distinction is the whole of `#4`.** Any refactor that
   re-collapses the two -- or any new consumer of `_sc_finish_flow` that treats a
   falsy `measured` as "no measurement" -- re-introduces the bug. §4.1
   consequence 1 is the live example: a guard written as `is None` stops catching
   what it used to.
4. **A widened return value can expose impossible fixtures.** Letting `0.0`
   through will turn some existing tests red; read each for whether it models a
   state the code cannot reach before touching production code (memory
   `narrowing-exposes-impossible-fixtures`).

---

## 8. End-to-end criterion

Both halves are checked on HA-Test first; HA-Prod only on explicit release.

**`#3`** — drive a self-closing zone into a fault (a `confirm_entity` that stays
off gives `PROBLEM_VALVE_DID_NOT_OPEN`): `binary_sensor.<zone>_problem` turns
on, which today it does not. Then let a good run finish: the sensor turns off
again, which today it never does.

**`#4`** — with the Sonoff emulator (memory `hasi-sonoff-emulator-testsystem`),
run a zone whose flow sensor holds `0` while the valve reports open. Expected:
the run log shows `failed` with reason `flow_never_started`, the bucket reads its
pre-run value rather than a satisfied one, and `water_used_total` has not moved.
Today: `completed`, bucket satisfied, total raised by the full planned volume.

---

## 9. Test baseline

Measured on the base commit `418ab8a0` in its own worktree
(`issue3-work/base`), because the old `baseline-names.txt` was taken on
`965a4f9d` and no longer applies (memory `rebaseline-when-the-base-moves`):

```
7 failed, 3254 passed, 9 skipped, 10 warnings, 349 errors in 281.50s
```

356 failure/error names in `issue3-work/baseline-names.txt`. These are the known
Windows-local blockers; CI is the authoritative gate.

---

## 10. What the review changed (2026-09-26, after implementation)

A `superpowers:code-reviewer` pass over `418ab8a0..fdb89d92` found one Critical
that turned `#4` into its opposite, plus three Important findings. All were
measured before being accepted, and two of the reviewer's own points were
overruled with evidence.

### 10.1 Critical: a `0.0` is only an answer when the meter could answer

`_flow_build_meter` feeds the valve-open reading **into** the meter, so
`_have_reading` is true from the first second and `delivered()` never returns
`None` again. Two states then report `0.0` without having measured the run:

- **a sensor that answered once at the open and then went unavailable** — the
  dead-sensor case §4.1's own docstring claimed still returned `None`;
- **a per-run totalizer on a zone whose type is still being learned.** It
  resolves to the over-credit-safe `lifetime`, which KEEPS the pre-reset
  baseline, so the post-reset climb never rises above it. Measured: **45 L
  really delivered, `delivered() == 0.0`, `saw_reset() == True`** — and the run
  recorded FAILED with its credit reversed.

The classic runner diverts that second case to a time-based credit **before**
its dry branch (`irrigation.py:1536`) and pins it with
`test_metered_zone_auto_hold_until_reset_credits_timed_not_fault`. This design
mirrored the branch and not its precondition — the sister-path check stopped one
level too early.

**Fix:** `FlowMeter` gains `saw_reading_after_open()`, and `_sc_finish_flow`
returns `None` for a `0.0` when the meter either never read after the seed or
saw a reset it cannot price. `delivered()` is untouched: its `0.0` contract is
what the crediting callers price a genuinely dry run with, and only the caller
that writes a run OFF needs the stricter evidence.

**Not fixed here:** the classic runner has the same blind spot for the
dead-after-seed case. It is a pre-existing defect in another runner with
different credit mechanics, so it gets its own issue rather than widening this
PR. And a rate sensor whose every interval exceeds `FLOW_MAX_GAP_SECONDS`
remains indistinguishable from dry on both paths; separating those needs
coverage accounting, not a guard.

### 10.2 Important, accepted

- **The no-anchor branch is gone** (§4.1 consequence 3, §4.3 step 1).
- **`valve_did_not_open` had no label** in any of the eight languages, so
  §3.1's fault showed the generic "The last irrigation run failed." rather than
  its cause — which is half of what §3.1 is for. Added everywhere; only
  `en.json` is bundled, so two dist bundles were rebuilt.
- **Two event contracts in `docs/usage-events.md` had gone stale**:
  `irrigation_finished` now also fires for a run recorded failed and can carry a
  filled `problems` list, and `zone_problem` now carries `flow_never_started`.
  Its `entity_id` can be null, which `batch.py` has done since long before this
  branch without the docs saying so.

### 10.3 Overruled, with evidence

- **`<= 0` rather than `== 0`** was questioned and is right. A rate sensor with
  a small negative resting offset measures below zero (−0.2 L over a 600 s dry
  run, measured); `== 0` would let that into the credit branch and write a
  bucket *below* the pre-run level. A run that really watered cannot go net
  negative — a totalizer structurally cannot, and a 600 s run at 10 L/min with a
  −5 L/min blip at close measures 99.17 L.
- **The early-stop insulation cannot swallow a full-window run.** Every
  full-window route delegates to `_sc_finish_run` first
  (`run_watch.py:981-984`, `:1010-1014`), including a manual stop inside the
  finish grace, which returns before `_sc_finish_flow` is reached at all.
