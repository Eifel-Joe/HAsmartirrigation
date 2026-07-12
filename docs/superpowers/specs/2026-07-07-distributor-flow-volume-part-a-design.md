# Distributor flow-volume tracking — Part A (measurement) — Design

Date: 2026-07-07
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 4, sub-project A (measurement) — see `hasi-flow-volume-tracking-feature`

## Problem

Distributor member zones are credited **time-based**: `_dist_credit_zone(zone, seconds)`
(`distributor.py:606`) computes `_timed_volume_l(zone, seconds)` = seconds × configured
throughput, then credits the bucket + logs the run. The distributor's `flow_sensor`
field (the shared inlet meter) exists in the form + store (`store.py:349`) but the
backend reads it nowhere — the help text says "not yet active".

Goal (Part A only): measure the **actual** delivered volume per member window from the
distributor's flow meter and credit that instead of the time estimate. No early stop —
each window still runs its full duration (early stop is Part B).

Scope decision (user, 2026-07-07): Part A first (measurement, all 3 control variants,
no actuation change); Part B (early stop for classic + self-closing-with-stop) later.

> **SCOPE CORRECTION (2026-07-07, supersedes the cumulative parts below).** b23 ships
> **RATE-ONLY**, matching JustChr's existing zone flow code, so the distributor member
> zones behave exactly like the existing zones (releasable without deviating from the
> baseline). The **cumulative-total** branch described in the "Units" and "Measurement"
> sections below is implemented but **dormant behind a feature flag**
> (`const.DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False`): a cumulative sensor
> degrades to time-based crediting in b23. The cumulative code + tests are retained so a
> later **joint zone+member** cumulative rollout only has to flip the flag (do NOT arm it
> for the distributor alone). Consequence: the user's Sonoff SWV (a cumulative L counter)
> is not volume-metered in b23.

## Existing machinery to reuse (JustChr zone flow code)

Normal zones already do flow-metered runs, RATE-only:
- `_flow_rate_to_l_per_min(value, unit)` (`irrigation.py:531`) — converts rate units
  (`l/h`, `m³/h`, `m³/min`, `gal/min`, `gal/h`; default `L/min`) to L/min.
- `_read_flow_increment(zone, step_seconds)` (`irrigation.py:546`) — reads the zone's
  flow sensor, converts its rate to L/min, integrates over the step; returns 0.0 on
  unavailable/non-numeric.
- `_credited_depth_native(zone, volume_l)` (`irrigation.py:1245`) — volume → bucket
  depth in the zone's units (the crediting path).

These are RATE-only; a cumulative total counter (the user's Sonoff SWV) is NOT handled
by the zone code (an unrecognized unit is assumed to be `L/min`).

## Units (user directive: follow the existing JustChr conventions)

- **Rate sensors:** reuse `_flow_rate_to_l_per_min` verbatim (same unit strings +
  factors). Classify a unit as a rate iff it is a per-time unit (contains `/`, e.g.
  `L/min`, `L/h`, `m³/h`, `gal/min`).
- **Cumulative total sensors** (NOT in the zone code): add a total→litres converter
  using the SAME factors/strings — `L`/`l`/`liter(s)` → ×1, `m³`/`m3` → ×1000, `gal`/
  `gallon(s)` → ×3.785411784; unknown total unit → assume litres (mirrors the rate
  path's "assume L/min" default). Total units are those NOT containing `/`.

This keeps one unit vocabulary (JustChr's) across zones and the distributor; the only
addition is the cumulative branch the zone code lacks.

## Design

### Measurement in the sweep (`_dist_run_sweep`)

Today each watered outlet does: open inlet → (confirm) → `await _dist_sleep(window)` →
credit (time-based) → close inlet. When the distributor has a `flow_sensor`, replace
the single sleep with a **poll-and-accumulate loop** over the same `window`:

```
delivered = 0.0
last_total = <read distributor flow_sensor>   # only for the cumulative branch
elapsed = 0.0
while elapsed < window:
    step = min(FLOW_POLL_SECONDS, window - elapsed)
    await _dist_sleep(step)
    elapsed += step
    inc, last_total = _dist_flow_increment(distributor, step, last_total)
    delivered += inc
```

`_dist_flow_increment(distributor, step_seconds, last_total)` (new, in `distributor.py`)
reads `distributor["flow_sensor"]` and returns `(litres_this_step, new_last_total)`:
- unavailable / non-numeric → `(0.0, last_total)` and mark the window "flow-unreliable"
  (see fail-safe);
- rate unit → `_flow_rate_to_l_per_min(raw, unit) * step / 60`, `new_last_total = None`;
- total unit → `max(0.0, raw_l - last_total_l)` (litres, converted), `new_last_total =
  raw_l`; a **negative** delta (counter reset/rollover) contributes 0.0 and marks the
  window flow-unreliable for that member.

`FLOW_POLL_SECONDS` = a small constant (reuse the existing metered tick if one is
defined, else e.g. 5 s). Poll granularity only affects rate accuracy; a cumulative
counter is exact regardless.

### Crediting (`_dist_credit_zone`)

`_dist_credit_zone` gains the measured litres. When a reliable measurement exists it
credits `_credited_depth_native(zone, measured_l)` and records the run with
`volume_l=measured_l` (actual), `trigger=RUN_TRIGGER_DISTRIBUTOR`. Otherwise it keeps
today's `_timed_volume_l(zone, seconds)` path unchanged. (`actual_s`/`planned_s` still
carry the window seconds — Part A does not change the timing.)

### Fail-safe (degrade to time-based, never break watering)

A flow sensor that is unavailable / non-numeric / has no reading at open / whose
cumulative counter goes backwards during the window → the window is marked
**flow-unreliable** and that member is credited **time-based** (today's behaviour). The
window still runs its full duration and the sweep advances/closes exactly as now. A
dead or flaky meter must never stop irrigation, halt the distributor, or mis-credit.

### Gating + UI

Purely presence-gated on the distributor's `flow_sensor` (mirrors the zone
`real_flow = bool(zone.get(ZONE_FLOW_SENSOR))`). No `flow_sensor` → the sweep keeps the
single `_dist_sleep(window)` + time-based credit, byte-for-byte unchanged. Update the
`flow_sensor` field help text (currently "not yet active") to state it now measures the
actual delivered volume — in all 8 languages.

## Testing

- Cumulative counter: open snapshot + per-step deltas sum to the counter delta; a member
  is credited the measured litres (m³ and gal units converted correctly).
- Rate sensor: rate × window integrates to the delivered litres (reuses
  `_flow_rate_to_l_per_min`).
- Fail-safe: sensor unavailable / non-numeric / counter-goes-backwards → the member is
  credited time-based; the sweep still advances + closes; no halt.
- No `flow_sensor`: the sweep is unchanged (single sleep, time-based credit) — assert the
  poll loop is not entered.
- Unit classification: `/`-units → rate path, total units → cumulative path.
- The measurement never changes the sweep's outlet order, early-stop bound, or master
  handling (existing distributor tests stay green).

## Out of scope (→ Part B and beyond)

Early stop by volume (`target_volume`, closing the inlet / firing the stop-service
early), the self-closing stop-service variant, and the optional throughput
auto-calibration idea (pressure-dependent — deferred / maybe never).
