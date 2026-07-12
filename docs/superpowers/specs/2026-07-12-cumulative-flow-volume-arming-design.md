# Cumulative Flow-Volume Tracking — Arming + Calibration Advisory

> **Status:** approved (design), 2026-07-12
> **Base:** `production` c36c842 (v2026.07.16). Fork release first; upstream (JustChr) PR decided separately later.
> **Builds on:** flow-volume Part A (measurement, ~b23) + Part B (early-stop, ~b24), currently RATE-ONLY.

## Problem

The flow-volume feature ships **rate-only**: it trusts a flow sensor whose unit is a *rate*
(contains `/`, e.g. `l/min`). A **totalizer** meter (a cumulative counter — `m³`, `L`, `gal`,
no `/`, `state_class: total_increasing`) is not metered. On the distributor a full cumulative
branch exists but is parked behind `DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False`
(const.py:669), read at exactly one site (distributor.py:546); on the **zone** side there is no
cumulative code at all — `_read_flow_increment` (irrigation.py:586) reads every sensor as a
rate. So a user with a totalizer water meter gets no measured crediting and no early-stop.

Two further gaps ride along:
- **Review-M-1:** a run that reaches its safety cap *without* reaching its target volume is
  logged `completed`. `_dist_measure_window` computes `stopped_early` (distributor.py:573) but
  the sweep discards it (distributor.py:1210 drops the 3rd tuple element), so `_dist_credit_zone`
  always logs `RUN_RESULT_COMPLETED`.
- A **self-closing / fixed-window** valve cannot early-stop (no `stop_service`) and cannot
  cheaply extend its run, so a mis-configured throughput silently over- or under-waters with no
  feedback to the user.

## Goal

1. Meter and early-stop **totalizer** flow sensors, driven purely by the sensor **unit**
   (auto-detection, reusing the existing `flow_sensor` field — no new toggle), for **zones and
   distributor members together** (avoids the shared-bucket double-count the flag comment warns
   about).
2. Log a run that hit the cap short of its target as `partial`, not `completed` (Review-M-1).
3. For fixed-window (can't-stop) zones, detect consistent over/under-delivery and **notify** the
   user with a **recommended throughput correction**.

## Existing machinery (verified)

- Unit sniff + conversion (distributor only): `_dist_flow_unit_is_rate` (distributor.py:476-480,
  rate iff unit contains `/`), `_dist_flow_litres_from_total` (distributor.py:482-491, m³×1000,
  gal×3.785411784, else L). Dormant delta accumulator + rollover guard: distributor.py:549,
  566-572. Flag gate: distributor.py:546.
- `_dist_measure_window` (distributor.py:513-579) returns `(delivered|None, elapsed, stopped_early)`;
  a dead/dry/reset meter returns `None` → time-based fallback (fail-safe at :578).
- `_dist_credit_zone` (distributor.py:806-852): measured → gross depth (`_depth_from_volume_native`);
  None → time-based (`_timed_volume_l`). `add_to_total=True` (one-shot at window end).
- Member early-stop wiring: target `_metered_target_volume(zone, _zone_target_bucket(zone))`
  (distributor.py:1124, shared with zones at irrigation.py:609-623); `can_stop = classic or
  (service and stop_service)` (distributor.py:1120-1123); classic-extend cap
  (distributor.py:1127-1131).
- Zone metered run: `_run_valve_metered` (irrigation.py:625-798), loop guard
  `while elapsed < max_seconds and delivered < target_volume` (:717); increment reader
  `_read_flow_increment` (irrigation.py:586-607, **rate-only, stateless per step**); shared rate
  converter `_flow_rate_to_l_per_min` (irrigation.py:570-584). Zones stream credit continuously
  via `_commit_run_progress` (final `_record_run` `add_to_total=False`).
- `RUN_RESULT_PARTIAL = "partial"` (const.py:388) already has a `.history-partial` chip
  (view-zone-settings.ts:2072) + `results.partial` label in all 8 languages → **no new i18n**.
- `ZONE_THROUGHPUT = "throughput"` (const.py:290) is the per-zone flow rate (l/min).
- `water_used_total` (store.py:207) is the shared per-zone usage sink both paths write.

## Design

### Component A — Cumulative metering via unit auto-detection

- **Shared helpers (DRY):** lift the unit sniff + totalizer→litres conversion into the base
  (`irrigation.py`) as shared methods used by BOTH the zone reader and the distributor. Detection:
  a sensor is a **totalizer** when its unit lacks `/` **or** its `state_class` is
  `total_increasing`; otherwise a rate. No unit and no total_increasing → treat as rate (today's
  behaviour). Conversion: m³×1000, gal×3.785411784, L/unknown passthrough (optionally widen: kL).
- **Distributor:** delete the `DISTRIBUTOR_CUMULATIVE_METERING_ENABLED` flag and its gate
  (distributor.py:546); the dormant delta branch becomes live whenever a totalizer is detected.
- **Zone (new code):** for the linked-entity metered path (`_run_valve_metered`, used by
  linked/classic zones with a `flow_sensor`; standalone service zones are unmetered today and stay
  so), extend the reader to hold a `last_total` across the poll loop and route each step through
  the shared unit logic — rate → integrate `rate × step` (as today); totalizer → accumulate
  `cur − last`. Because the zone STREAMS credit continuously (unlike the distributor's one-shot
  end-of-window credit, so it cannot retroactively discard the whole window), a glitch-low or
  reset reading (`cur < last`) contributes 0 **and keeps the prior baseline** — it never reseeds
  to the low value. A transient dip is thus fully absorbed (the recovery step credits the true
  `cur − prior`), and a genuine mid-run reset merely stops further crediting (safe under-credit →
  the run extends to its cap and logs `partial`); it can never over-credit. The baseline is
  pre-seeded from a read at valve-open so the first poll interval is captured. The dry-meter
  fail-safe (delivered ≤ 0 → FAULT_FLOW_NEVER_STARTED) is preserved. Shared detection also excludes
  known abbreviated rate units without a slash (`gpm`, `lpm`, `gph`, `lph`) so they stay rates.
- **Arm together:** because both paths now use the identical unit logic, a shared physical meter
  is read the same way on both sides — the double-count risk the flag comment named is resolved
  structurally, not by a comment.

### Component B — Run-log granularity (Review-M-1, distributor-only)

- The **zone** metered path already logs this correctly: `_run_valve_metered` records
  `RUN_RESULT_PARTIAL` when `stopped or timed_out` (`timed_out = real_flow and delivered <
  target_volume`, irrigation.py:768-782). Only the **distributor** drops the signal.
- Fix: the sweep stops discarding `stopped_early` (distributor.py:1210) and passes it to
  `_dist_credit_zone`, which logs `RUN_RESULT_PARTIAL` when the run reached its `cap` **without**
  reaching its target volume, and `RUN_RESULT_COMPLETED` otherwise (target reached / normal).
  Reuses the existing `partial` chip/label — no new i18n.

### Component C — Calibration advisory (distributor members only)

- **Scope — distributor members.** The advisory needs BOTH a flow measurement AND a can't-stop
  run. Standalone service/self-closing zones run via `async_run_self_closing` with no flow poll
  loop (no measured volume); standalone linked/classic metered zones (`_run_valve_metered`) always
  early-stop at target and already log `partial` on a cap timeout. The one place both conditions
  meet is a **distributor member** whose valve cannot early-stop (`can_stop` False,
  distributor.py:1120-1123) — its window is still metered via the shared inlet, so a wrong
  `throughput` shows up as consistent over/under-delivery with no self-correction.
- **Signal — the observed FLOW RATE, not the volume.** (Code-review correction 2026-07-12.)
  Inferring a throughput error from a volume deviation is wrong: volume deviation absorbs the zone
  multiplier (a correctly-calibrated member with multiplier ≠ 1 would deviate permanently), manual
  custom-duration runs, and the maximum_duration clamp. The clean, robust quantity is the **observed
  rate** `observed_lpm = measured_l ÷ (seconds ÷ 60)` — the true physical flow, immune to all three.
  Compare it against the configured throughput in the same unit (`_throughput_lpm(zone)`, L/min).
- **Sampling:** on each such member run, append `observed_lpm` to a new capped per-zone store field
  `flow_calibration_samples` (keep the last `FLOW_CAL_MAX_SAMPLES`). Only **scheduled** runs with a
  **reliable** `measured_l` (not a time-based fallback, not a `duration_override` manual run) are
  sampled.
- **Trigger:** with ≥ `FLOW_CAL_MIN_SAMPLES` (3), let `cfg = _throughput_lpm(zone)` and
  `mean_obs = mean(samples)`. If `|mean_obs − cfg| / cfg > FLOW_CAL_DEVIATION` (0.15) → raise **one**
  HA `persistent_notification`.
- **Message:** names the zone, the direction (over/under-watering), and a **recommended throughput**
  = `mean_obs` presented in the user's throughput unit (L/min metric, GPM imperial — convert), versus
  the configured `throughput` (raw display value). Recommendation only — nothing auto-applied. The
  service call is wrapped in try/except so an advisory failure can never strand the inlet/master.
- **Self-clearing (no spam):** a per-zone `flow_calibration_advised` marker is set when the
  notification fires and cleared once the rolling mean returns within ±15%; re-notify only after
  it has cleared.

## Not doing (YAGNI)

- No new user-facing toggle — detection is by unit; the existing `flow_sensor` field is reused.
- No auto-apply of the recommended throughput (advisory only).
- No per-run persisted totalizer baseline for mid-run restart — the reader re-seeds `last` from
  the live sensor each call (a restart mid-window loses the in-window baseline and falls back to
  time-based, same fail-safe as today). Documented limitation; revisit only if it bites in the
  live test.
- No advisory for standalone zones — metered linked/classic zones already early-stop at target
  and already log `partial` on a cap timeout (irrigation.py:768-782); standalone service zones are
  unmetered. The advisory adds value only for can't-stop distributor members.

## Testing

Unit tests (canonical env: `.venv` 3.12 + HA 2024.12.5, `-p _local_socket_unblock`):
1. Shared unit helper: rate iff `/`; `total_increasing` → totalizer; conversions m³/L/gal.
2. Zone cumulative: totalizer deltas credit measured volume + early-stop; a glitch-low/reset (`cur < last`) contributes 0 + keeps baseline (transient dip absorbed on recovery, never over-credits); first interval captured via valve-open seed; dry meter → fault; `gpm`/`lpm` stay rates.
3. Distributor cumulative: existing monkeypatch tests updated for the retired flag (now always active for totalizers).
4. M-1 (distributor): sweep run that hit cap without target → `partial`; target reached / normal → `completed`. Regression: the zone path still logs `partial` on timeout (unchanged, irrigation.py:768-782).
5. Advisory: ≥3 samples mean >15% → one notification with the right recommended l/min; <3 or in-band → none; self-clear + re-notify after clearing; a can-stop member (classic / service with stop_service) → never sampled/notified; only reliable measured runs sampled.

`black`/`ruff` clean. **Then HA-Test live verification against the real totalizer meter** (the open hardware gate) before the prod release.

## Delivery

- Fork release (next CalVer): source cherry-pick onto `production` + version bump (all three) +
  dist rebuild (frontend touched only if help/tooltip reword is included — see below).
- Optional i18n follow-up: the `flow_sensor` help/tooltip currently says rate-only
  (en.json:747/969) — reword to mention totalizer support (all 8 languages) if included this round.
- Design/plan docs → `archive/design-history`.
- Upstream (JustChr) PR: separate later decision.
