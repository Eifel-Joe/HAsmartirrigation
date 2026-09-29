# The distributor does not start over an open inlet

Design for `Eifel-Joe#66`, reported upstream as `JustChr#181`. Base: `upstream/master` =
`1876aa03` (unchanged on 2026-09-29). Every line reference below is to that commit.
`0b9a71bd` (`JustChr#182`, merged later that day) moves `store.py` below line 1680 down by four
lines; no other file cited here changed.

**Status:** behaviour decided with the user on 2026-09-29. **JustChr agreed to the claim as the
gate's place on 2026-09-29** (`JustChr#181`, comment `5894821774`): every entry passes it, and the
estimate stays independent of the moment it runs; the behaviour, the signal set and what the user
sees stand as proposed. He added one request, a grace period after the integration's own close
command, decided with the user the same day: **30 s, and only after a close command that was
actually sent** (R6, *The grace after our own close*). The implementation plan follows this
amended spec.

## The defect, measured

Count watch mode, HA-Test, build `v2026.09.29b1` (identical to `1876aa03` on this path). Inlet
opened from outside, then *Irrigate now* on one member. Full record:
`docs/superpowers/reconstructed/2026-09-29-distributor-inlet-open-count-repro.md`.

| # | measured |
|---|---|
| H1 | the stored position advanced at the foreign on edge (4 → 5) while, by the ring model the code documents (`distributor.py:1744-1768`), outlet 4 kept flowing |
| H2 | a cycle was claimed 40.4 s into the foreign open; opening the already-open inlet made no edge (one ON, one OFF in the recorder for the whole sequence) |
| H3 | the leg was credited to the member at outlet 5 (61 s, 10.17 L, `completed`) |
| H4 | the member at outlet 4, whose outlet had the water for 106 s, got nothing, not even an `observed` entry |
| H5 | afterwards the stored position was 6 against the model's 5, `position_state` still `synced` |

Nothing prompts a re-sync, so every later cycle waters and credits the outlet after the one it
names, until someone re-syncs by hand.

## Why nothing in the code stops it

* **The claim** (`distributor.py:1195-1203`) asks three things before it takes the distributor:
  synced, commissioning confirmed (not for a test run), not already in flight. Nothing about the
  inlet.
* **`_dist_eligible_for_run`** (`:383-410`) asks the same static questions plus demand. Nothing
  about the inlet either.
* **The inlet-watch sees edges, not states** (`:1013-1020`). `count` advances the position at a
  seen off→on edge and stashes the open for the observed credit (`:949-954`); `warn` marks the
  distributor uncertain at the same edge; `ignore`, the default (`store.py:517`), registers no
  listener at all (`:1055-1062`). An inlet that is open without a seen edge — `old_state` is None
  at start-up, or `unavailable → on` — registers in no mode.
* **The claim drops the stash** (`:1212`), so in `count` the foreign run's credit is discarded
  the moment a cycle claims the distributor (H4).
* **The zone predicate does not reach it.** JustChr on `JustChr#181`: a member watered from
  outside shows up as a foreign *inlet* open, not in `_observed_on_since`, so asking
  `zone_run_in_flight` from `distributor.py` would not close the gap.

## What it costs, per watch mode

| mode | a cycle claimed while the inlet is open |
|---|---|
| `count` | **measured**, H1–H5: credit to the wrong member, the right one gets nothing, position silently one ahead |
| `warn` | read: the foreign edge's `_dist_mark_uncertain` blocks later claims through the synced guard; between the edge and that store write a claim still passes |
| `ignore` | read: the member at the flowing outlet is watered on top of the foreign run; in classic mode the integration's close also ends the foreign run at the end of its own window. The position stays consistent. |
| any mode, no edge seen | read: behaves like `ignore` at the claim |

## Requirements

* **R1** — No distributor cycle starts while its inlet reports open: through every entry, in
  every watch mode, in both watering modes, whenever `inlet_entity` is set.
* **R2** — A refused cycle changes nothing: no claim, no stash pop, no busy marker, no master
  hold, no position write, no `active_cycle`. In `count` with observed watering the foreign run
  is then credited to the right member at its close edge, by the code that exists today — when
  the open lasted at least twice the skip pulse, below which it counts as an advance pulse
  (`:979-984`).
* **R3** — The refusal is visible where a user looks: the log, a notification, and the history
  of the members that did not get their water.
* **R4** — The finish-anchor estimate (`get_total_irrigation_duration`) does not change.
* **R5** — No new persisted state. The integration never actuates an inlet it did not open.
* **R6** — The integration's own close does not refuse the next cycle: for 30 s after the
  integration sent a close command for a distributor's inlet, an open report from that inlet does
  not block that distributor's claim (JustChr's request on `JustChr#181`).

## Options considered

### What happens to a cycle that meets an open inlet (user decision)

| option | cost |
|---|---|
| **chosen: refuse it** | the members keep their deficit until the next run; under-watering shows in the bucket, over-watering would not (the lesson of `Eifel-Joe#64`). Uniform across all modes. |
| defer until the inlet closes, then sweep | a small scheduler of its own (waiting, cancel on unload, the days-since counter, the run's parameters); it only pays in `count` — in `warn` the distributor is uncertain after the foreign pulse, in `ignore` the ring is desynchronised by it. Filed as a follow-up. |
| take over: close the inlet, then sweep | impossible in service mode without `stop_service`; ends a deliberate manual run |

### Where the gate sits (agreed by JustChr on 2026-09-29)

| option | covers every entry | cost |
|---|---|---|
| **chosen: in the claim**, `async_run_distributor_cycle` | yes: schedule, *Water all zones*, *Irrigate now*, the member run with a custom duration, `distributor_run_now`, the test run from button and service | none found; the estimate is untouched |
| in `_dist_eligible_for_run` (JustChr's suggestion) | no: `distributor_run_now` (`:1896`) and the test run (`:1788`) call the claim directly | the predicate also feeds the estimate (`skip_conditions.py:593`): a foreign open at the instant of the estimate would drop the distributor's track, and a finish-anchored schedule would start too late. A flag to exempt the estimate makes it the claim's check again with less coverage. |
| both | yes | two places for one question; the dispatcher gains nothing, because the claim already knows the target members (`only_zone_ids`) |

### What the gate reads

| option | verdict |
|---|---|
| **chosen: the live state of `inlet_entity`** | the one signal all modes share; covers an open without a seen edge; no new state |
| the stash in `_dist_observed_open_map` | only `count` with observed watering, only after a seen edge |
| the inlet's flow sensor | rejected: a rate sensor lags, a totaliser needs a baseline |
| a listener in every mode, recording opens | new state, and still blind to an open without a seen edge |

### Which modes it covers (user decision)

**All modes, whenever `inlet_entity` is set.** `ignore` is the default, so leaving it out would
leave the default installation unprotected. `ignore` means "do not track foreign pulses"; the
gate asks a different question, "do not start over an open inlet". In classic mode
`inlet_entity` is the valve the integration switches itself, so its state is as reliable as the
switching.

### The grace after our own close (JustChr's request; user decision)

| option | verdict |
|---|---|
| **chosen: `_dist_close_inlet` records the time once its close command returned, and the gate consults it** | one writer, one reader; every close of the integration's own counts without weighing each call site |
| record it only at a cycle's last close | every close site would need its own reasoning, for nothing: a close in the middle of a sweep never meets the gate |
| let the sweep wait until the inlet reports closed, up to 30 s | lengthens every cycle, holds the claim and the master while it waits, and ends cycles up to 30 s later than the finish-anchor estimate says. JustChr asked for a grace, not a wait |

**30 s, and only after a command that was actually sent** (user decision): the grace is
`VALVE_CONFIRM_TIMEOUT`, the window `_confirm_valve_running` already gives a slow valve to report
open. Service mode without `stop_service` sends no command and gets no grace.

### Count's advance (user decision)

**`count` keeps advancing at the on edge** (`:954`). With the gate, no cycle can start while the
stored position is one ahead of the flowing outlet, which removes the one consumer that was
harmed. Moving the advance to the off edge would make the close handler book advances itself,
and it cannot tell a foreign off edge from the late off report of the integration's own
self-closing run — the same race that makes missed edges their own issue — and
`on → unavailable → off` would lose an advance that the on edge books today.

## The design

### The gate

The order in `async_run_distributor_cycle` becomes:

```
synced → commissioning confirmed (not for a test run) → not in flight → INLET → inflight.add
```

* A pure, synchronous helper (working name `_dist_inlet_reports_open(distributor)`) returns the
  blocking state or `None`.
* **It blocks on exactly `on`, `open`, `opening`, `closing`.** `closing` blocks because the valve
  has not closed yet and the ring has not indexed.
* **It never blocks** on `off`, `closed`, `unavailable`, `unknown`, a missing entity, an empty or
  absent `inlet_entity`, or any other state. "Not available" does not mean "open", and this keeps
  today's behaviour for every case the gate cannot judge.
* It is independent of the watch mode and of the watering mode.
* **It never blocks during the grace after the integration's own close** for this distributor
  (R6, next section).
* The read is `hass.states.get`, synchronous, so there is still no `await` between the check and
  `inflight.add`; the single-flight guarantee of the claim is unchanged. The grace check is a dict
  lookup and a clock read, synchronous as well.
* **In flight before the gate:** while the integration's own sweep holds the inlet open, the
  in-flight guard answers first, so the gate never reports the integration's own run.

### The grace after our own close

Requested by JustChr on `JustChr#181`: `_dist_close_inlet` sends the close command and does not
wait for the inlet to report closed. A slow or cloud-polled inlet can keep reading `on` or
`closing` for a while after the integration's own close, and a cycle for the same distributor right
after it — a second dispatch, or *Irrigate now* on another member — would be refused although
nothing foreign happened.

* **Where it starts:** `_dist_close_inlet` records `self.hass.loop.time()` under the
  distributor's id **after its close command returned without raising** — the monotonic clock
  this module already measures a foreign open with (`distributor.py:951`, `:978`): in classic mode once the inlet was turned
  off, in service mode once `stop_service` was called. Service mode without `stop_service` sends
  nothing and records nothing: without a command there is no evidence the valve has closed, and a
  cycle started over a still-open inlet is the measured defect itself (H2). A close command that
  raises records nothing either.
* **Every own close counts:** the end of each leg (`distributor.py:1725`), the halt after a failed
  confirm (`:1595`), the safety close on an exception (`:1255`) and the close after a restart
  (`:1824`). Only a close that ends a cycle can ever meet the gate — its last leg's, the safety
  close, or the close after a restart; a close in the middle of a sweep is followed by the sweep's
  own next open. After a halt, and after a restart in the `pausing` phase, the distributor is
  uncertain, and the synced guard refuses before the gate is asked. After a restart in the
  `watering` or `starting` phase it stays synced (`:1813-1816`), and the resume close's grace
  applies like any other. *(Erratum 2026-09-29, found in the plan's dry run: this said a restart
  always leaves the distributor uncertain.)*
* **How long:** a new constant `DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS = VALVE_CONFIRM_TIMEOUT` (30 s),
  one number for how long a valve may take to report. The grace holds while less than 30 s have
  passed since the recorded close.
* **Where it is kept:** a dict on the coordinator, keyed by distributor id and created on first
  use. In memory only (R5): it holds no handle, needs no teardown, and a restart forgets it.
* **What it does:** while the grace holds, `_dist_inlet_reports_open` returns `None` for that
  distributor, whatever the inlet reports. Another distributor's gate is not affected.
* **The trade, accepted by JustChr:** a foreign open inside those 30 s goes unseen.

### The refusal

The refusal returns `False` before `inflight.add`, like the guards before it. It does not persist
`STARTING`, does not start the master, does not write a position, does not touch
`active_cycle`, and **does not pop the observed stash** (R2). For the callers:
`_dispatch_distributor_cycles` returns `False`, so the distributor contributes nothing to the
scheduler's days-since reset; *Irrigate now*, the member run, `distributor_run_now` and the test
run end without a sweep. `distributor_run_now` raises no error of its own, consistent with the
other guards of the claim; the log and the notification tell the user.

The refusal path may `await` (it does not hold the claim) and does three things:

1. **Log a warning:** `Distributor '%s' did not start a cycle: inlet %s is %s`.
2. **Notify** through `_dist_notify`: the same `notification_id` per distributor as a halt, so a
   repeat replaces the previous notification instead of piling up; forwarded to `notify_target`
   when one is set. New key `panels.distributors.notify.inlet_open` in all eight languages,
   filled with `.replace()` like `halted`, with the placeholders `{name}` and `{entity}`:
   * EN: `Distributor '{name}' did not start a watering cycle: its inlet {entity} was open.`
   * DE: `Verteiler '{name}' hat einen Bewässerungszyklus nicht gestartet: sein Einlass {entity} war offen.`

   The wording stays neutral about who opened the inlet: it can also be the tail of the
   integration's own self-closing run whose off report comes late — in service mode without
   `stop_service`, which gets no grace, or once the grace has run out. Nothing dismisses the
   notification automatically, as with the halt notification today.
3. **Record a skipped run** for the members through `_record_skipped_run`, with a new reason
   `SKIP_REASON_INLET_OPEN = "inlet_open"`, labelled under `panels.zones.outlook.checks.inlet_open`
   in all eight languages (EN `Distributor inlet open`, DE `Verteiler-Einlass offen`) — the key
   the history table already localises skip codes from (`ip-zone-history.ts:74-79`).
   * **Which members:** the members of this distributor that are in `only_zone_ids`, otherwise
     every member of this distributor — always passed as an **explicit list**. Both halves
     matter: the dispatcher hands the claim the schedule's whole target, direct zones included
     (`allowed = target`, `distributor.py:482`), and `_record_skipped_run(None, …)` means every
     zone of the installation (`irrigation.py:3041-3059`). Disabled members are skipped there
     already. This follows the rain-delay convention of recording every targeted member, due or
     not (`distributor.py:441-458`).
   * **No entry for a test run** — it never waters or credits.
   * **Trigger** `manual` for a forced member run (`force_water`), otherwise the default
     `schedule`. *Water all zones* cannot be told from a schedule at the claim; the rain-delay
     path has the same imprecision today.

### Behaviour by situation

| situation | today (`1876aa03`) | with the gate |
|---|---|---|
| `count`, on edge seen | sweep over the open inlet, credit to the neighbour, position one ahead (**measured**) | refused; the stash stays, the close edge credits the right member (with observed watering); the position is right, booked at the on edge while the ring steps at the off edge |
| `warn`, on edge seen | blocked by the synced guard, except between the edge and the store write | that window is closed |
| `ignore` | member watered on top; in classic mode the foreign run is cut at the integration's window | refused; the foreign pulse itself still desynchronises the ring, as `ignore` is documented |
| any mode, no on edge seen | sweep over the open inlet | refused; the later off edge still books nothing — separate issue |
| own close sent (classic, or service with `stop_service`), the inlet still reports `on` or `closing`, next claim within 30 s | sweep | **not refused** — the grace (R6) |
| the same, next claim after 30 s, the inlet still reports open | sweep | refused |
| own self-closing run without `stop_service`, late off report, immediate second claim | sweep over a possibly still-open valve | refused, correctly: no command was sent, so no grace |
| foreign open within 30 s of the integration's own close | sweep over the open inlet | not seen — the trade JustChr accepted |
| service mode without `stop_service` | — | nothing special: a refusal actuates nothing |
| service mode without `inlet_entity` | — | no signal, unchanged; stated in the docs |
| finish-anchor estimate | — | unchanged |

### Documentation

`docs/configuration-distributors.md`, section *Watching the inlet for foreign pulses*, gains a
paragraph: a cycle never starts while the inlet reports open, in every watch mode, provided an
inlet entity is set; for 30 s after the integration closed the inlet itself, an inlet that still
reports open does not block, so a slow or cloud-polled valve does not refuse the next cycle
(service mode needs a stop service for this); a refused cycle appears in the members' history and
as a notification; re-sync only while the inlet is closed; a self-closing distributor without an
inlet entity has no such protection.

## Sister paths checked

* **Every sweep entry passes the claim:** the schedule (`scheduler.py:2390`), *Water all zones*
  and *Irrigate now* (`irrigation.py:3389`), the member run (`irrigation.py:3446`),
  `distributor_run_now` (`distributor.py:1896`), the test run (`distributor.py:1788`, called from
  `button.py:236` and the service registered at `services.py:530`). Covered by one gate.
* **Direct zones** are already covered: `_drop_zones_already_running` (`irrigation.py:3379`)
  asks the wide `zone_run_in_flight`.
* **`async_resume_distributor_cycles`** (`:1810`) closes an inlet after a restart; it starts
  nothing.
* **Each leg's own open** (`_dist_open_inlet` inside the sweep) is the mid-sweep window — see
  below.
* **Found while checking, filed separately:** `_dispatch_distributor_cycles` takes one list of
  distributor *copies* (`store.py:1718`, `attr.asdict`) and awaits each cycle in turn
  (`distributor.py:476-536`). With two or more distributors, B's claim and sweep read
  `position_state`, `commissioning_confirmed` and `current_outlet` (`:1417`) from a copy as old
  as A's whole sweep; a member run, a foreign pulse or a re-sync on B in that time is overwritten.
  A different mechanism — the gate reads live state and is not affected — so its own issue.

## Explicitly not in this work

Each of the first four gets its own issue in the fork; the texts are approved in the chat first.

* **Deferring a refused cycle** until the inlet closes.
* **Missed edges in the inlet-watch.** An on edge that is not seen (start-up, `unavailable → on`)
  leaves `count` and `warn` one position behind without any cycle: the close edge finds no stash
  and books nothing. Read, not measured: the handler also sees no close edge for a valve that
  closes through `closing` (`:1008-1020`; in `open → closing → closed` neither pair matches), so
  the observed credit is lost there; whether the inlet valves report `closing` is open.
* **A classic sweep over an unavailable inlet credits water that never flowed.** Home Assistant
  skips unavailable entities when it executes an entity service call (`helpers/service.py:477` in
  2024.12.5, to be confirmed on a current release before filing), so the sweep switches nothing
  and, without a flow sensor or `confirm_entity`, credits its window by time.
* **The stale distributor copies** described under *Sister paths checked*.
* **Residual windows, no issue:** a foreign open *during* a sweep (the handler ignores edges while
  `active_cycle` is set), and the seconds between the claim and the first open (master start and
  settle). Different windows, no harm measured, and no gate at the claim can see them. A third
  window is chosen, not left over: a foreign open within 30 s of the integration's own close goes
  unseen (R6, the trade JustChr accepted).
* The flow sensor as a substitute signal (rejected above) and moving `count`'s advance (decided
  above).

## End-to-end criterion

**Tests** (pytest; locally Python 3.12 + HA 2024.12.5, CI is the authoritative gate). All drive
the real `async_run_distributor_cycle`:

1. It blocks on `on`, `open`, `opening`, `closing` (parametrised): `False`, no sweep, no
   `STARTING`, nothing left in the in-flight set, no master hold.
2. It lets the cycle through on `off`, `closed`, `unavailable`, `unknown`, a missing entity, an
   empty `inlet_entity`.
3. Independent of the mode: `count`, `warn`, `ignore`, each in classic and service mode.
4. Order: a distributor in flight with its inlet on returns `False` without notification or
   history entry.
5. **The measured case as a regression test:** `count` with observed watering; the on edge
   through the real handler; the claim refused; the off edge — the member at the stashed outlet
   gets the observed credit, the position is start + 1, still `synced`.
6. Feedback: the notification with the per-distributor id, forwarded to `notify_target`; history
   entries for exactly the targeted members, or every member as a list — a zone outside the
   distributor gets **no** entry; none for a test run; trigger `manual` for a forced run,
   `schedule` otherwise.
7. Every entry once: the scheduled dispatch, `async_irrigate_now` (one zone and all),
   `async_run_zone` on a member, `handle_distributor_run_now`, `async_run_distributor_test`.
8. `get_total_irrigation_duration` returns the same with the inlet open and closed.
9. Both new keys in all eight languages with matching placeholders — pinned by the existing
   `tests/test_i18n_completeness.py`.
10. **The grace after our own close (R6)**, the clock driven through the host's
    `hass.loop.time`, the real `_dist_close_inlet`, the inlet state left `on`: (a) a claim 29 s after the close is not refused
    — JustChr's requested test; (b) 31 s after it, it is refused; (c) service mode with
    `stop_service`: the grace holds; (d) service mode without `stop_service`: no grace, refused at
    once; (e) a close on distributor A leaves distributor B's gate as it was; (f) a close command
    that raises records no grace.

**Gates:** the full suite with no new failures against a baseline measured at the
implementation's base commit; `black` and `ruff` clean; the dist rebuilt, all four bundles staged
with `-f` and counted; a mutation matrix over every added line, with no survivor left standing on
an argument instead of a measurement.

**Live on HA-Test** (a pre-release build; distributor Gardena1 set up as in the measurement
record; HA-Prod is not touched):

* **L1 `count`:** declare position 4, open the inlet, *Irrigate now* on zone 6. Expected: no
  claim (`watering_now`, the master and the run script stay off), the notification is present,
  Test5 shows *skipped — Distributor inlet open*; after closing (≥ 30 s open) Test4 gets the
  observed credit; stored 5 = model 5, `synced`.
* **L2 `ignore`** (watch mode switched in the panel): open the inlet, *Irrigate now* — refused.
* **L3 no edge:** open the inlet, restart HA-Test (announced first), then *Irrigate now* —
  refused. This proves that the live state covers the case without an edge. What the close then
  does to the position is evidence for the missed-edge issue.
* **L4 no false refusal:** inlet closed, *Irrigate now* — a normal cycle with its terminal
  advance.
* **L5 the grace after our own close** (service mode, single-member cycles only). For the test the
  inlet keeps reporting `on` after the integration's close: the leg's run script closes the valve
  45 s late (the `grace_emu_*` set, `input_number.grace_emu_off_delay` = 45), and `stop_service`
  is a do-nothing helper script created for the test — announced before it is created, removed
  afterwards. Single-member cycles, because a second leg would open while the first leg's valve is
  still waiting to close.
  * **L5a:** *Irrigate now* on one member; within 30 s of its leg's end, *Irrigate now* on another
    member — the cycle starts.
  * **L5b:** a fresh run; the second *Irrigate now* 31–44 s after the leg's end, the inlet still
    `on` — refused, with the notification and the history entry.
* Afterwards everything back as found: position, watch mode, logger level, valve, master, probe,
  the wiring changed for L5, and the helper script removed.

## Delivery

* One upstream pull request, branched from `upstream/master` (JustChr answered on 2026-09-29):
  the gate with its grace, the refusal path, both i18n keys in eight languages, the documentation
  paragraph, the rebuilt dist, the tests.
* Nothing in the code, the commits or the pull request refers to the fork's issues.
* This spec and the measurement record go to `archive/design-history` (rule P1).
