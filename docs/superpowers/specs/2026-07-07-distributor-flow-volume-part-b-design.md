# Distributor flow-volume tracking — Part B (early stop) — Design

Date: 2026-07-07
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 4, sub-project B (early stop) — see `hasi-flow-volume-tracking-feature`
Builds on: Part A (measurement), shipped in b23 — `2026-07-07-distributor-flow-volume-part-a-design.md`

## Problem

Part A (b23) meters the actual delivered volume per distributor member window from the
shared inlet flow sensor and credits the real litres, but each outlet still runs its
**full computed window** — there is no early stop when the target volume is reached.
JustChr's normal zones already stop a real-flow run at its target volume
(`_run_valve_metered`, `real_flow=True`). Part B brings the same behaviour to
distributor member zones, following JustChr's zone scheme.

Goal: when a distributor has a rate flow sensor and a member has a positive volume
target, stop that member's watering as soon as the metered delivered volume reaches the
target — closing the inlet (classic) or firing the stop-service (self-closing). Rate
sensors only; cumulative counters stay dormant (as in Part A).

## Decisions (user, 2026-07-07)

1. **Variant scope:** classic (`linked_entity`) **and** self-closing service **with** a
   configured stop-service. Self-closing **without** a stop-service keeps Part A
   behaviour (measure only, full window).
2. **Trigger:** automatic — active whenever a rate `flow_sensor` and a valid volume
   target exist (like JustChr zones; no new opt-in field).
3. **Time cap — variant-split** (a self-closing valve physically cannot run past its
   passed duration, so extension is only possible for `linked_entity`):
   - **classic:** JustChr-faithful — run until the target volume, capped only by the
     member's safety `maximum_duration`; **may run past the nominal window** when the
     real flow is slower than the configured throughput.
   - **self-closing + stop:** early stop only — cap is the window (the self-close
     duration); never extends.

## Existing machinery to reuse (JustChr zone flow code)

- `_metered_target_volume(zone, floor)` (`irrigation.py:569`) — litres the zone must
  deliver to reach the post-run target bucket `floor`; `floor = _zone_target_bucket(zone)`
  (`irrigation.py:64`). Reused verbatim as the member's volume target.
- `_depth_from_volume_native(zone, volume_l)` (`irrigation.py:1228`) — gross bucket depth
  from measured litres. This is what `_run_valve_metered` uses to credit a **real-flow**
  run (`credit_depth = _depth_from_volume_native if real_flow else _credited_depth_native`).
- `_read_flow_increment` / `_flow_rate_to_l_per_min` (`irrigation.py:546/531`) — the rate
  integration Part A already reuses via `_dist_measure_window`.
- `ZONE_MAXIMUM_DURATION` (`const.py:289`, key `"maximum_duration"`, zone default ~4 h) —
  the classic-path safety cap.
- `DISTRIBUTOR_FLOW_POLL_SECONDS = 5` (Part A) — reused as the poll interval. The finer
  5 s tick (vs the zones' `FLOW_POLL_INTERVAL = 15`) bounds target overshoot to ≤ 5 s of
  flow, which matters for early stop.

## Design

### Per-outlet derivation (in `_dist_run_sweep`, before opening the inlet)

For each watered member:
```
target = _metered_target_volume(zone, _zone_target_bucket(zone))
can_stop_early = (
    watering_mode == CLASSIC              # we hold the inlet
    or (watering_mode == SERVICE and distributor.get("stop_service"))
)
rate_ok = flow_sensor present and a healthy rate reading (see fail-safe)
early_stop_active = rate_ok and target > 0 and can_stop_early
extends = early_stop_active and watering_mode == CLASSIC
cap = max_seconds (ZONE_MAXIMUM_DURATION) if extends else window
```

### Master coordination (REGEL 3 — reuse the hardened Phase-1 machinery, no new live re-noting)

The sweep's master note uses **`cap`** instead of the fixed `window`
(`_master_note_run(cap)`). For the classic-extend case this books the master off-deadline
against the safety cap up front, so the pump stays on for the (possibly extended) run.
When the outlet actually closes, the existing terminal `_dist_master_end`
(pre_deadline/own_deadline live-collapse from Phase-1) brings the deadline back to the
real close time — exactly the b23 mechanic. The self-closing and no-early-stop paths use
`cap == window`, so the master behaviour is byte-for-byte b23. No new live deadline
re-noting is introduced.

### Metered run (extend `_dist_measure_window` → windowed, volume-targeted)

`_dist_measure_window(distributor, cap, target=None)` gains an optional `target`. The
existing rate-integration loop additionally breaks when `delivered >= target` (when
`target` is given). **Return type change:** it now returns the tuple
`(delivered, actual_seconds, stopped_early)` instead of Part A's bare `delivered`-or-`None`
scalar — the Part A sweep call site and the Part A `_dist_measure_window` unit tests are
updated to unpack the tuple (same branch, no external consumers). `delivered` keeps its
Part A meaning (litres, or `None` to fall back to time-based crediting):
- no sensor / unreliable / cumulative-dormant → falls back exactly as Part A
  (`_dist_sleep(window)`, returns measurement `None`); `actual_seconds == window`,
  `stopped_early == False`. (When the sensor is not healthy, `cap == window` by the
  derivation above, so a fallback never extends.)
- rate sensor + target → integrate per 5 s step up to `cap`, breaking at `delivered >=
  target`; `actual_seconds = elapsed`, `stopped_early = elapsed < cap`.

The sweep then closes via the existing `_dist_close_inlet` (classic → inlet off;
self-closing → stop-service). The flow keeps running only for the microseconds between
the loop returning and the close call — negligible.

### Crediting (`_dist_credit_zone`) — measured litres + actual seconds + depth-fn fix

`_dist_credit_zone(zone, seconds, measured_l=None)` is called with the **actual** elapsed
seconds and the measured litres:
- **Correctness fix (REGEL 8, carried over from Part A):** a **measured** volume must be
  credited via `_depth_from_volume_native` (gross), NOT `_credited_depth_native` (which
  divides out the zone multiplier — correct only for *timed* volume). Part A used
  `_credited_depth_native` for both, under/over-crediting a measured run when the member's
  multiplier ≠ 1. Part B credits the measured path with `_depth_from_volume_native` and
  keeps the timed fallback on `_credited_depth_native`, mirroring `_run_valve_metered`'s
  `credit_depth` selection.
- `_record_run` logs `volume_l = measured litres`, `actual_s = elapsed`,
  `planned_s = window` (the plan was the window; the run may have stopped early or run to
  the safety cap).

### Fail-safe (never extend without healthy metering; never mis-credit)

- Sensor unavailable / non-numeric / cumulative-dormant / `target <= 0` / zone has no
  size → **no early stop**, `cap = window` (never `max_seconds`), time-based crediting.
  Extension is gated strictly on an actively-metering healthy rate sensor.
- Valve opened but `delivered <= 0` at the end (flow never registered) → treat as
  unreliable → time-based credit (do not credit 0 L). "No flow at open" remains the
  existing `confirm_entity` halt path (unchanged).
- A dead/flaky meter can never stop, shorten, extend unexpectedly, or halt the ring
  beyond what the existing confirm/halt logic already does.

### Position (indexing ring)

Early or late inlet close = earlier/later OFF edge = one close = one advance. No position
desync; the sequential sweep simply shifts in time. Advance logic unchanged.

### Gating + rate-only

Presence-gated on `flow_sensor` + a valid target + a stoppable control path. Cumulative
metering stays dormant (`DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False`); a cumulative
sensor gets no early stop (measurement already degrades to time-based in b23). The
`flow_sensor` help text gains a short note that, where the valve can be stopped, the meter
also stops the outlet early at the target volume (all 8 languages).

## Testing

- **classic early stop:** target reached before the window → inlet closed early,
  `actual_seconds < window`, credited the measured litres via `_depth_from_volume_native`.
- **classic extend:** slow flow, target reached *after* the nominal window but before the
  safety cap → runs past the window; master note = cap, terminal collapse to the real
  close; assert no master over-run and no early master-off mid-sweep.
- **classic never reaches target:** runs to `max_seconds` safety cap, closes, credits the
  measured litres.
- **self-closing + stop:** target reached before the window → stop-service fired early;
  never extends.
- **self-closing without stop / no flow_sensor / cumulative / no target / no size →**
  unchanged (Part A measure or time-based, full window, no early stop, `cap == window`).
- **crediting depth fn:** a member with multiplier ≠ 1 credits the measured volume gross
  (`_depth_from_volume_native`), not divided by the multiplier.
- **fail-safe:** unreliable sensor never extends (`cap == window`); `delivered <= 0` →
  time-based credit.
- **position:** exactly one advance per outlet regardless of early/normal/extended close.
- **regression:** existing distributor, master (H7), and Part A tests stay green.

## Out of scope (→ later)

- Cumulative-counter early stop (dormant flag; a later joint zone+member rollout).
- Throughput auto-calibration from the sensor (pressure-dependent — deferred / maybe never).
- Any change to the normal-zone `_run_valve_metered` path (Part B only touches the
  distributor sweep + `_dist_credit_zone`).
