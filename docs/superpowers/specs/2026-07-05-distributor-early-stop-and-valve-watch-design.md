# Distributor early-stop + inlet-valve watch — Design

**Date:** 2026-07-05
**Two independent features** (position-tracking theme), shipped together as beta b10.

---

## Feature 4 — Early-stop: end the cycle after the last due outlet (new default)

### Problem
`async_run_distributor_cycle` sweeps the **full** ring every cycle: from `current_outlet` through all `n` outlets, watering due ones, skip-pulsing the rest, and advancing after each — ending back at the start position (effectively "return to home"). When the due outlets are early in the ring, the trailing non-due outlets are skip-pulsed and paused for nothing.

### Behavior (new default)
The mechanical ring can only advance forward and cannot skip an outlet, so **leading** skip-pulses (to reach a *later* due outlet) are mandatory; only **trailing** ones are avoidable. The cycle now:
1. Builds the sweep order from `current_outlet` (`order = [members[(current-1+k) % n] for k in range(n)]`).
2. Determines `last_due_idx` = the highest index in `order` whose member is in `to_water` (the due set). (`to_water` is already computed; guard `if not to_water: return False` already returns before sweeping when nothing is due.)
3. Sweeps `order[0 .. last_due_idx]` inclusive (`k = last_due_idx + 1` outlets): waters due members, skip-pulses the leading non-due ones. **After the last due outlet the sweep stops** — no trailing skip-pulses of the non-due tail, no trailing inter-outlet pause.
4. Persists `current_outlet` = the last watered outlet **+ 1** (see b12 correction). The next cycle continues forward from there.

Loop shape: `for i in range(k): open/window/close; if i < k-1: pause + advance`; then **one terminal advance after the loop**. So `k` outlets, `k-1` inter-outlet pauses/advances, plus the terminal advance = `k` advances total, ring ends at `order[k-1] + 1`.

> **Correction (b12, 2026-07-05):** The original draft (points 3–4, loop shape) said the ring ends **on** the last watered outlet (`order[k-1]`, "no final advance"). That is **physically wrong**: a Gardena-style distributor indexes on every valve OFF / pressure-drop edge, so the last watered outlet's own pulse advances the mechanism one step — it can never rest on the outlet it just watered. Confirmed live (before=2, one 120 s pulse on outlet 2, stored stayed 2 while the ring stepped to 3) and by the mismatch with `_dist_on_inlet_pulse`, which already books one advance per pulse (`(cur % n) + 1`). Fix: a **terminal `_dist_advance` after the loop** so `current_outlet` = the outlet the ring now rests on = what the next pulse will water (= last watered **+ 1**, wrapping to home for a full ring). The **sweep** still stops early (trailing non-due outlets are not visited); only the recorded end position moves from last-watered to last-watered + 1.

### Interactions
- **`distributor_cycle_estimate`** (finish-anchor) must match the truncated sweep: order from `current_outlet`, find the last outlet with `duration > 0` (due), count only `order[0..last_due]` — sum their windows (due→duration, else skip) + `(k-1)·pause` + per-window settle (if the master cycles) + safety buffer. Returns 0 if none are due. This replaces the current "all n outlets + n pauses" formula. (The estimate approximates "due" as `duration > 0`, same as today; the executor's `to_water` also factors soil-veto, so estimate ≥ executed in edge cases — acceptable, same direction as today.)
- **Test-run** (`test_run=True`) is UNCHANGED — it sweeps ALL `n` outlets (it must test every outlet) and returns to start. Early-stop applies only to the normal watering path.
- **`resync_home` service** stays as the manual "set position to outlet 1" anchor.
- **Restart reconciliation** unchanged (mid-watering→synced abort, mid-pause→uncertain); position persistence after each step unchanged.
- **H7 master rolling notes** unchanged — a shorter sweep just means fewer notes and the master turns off after the (shorter) actual end. No regression.
- **`only_zone_ids` (H5) / member manual-run (b9)**: a single-outlet run already narrows `to_water` to one zone; early-stop naturally stops right after that outlet. Consistent.

### Scope: backend only (`distributor.py`). No config, no panel, no store change.

---

## Feature 5 — Inlet-valve watch: track foreign pulses to stay synced (opt-in)

### Problem
HASI is blind to ring advances it didn't cause. If the inlet valve is pulsed outside HASI's cycle, the physical ring advances but `current_outlet` doesn't — desync.

### Scope of the mitigation (explicit)
This catches ONLY **HA-observable** actuations — a pulse that produces a state change on the `inlet_entity` (HA-routed toggles, or a switch/valve entity whose state reflects the physical inlet). A purely **physical** pulse (Gardena manual override, or any actuation HA never sees) remains invisible. So this is a **partial** mitigation, not a cure for the fundamental blindness (spec ch. 8).

### Config
New per-distributor boolean `watch_inlet` (default **False**). Added to `DistributorEntry` (store, migration additive), the config POST/API, the panel distributor form (with a help note about the HA-observable limitation), and i18n (8 languages).

### Mechanic — own vs. foreign via `active_cycle` (no context/flag needed)
HASI pulses the inlet **only** during a cycle, and a running cycle always has a non-empty `active_cycle`. Therefore:
- Register a state listener on `inlet_entity` (`async_track_state_change_event`) **only** for distributors with `watch_inlet=True` and a state-observable `inlet_entity`.
- On an **off→on** edge (old state in {off, closed}, new state in {on, open, opening}):
  - If `active_cycle` is **non-empty** → it's HASI's own pulse → **ignore**.
  - If `active_cycle` is **empty** → **foreign** pulse → the ring advanced: `current_outlet = (current % n) + 1` (ring-wrap, `n` = member count), persist, keep `position_state = synced`, and fire `DOMAIN + "_distributor_updated"` so the entities refresh. If `n == 0` (no members) → ignore.
- Each off→on edge = one advance (matches the mechanism's per-pulse step); no debounce beyond edge detection.

### Lifecycle
The coordinator holds `{distributor_id: unsub}`. Register listeners on integration setup (for existing `watch_inlet` distributors) and on distributor create/update (register when `watch_inlet` turns on or `inlet_entity` changes; unregister when it turns off / the entity changes / the distributor is deleted). Mirror the existing distributor-signal wiring.

### Scope
`DistributorEntry` + store migration; `distributor.py` (listener register/unregister + the foreign-pulse handler); config API (accept `watch_inlet`); panel distributor form (`si-distributor-form.ts` + types + i18n 8).

---

## Testing
- **Feature 4 (unit):** early-stop stops after the last due outlet (assert the sweep visits `current..last_due` only, ring ends at last due, `current_outlet` persisted correctly); leading non-due outlets still skip-pulsed to reach a later due one; `test_run=True` still sweeps all `n`; `distributor_cycle_estimate` truncates (assert it counts only up to the last due outlet, not all `n`).
- **Feature 5 (unit):** off→on while `active_cycle` empty advances `current_outlet` with ring-wrap + stays synced + fires the signal; off→on while `active_cycle` non-empty is ignored; wrap at `n`; `n==0` ignored; listener registered only when `watch_inlet=True`; toggling `watch_inlet` off unregisters.
- HA listener wiring + panel verified live on 192.168.10.196.

## Out of scope (YAGNI)
- No per-outlet "expected next" prediction beyond +1 on a foreign pulse.
- No attempt to detect physical (non-HA) pulses.
- No change to the commissioning test-run sweep.

## Release
Bundle both into beta **b10** (version bump ×3, **rebuild dist** — panel changed, black, full pytest, prerelease). Re-verify: a schedule where only early outlets are due stops early (no trailing skip-pulses, position stays mid-ring); with `watch_inlet` on, a manual HA toggle of the inlet advances `current_outlet`.
