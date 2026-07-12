# Observed-watering for service & member zones — Design

**Date:** 2026-07-11
**Status:** Approved (design), pending spec review
**Type:** Feature (opt-in, additive) — extends JustChr's `observed_watering_enabled`

## Problem

JustChr's experimental "observed watering" (`observed_watering_enabled`, Setup →
Experimental) credits a zone's bucket when its valve runs **outside** Smart
Irrigation — a manual tap, an automation, etc. — estimated from run time ×
throughput, so the soil-moisture model stays honest.

But it only observes zones that have a **`linked_entity`**: in
`observed_watering.py::async_setup_observed_watering` the tracked set is built
solely from `zone.linked_entity`. Zones that water through a **service /
self-closing** valve (no `linked_entity`) and **distributor member zones** (which
water via the distributor's shared inlet) are never observed — so external
watering of those zones silently drifts the model.

## Goal

Make observed watering work for zones without a `linked_entity`:
- **Phase 1** — normal **service / self-closing** zones, via a new optional
  `observed_entity` on the zone.
- **Phase 2** (own spec/plan cycle) — **distributor member zones**, by reusing
  the distributor's existing `inlet_entity` watch.

The whole feature stays behind the existing `observed_watering_enabled` flag
(default off). Off ⇒ byte-identical to today.

## Non-goals

- No change to the crediting math (still run time × throughput, capped at
  `maximum_bucket`) — Phase 1 reuses `_credit_observed_watering` unchanged.
- No new field where an observable entity already exists: `linked_entity` zones
  are already covered; distributors already carry an `inlet_entity`.
- Phase 2 (distributors) is designed here at a high level but planned & built in
  its own cycle after Phase 1 ships.

---

## Phase 1 — normal service / self-closing zones

### 1. New zone field
- `ZoneEntry.observed_entity` (optional, default `None`) — the physical
  valve/switch entity to watch for external runs of a service-mode zone.
- Additive storage: hydrated in `async_load` via `.get(key, None)`, **no
  `STORAGE_VERSION` bump** (same pattern as `confirm_entity`). CRUD flows through
  the existing zone-update path; add the key to the zone websocket POST schema if
  that schema is explicit.

### 2. Frontend (zone settings)
- Render an entity picker (domains valve/switch/input_boolean, `|| null` clear —
  mirror `confirm_entity`) in the zone editor, **shown only when**:
  `watering_mode` is a service/self-closing mode **AND**
  `config.observed_watering_enabled` is on.
- The zone-settings view already fetches `config`; reuse that to read the flag
  (same mechanism the distributor zone-side gate uses).
- Label + `slot="description"` help in all 8 languages, in the register of the
  neighbouring service-mode fields.

### 3. Observer (backend)
- In `async_setup_observed_watering`, extend the `entity_map` build: for each
  zone, contribute `linked_entity` if set, **else** `observed_entity` if set. So
  a zone maps **at most one** watch entity (linked xor observed). Everything
  downstream (`_observed_state_changed`, `_credit_observed_watering`) is unchanged
  — it already keys on `entity → zone_id` and credits from run time × throughput.

### 4. SI-own-run suppression (mandatory correctness)
- Today `_note_si_valve(zone_id, run_seconds)` (which sets `_si_driven_until`) is
  called only from the linked-entity runner paths (`irrigation.py`). The
  self-closing runner (`self_closing.py`) does **not** call it — safe today
  because self-closing zones were never observed.
- With this feature, SI's own service run opens the same `observed_entity`, so the
  self-closing runner **must** call `_note_si_valve(zone_id, run_seconds)` at the
  point it drives the service, or the observer would double-credit SI's own runs
  (the runner already credits the bucket optimistically at start).
- `run_seconds` = the zone's planned duration for that run, so suppression covers
  the whole run window (mirrors the linked-entity path's use of `max_seconds`).

### 5. Edge cases
- A service zone with `observed_entity` unset ⇒ simply not observed (optional).
- A zone that changes mode: entity_map is rebuilt on every config/zone change
  (existing behaviour), so switching mode re-derives the watched entity.
- Feature off ⇒ `enabled` short-circuits before any entity is tracked ⇒ no
  behaviour change, no `_note_si_valve` effect (marker is harmless when unused).

### 6. Testing (TDD)
- Observer: a service zone with `observed_entity` + feature on → external
  open→close credits that zone's bucket (run time × throughput); feature off →
  not tracked. linked_entity still wins when both are notionally present.
- Suppression: an SI-driven self-closing run that opens `observed_entity` is
  **not** double-credited (marker set; observer ignores within the window).
- Frontend: the `observed_entity` row is visible only for service mode + flag on;
  hidden otherwise; `|| null` clear works.
- Storage: a zone loads with `observed_entity == None` when the key is absent.

---

## Phase 2 — distributor member zones (high-level design, own cycle)

Reuse the distributor's existing inlet watch — no new field (distributors already
carry `inlet_entity`, watched in both classic and self-closing modes via
`_dist_refresh_inlet_watch`).

- Extend the inlet handler so it tracks the **open duration** (off→on→off), not
  only the rising edge used today for position advance.
- On an **external** inlet open→close (`active_cycle` empty ⇒ not an SI cycle)
  when `watch_mode == count` and the open lasted **≥ `skip_pulse_seconds` + a
  small margin**: credit the member zone at the **current outlet** via the
  existing `_dist_credit_zone` (flow or timed), then advance the position as
  today.
- Shorter opens are ring-advance pulses → **not** credited.
- SI's own cycles are already excluded by the `active_cycle` gate in
  `_dist_on_inlet_pulse`, so no `_note_si_valve` equivalent is needed there.
- Gated on `observed_watering_enabled` like Phase 1.

---

## Overarching

- **Opt-in, default off** — feature off = today's behaviour exactly.
- **Upstream:** extends JustChr's own observed-watering feature → clean PR
  candidate for JustChr.
- **Process:** develop on `local/observed-watering-ext` (from `production`
  v2026.07.13). Ship Phase 1 fully (regression + review + release/test decision)
  before starting Phase 2. Design docs archived per the standing archive-branch
  rule; excluded from production/PR branches.
