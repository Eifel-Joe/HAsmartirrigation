# Unified Flow-Measurement Engine (rate · per-run counter · lifetime totalizer)

> **Status:** approved (design), 2026-07-13
> **Base:** `production` 6ad28d1 (v2026.07.17). Fork release first; upstream (JustChr) PR decided separately later.
> **Supersedes:** the totalizer handling shipped in v2026.07.17 (CFV-3 zone reader + distributor delta-accumulation), which assumed lifetime-totalizer semantics and is fragile for per-run-reset counters.

---

## REVISION 1 (2026-07-13) — cross-run learning replaces the single-run `auto` heuristic

**Why:** adversarial verification of the first engine build proved the single-run `auto`
detection (§1/§4 below: "a near-zero drop within `reset_window_s` is a reset") **can
over-credit**. A per-run RESET and a lifetime totalizer that glitches to near-zero then
only *partially* recovers are indistinguishable **within one run** from the values alone
(`1000 → 0.5 → 800` credited 799.5 L, but a monotonic lifetime meter delivered 0). Since
"never over-credit — under-credit safely" is a hard rule, single-run auto-detection is
unsafe. The user chose **cross-run learning**. This section supersedes the auto parts of
§1 and all of §4; the `per_run`/`lifetime`/rate mechanics and §2/§3 stand as amended here.

### R1.1 The pure engine (`FlowMeter`) — explicit type only, no in-engine `auto`

`FlowMeter(counter_type, *, near_zero_frac=0.1, near_zero_floor=1.0)` where `counter_type`
is resolved by the caller to **`per_run`** or **`lifetime`** (anything else, incl.
`auto`, is treated as `lifetime` — the over-credit-safe default). The `reset_window_s`
parameter and the deferred-confirmation machinery are **removed**. Totalizer branch:

- **`lifetime`** — pure keep-baseline: `litres >= last` credits `litres - last`; a drop
  (`litres < last`) keeps `last` and credits nothing. **Never over-credits** (the CFV-3
  invariant). A per-run counter under `lifetime` under-credits (→ time-based fallback).
- **`per_run`** — reseed the baseline **exactly once**, on the *first* near-zero drop
  (`litres <= max(near_zero_floor, near_zero_frac x last)`) — the valve-open reset —
  then keep-baseline for the rest of the run. Credits the run's climb from the reset
  floor. The "reseed once" bound means a later mid-run near-zero glitch is a glitch
  (kept, not reseeded), so `per_run` cannot over-credit a genuine per-run counter.

Rate branch unchanged (integrate `rate x dt`, monotonic-safe on `at`). `delivered()`
returns `None` if no numeric reading was ever seen, else the cumulative (0.0 for dry).
The engine also exposes `last_total()` → the last totalizer litres seen (or `None` for a
rate sensor) for the learning layer's end-of-run value. Pure functions `flow_is_totalizer`,
`flow_litres_from_total`, `flow_rate_to_l_per_min` stay; two pure learning functions are
added (R1.2).

### R1.2 The learning layer (across runs) — resolves `auto` to `per_run`/`lifetime`

Per flow-sensor owner (each **zone**, and each **distributor**), two additive store fields
(default absent, no `STORAGE_VERSION` bump):
- `flow_last_end` (float | None) — the sensor's litres value at the *previous* run's close.
- `flow_reset_streak` (int, default 0) — consecutive runs whose open showed a reset.

Two pure functions (in `flow_metering.py`, unit-tested):
- `flow_learn_next_streak(prev_end, start_litres, streak) -> int` — no observation
  (`prev_end` is None or `<= FLOW_LEARN_MIN_PREV_END`=1.0) → streak unchanged; a **reset**
  (`start_litres < FLOW_LEARN_RESET_FACTOR x prev_end`, factor 0.5) → `streak + 1`; else
  (monotonic: `start >= 0.5 x prev_end`) → `0`.
- `flow_learn_resolve(override, streak) -> "per_run" | "lifetime"` — `override` if it is an
  explicit `per_run`/`lifetime`; else (auto) `per_run` when
  `streak >= FLOW_LEARN_RESET_STREAK_THRESHOLD` (=2), else `lifetime`.

**Behaviour:** a per-run counter is auto-measured from its **~3rd run** (two consecutive
open-resets classify it); the first ~2 runs resolve to `lifetime` → time-based fallback
(safe learning phase). A genuine lifetime counter never accumulates a streak → always
`lifetime`. Requiring **two** consecutive open-resets means a one-off glitch can't flip it;
mis-classification needs two precise consecutive open-glitches on a lifetime sensor
(negligible), and even then the `per_run` reseed-once bound limits the exposure. The
learning is self-correcting: a monotonic observation zeroes the streak.

### R1.3 Integration hooks (each metered path)

At run **start** (after reading the sensor to seed the meter): if the sensor is a
totalizer, compute `start_litres`, update `flow_reset_streak` via `flow_learn_next_streak`
(persist it), resolve the type via `flow_learn_resolve` (override wins), and build the
`FlowMeter` with the resolved type. At run **end**: persist `flow_last_end =
meter.last_total()` (skip when None). Shared base-mixin helpers keep this DRY across the
three paths; each path persists via its own store (`async_update_zone` /
`_dist_store_update`). The distributor inlet counter's reset cadence (per cycle vs per
outlet) is less certain — it uses the same mechanism keyed on the distributor and is a
**live-verification** item; until it learns, it is `lifetime`-safe.

### R1.4 Frontend `flow_counter_type`

The per-zone override select (shown only for totalizer-unit sensors) is unchanged
(`auto`/`per_run`/`lifetime`, default `auto`). `auto` now means "learn across runs"
rather than "detect within one run" — the help text says so. `flow_last_end` /
`flow_reset_streak` are internal (not surfaced).

---

## Problem

Flow measurement lives in three separate, inconsistent places, and none robustly handles a
**per-run-reset** volume counter (the common Sonoff/Z2M valve sensor):

1. **linked-entity zones** — `_run_valve_metered` / `_read_flow_increment` (irrigation.py:586-729).
   The v2026.07.17 totalizer branch accumulates deltas with a keep-baseline glitch guard and seeds
   at valve-open. On a **per-run counter** whose value at open is still the previous run's total
   (or races the reset), the stale-high baseline suppresses the whole climb → 0 measured → falls
   back to time-based. Correct only for lifetime totalizers.
2. **service / self-closing zones** — `async_run_self_closing` (self_closing.py) credits
   `_timed_volume_l` (throughput × time) **only**; the `flow_sensor` field is never read. No
   measurement at all.
3. **distributor members** — `_dist_measure_window` (distributor.py:513-579) accumulates deltas
   with a reset-as-unreliable guard. Same per-run-counter blind spot as (1).

**Verified live (2026-07-13, HA-Prod `sensor.wasser_hinten_..._volume`, a Sonoff per-run counter,
unit `L`):**
- On valve-open the sensor resets from the previous value (62) to **0 within ~6 ms** — a **per-run
  cumulative counter**, not a lifetime totalizer.
- It climbs in 1-L steps during the run and **holds the final value after close** (stable until the
  next run resets it).
- A manual 2-min run delivered a measured **12 L**, while the time-based estimate (4 L/min) was
  **8 L** — a 50% under-count. This is exactly the accuracy the engine recovers.

The user's whole prod setup is three **service** zones (two with such a per-run counter), so today
none of their zones are metered, and (1)/(3) would mishandle their sensor type if used.

## Goal

One **shared flow-measurement engine** that correctly measures delivered litres for:
- a **rate** sensor (unit contains `/`) — integrate `rate × Δt`;
- a **per-run counter** (resets toward 0 at valve-open) — credit the run's accumulated climb;
- a **lifetime totalizer** (monotonic across runs) — credit the end−start delta;

used by **all three** metered paths (linked-entity, service, distributor), driven by the sensor
**unit + a reset-at-open observation**, with an optional per-zone override and safe time-based
fallbacks. The calibration advisory then also applies to service zones.

## Design

### 1. The engine — `FlowMeter`

A small stateful helper created at run start, fed one sensor reading per poll, and finalized at
run end. Lives in a new `flow_metering.py` (or on the base mixin); pure logic, unit-tested in
isolation.

```
FlowMeter(unit_hint?, counter_type_override="auto", *, now, reset_window_s, near_zero)
  .sample(value, unit, state_class, at)   # one poll reading
  .delivered()  -> float | None            # measured litres, or None -> time-based fallback
```

**Classification (per reading, resolved on the first non-None reading):**
- `state_class == "total_increasing"` OR (unit non-empty, no `/`, not a known abbreviated rate
  `gpm/lpm/gph/lph`) → **totalizer**; else → **rate**. (Reuses the shared `_flow_is_totalizer`.)

**Rate branch:** `delivered += _flow_rate_to_l_per_min(value, unit) * Δt / 60` (Δt since the last
sample). Unchanged from today's rate path.

**Totalizer branch** (`_flow_litres_from_total` converts each reading to litres):
- First reading → `last = litres`, `delivered = 0`.
- **Reset vs glitch discrimination** (the crux):
  - `counter_type == per_run` → the first significant drop toward ~0 is the reset: reseed
    `last = litres`, keep `delivered = 0`. (A per-run counter is expected to reset.)
  - `counter_type == lifetime` → a drop is **never** a reset; always a glitch (keep `last`, add
    nothing).
  - `counter_type == auto` → a drop is a **reset** iff it happens within `reset_window_s` of run
    start **and** falls to near zero (`litres <= near_zero`, e.g. ≤ max(1, 0.1×last)). Then reseed
    `last = litres`. Any other drop (later, or not near-zero) is a **glitch** (keep `last`).
- On a rising reading (`litres >= last`): `delivered += litres - last; last = litres`.
- On a glitch (`litres < last`, not a reset): keep `last`, add nothing (the CFV-3 keep-baseline fix
  — never over-credits on a transient dip or rebound).
- This unifies both totalizer types: a per-run counter reseeds at ~0 and accumulates the climb
  (→ final); a lifetime totalizer accumulates end−start; glitches never over-credit.

**Result / fallback:** `delivered()` returns the accumulated litres if a real signal was seen
(`delivered > 0` and at least one reliable reading), else `None` → the caller credits time-based.
Dry meter (valve open, no flow) → `None`. Rate/totalizer sensor unreadable throughout → `None`.

### 2. Per-zone override + unit-driven UI

- New per-zone store field `flow_counter_type` ∈ {`auto`, `per_run`, `lifetime`} (default `auto`),
  additive like `observed_entity` (no STORAGE_VERSION bump). Passed to the `FlowMeter`.
- **Frontend:** a new select in the zone settings, shown **only when the selected `flow_sensor`'s
  unit indicates a totalizer** (unit without `/`, or `state_class: total_increasing`) — read from
  `hass.states[flow_sensor]`. Hidden for a rate sensor (no ambiguity — always integrate) and when
  no `flow_sensor` is set. Same conditional-row pattern as the distributor `watch_mode` field.
  i18n label + option strings in 8 languages.

### 3. Integrations (all three paths call the engine)

- **linked-entity** `_run_valve_metered`: replace the inline `_read_flow_increment` totalizer/rate
  arithmetic with a `FlowMeter` fed each poll; credit `meter.delivered()` (fallback to the existing
  time-based path when it returns `None`). Retire the CFV-3 `_flow_last_total` seed/keep-baseline
  code (superseded by the engine).
- **service / self-closing** `async_run_self_closing`: this path is **fire-and-forget** (it opens
  the valve, credits the bucket optimistically, schedules a cosmetic finish, and returns — the
  hardware owns the close), so a *blocking* poll loop is wrong. Instead start **non-blocking
  interval sampling** (`async_track_time_interval`, cadence `FLOW_POLL_INTERVAL`) at valve-open,
  feeding a per-zone `FlowMeter`; finalize at `_sc_finish_run` / `async_stop_self_closing`: credit
  `meter.delivered()` (else `_timed_volume_l` as today) and correct the optimistic time-based
  bucket credit to the measured volume. Run timing is unchanged — only sampling + the correction
  are added. Then the member/zone **calibration advisory** (observed rate vs configured
  throughput) applies here too. (A restart mid-run loses the in-memory meter → time-based
  fallback, safe.)
- **distributor** `_dist_measure_window`: replace its inline delta-accumulation with the `FlowMeter`
  (same poll cadence, same cap/target early-stop semantics preserved — Part B early stop still
  breaks when `delivered >= target`). The per-run-counter blind spot is fixed for the shared inlet
  meter as a side effect.

### 4. Reset observation & the open window

The reset is only interpreted as a reset **within `reset_window_s`** of valve-open (default 30 s,
generous vs the observed 6 ms) under `auto`. Reading the sensor at/just after valve-open gives the
`start`; sampling then observes whether it drops (per-run) or climbs (lifetime). Because the engine
reads throughout the run (not only start/end), a delayed reset **inside** the window is still
caught. A reset delayed **beyond** the window under `auto` under-credits safely (falls back to
time-based, never over-credits); the user selects `per_run` to make any near-zero drop a reset
regardless of timing — the escape hatch for a genuinely delayed reset.

## Not doing (YAGNI)

- No new user toggle beyond `flow_counter_type` (which is auto by default and only shown for
  totalizer sensors). Rate vs totalizer stays unit-driven.
- No mid-run early-stop for service/self-closing zones (they can't stop — unchanged); measurement +
  the advisory cover them.
- No attempt to recover the last ~1 poll interval of flow before close beyond a short settle read
  (documented minor under-count).

## Testing

Engine unit tests (`tests/test_flow_meter.py`, isolated, no HA): rate integration; per-run counter
(reset-at-open → final, incl. the verified 62→0→12 trace); lifetime totalizer (end−start); glitch
mid-run keeps baseline (never over-credits, incl. glitch-to-near-zero outside the open window);
override forces per_run/lifetime; dry/unreadable → None; delayed reset within the window.
Path tests: linked-entity metered run credits the engine value + falls back to time-based;
service run polls + credits measured + advisory samples it; distributor sweep unchanged early-stop +
engine value. Frontend: `flow_counter_type` row visible only for a totalizer-unit sensor.
Full suite green vs the pre-existing env baseline; `black`/`ruff` clean. Then **HA-Test/Prod live
verification** against the real per-run counter (measured vs time-based, all three sensor types if
available).

## Delivery

Fork release (next CalVer) — source cherry-pick onto `production` + version bump (all three) + dist
rebuild (frontend touched: the new field + i18n). Design/plan docs → `archive/design-history`.
Upstream (JustChr) PR: separate later decision. **REGEL-8:** the three integrations are sister
paths of one engine — verified together; the calibration advisory's scope widens from
distributor-members to any can't-stop measured run (service zones included).
