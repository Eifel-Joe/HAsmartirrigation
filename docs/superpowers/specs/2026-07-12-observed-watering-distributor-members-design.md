# Observed Watering — Phase 2: Distributor Member Zones

> **Status:** approved (design), 2026-07-12
> **Feature family:** observed watering (Phase 1 = service/linked zones v2026.07.14 + run-log v2026.07.15; this = Phase 2, member zones)
> **Fork release target:** v2026.07.16 (Eifel-Joe). Upstream (JustChr) PR: bundled with all observed-watering work into ONE PR later.

## Problem

JustChr's *observed watering* (`observed_watering_enabled`, opt-in, default off) credits a
zone's bucket when its valve runs **outside** Smart Irrigation — run time × throughput.

Phase 1 extended the observer from `linked_entity` only to service/self-closing zones via a
new optional per-zone `observed_entity`, and made each credit write a persistent `observed`
run-history entry that counts into `water_used_total`.

**Gap:** member zones of a mechanical distributor have **no own valve** — water reaches them
through the single shared `inlet_entity`. The per-zone observer (which watches a zone's own
entity) is therefore blind to them. If the user waters the distributor externally (a Gardena
timer or a manual inlet open outside HASI), the served member zone is **never credited** and
its bucket drifts, exactly the problem observed watering exists to solve.

## Goal

An **external** inlet open→close that waters a distributor position credits the **correct**
current member zone's bucket and writes an `observed` run-history entry — consistent with
Phase 1. Short **advance pulses** (stepping the ring past an unmapped outlet) are **not**
credited. Smart Irrigation's own cycles are never double-credited.

## Existing machinery this builds on

- `_dist_refresh_inlet_watch` subscribes to `inlet_entity` state changes for `watch_mode`
  `count` and `warn` (never `ignore`).
- `_dist_inlet_state_handler` currently decodes **only** the `off→on` edge and defers to
  `_dist_on_inlet_pulse`.
- `_dist_on_inlet_pulse` acts only on **foreign** pulses (gated on `active_cycle` empty — SI
  pulses the inlet only inside a cycle, which always has a non-empty `active_cycle`):
  - `warn` → mark the distributor uncertain (de-arm + notify).
  - `count` → advance `current_outlet` by one: `(cur % n) + 1`.
- `_dist_members(distributor_id)` returns member dicts **sorted by `outlet_number`, 1..n**.
  The sweep treats `members[(current_outlet - 1) % n]` as "the outlet flowing now"
  (distributor.py sweep, ~line 966-968).
- `_dist_credit_zone(zone, seconds, measured_l=None, planned_seconds=None)` credits a member
  bucket (metered gross depth, or timed fallback via `_timed_volume_l`) and logs the run —
  today always `result=RUN_RESULT_COMPLETED`, `trigger=RUN_TRIGGER_DISTRIBUTOR`.
- `RUN_RESULT_OBSERVED = "observed"` (const) drives the teal `.history-observed` chip
  (Phase 1). Phase 1's observer logs `trigger="observed"` as a **string literal**.

## Design

### 1. Decode both inlet edges

`_dist_inlet_state_handler` gains an `on→off` branch that schedules a new async
`_dist_on_inlet_close(distributor_id)`. The `off→on` branch is unchanged — it still defers to
`_dist_on_inlet_pulse`, so all existing open-edge behaviour and tests stay intact.

### 2. Open edge — snapshot the watered outlet (no behaviour change)

Inside `_dist_on_inlet_pulse`, in the existing `count`-mode branch (foreign pulse,
`active_cycle` empty), **before** the position advance, stash an open record keyed by
distributor id:

```python
self._dist_observed_open_map()[distributor_id] = {
    "t": self.hass.loop.time(),
    "outlet": cur,   # 1-based ring index BEFORE the advance = the outlet now flowing
}
```

`_dist_observed_open_map()` is created lazily (mirrors `_dist_inflight_ids()`), so no
coordinator `__init__` change. The advance itself runs exactly as before.

Stashing happens **only** in the `count` branch. `warn` marks-uncertain and never stashes;
`ignore` registers no listener. SI cycles hit the `active_cycle` early return and never reach
the stash.

### 3. Close edge — `_dist_on_inlet_close` credits or discards

```
1. open = pop stash for this distributor; if None -> return (warn / ignore / SI open).
2. dist = store.get_distributor(id).
   Race guard (REGEL 8): if dist.active_cycle is non-empty -> an SI cycle claimed the inlet
   between open and close -> DISCARD, no credit.
3. If not observed_watering_enabled -> return (defensive: feature toggled off mid-open).
4. duration = hass.loop.time() - open["t"].
5. Threshold: if duration < 2 * skip_pulse_seconds -> advance pulse -> return (advance
   already happened on the open edge; only the credit is suppressed).
6. members = _dist_members(id); n = len(members); if n == 0 -> return.
   member = members[(open["outlet"] - 1) % n].
   If member is missing or state == DISABLED -> return.
7. await _dist_credit_zone(member, duration,
        result=RUN_RESULT_OBSERVED, trigger=RUN_TRIGGER_OBSERVED)
```

### 4. `_dist_credit_zone` gains result/trigger params (DRY)

```python
async def _dist_credit_zone(self, zone, seconds, measured_l=None, planned_seconds=None,
                            *, result=const.RUN_RESULT_COMPLETED,
                            trigger=const.RUN_TRIGGER_DISTRIBUTOR):
```

Defaults reproduce today's behaviour exactly (all existing callers unaffected). The observed
path passes `result=RUN_RESULT_OBSERVED, trigger=RUN_TRIGGER_OBSERVED` and `measured_l=None`
(external water is never metered by SI's own `_dist_measure_window`), so the timed fallback
credits `_timed_volume_l(zone, duration)` → bucket + `observed` run-log entry (teal chip) +
`add_to_total=True` → counts into `water_used_total`.

### 5. New const `RUN_TRIGGER_OBSERVED = "observed"`

Phase 1's observer currently logs the trigger as the literal `"observed"`. Introduce the
const and use it in **both** the observer and the new member path (small DRY tidy-up; belongs
in the same observed-watering feature family / PR).

## Gating & safety

- Active only when `observed_watering_enabled` **and** `watch_mode == count`.
- SI's own cycles excluded twice: `active_cycle` gate on the open edge (no stash) **and** the
  close-edge race guard (discard if a cycle is active at close).
- No double credit: member zones have no own valve, so the per-zone observer (which watches
  `linked_entity`/`observed_entity`) cannot also credit the shared-inlet water.
- Threshold `2 × skip_pulse_seconds` (default 30 s → 60 s) cleanly separates advance pulses
  (nominally `skip_pulse_seconds`, min 10 s) from real member runs (minutes), with margin for
  a jittery/long pulse.
- The threshold gates only the **credit**, never the **advance**: every foreign `count` pulse
  advances the ring (open edge) exactly as today; a short pulse simply skips the close-edge
  credit. This preserves position tracking unchanged.

### Known limitation (inherited, not introduced)

The credited member follows the tracked ring position — the same signal the SI sweep uses
(`members[(current_outlet - 1) % n]`). In sparse-outlet setups where the `count`-mode tracker
can drift from the physical ring (a pre-existing limitation of foreign-pulse resync), the
credit follows the tracker. Phase 2 neither worsens nor fixes this; SI's own cycles re-sync
the tracker. Documented here for honesty, out of scope to solve.

## Not doing (YAGNI)

- **No new config field** — reuses `observed_watering_enabled`, `watch_mode`,
  `skip_pulse_seconds`. No frontend/i18n changes; the Phase-1 `observed` chip is reused.
- **No metered observed credit** — external water has no SI flow-measurement window; timed
  fallback only. (A future enhancement could read a distributor `flow_sensor` during an
  external open, but it is out of scope here.)
- **No help-text change** — optional discoverability note deferred.

## Testing

Unit tests (coordinator built with `__new__`, Mock hass/store, stub the loop clock):

1. `_dist_credit_zone` default result/trigger unchanged (regression) — existing behaviour.
2. `_dist_credit_zone` with `result=observed, trigger=observed` logs an `observed` run and
   adds to total.
3. Open-edge stash: a foreign `count`-mode pulse records `{t, outlet}` (pre-advance index)
   and still advances the position.
4. Close edge credits the current member when `duration ≥ 2 × skip_pulse_seconds`
   (bucket rises, `observed` run-log entry written).
5. Close edge **does not** credit when `duration < 2 × skip_pulse_seconds` (advance pulse).
6. Close-edge race guard: `active_cycle` non-empty at close → no credit (SI cycle).
7. Close edge no-ops when `observed_watering_enabled` is off.
8. Close edge no-ops in `warn` mode (no stash was ever set).
9. Disabled / missing member at the current outlet → no credit.

Full suite green (canonical: `.venv` Python 3.12 + HA 2024.12.5, `-p _local_socket_unblock`),
`black`/`ruff` clean.

## Delivery

- Fork release **v2026.07.16** (Eifel-Joe): cherry-pick source commit(s) onto `production` +
  version bump. **No dist rebuild** (backend-only, no frontend change).
- Design/plan docs → `archive/observed-distributor-members-design-history`.
- Upstream (JustChr) PR: **not now.** When opened, bundle all observed-watering work
  (service-zones + run-log + this member phase) into ONE clean branch off `upstream/master`.
