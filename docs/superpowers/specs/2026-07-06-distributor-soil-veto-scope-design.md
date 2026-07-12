# Distributor soil-moisture veto scope — Design

Date: 2026-07-06
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 2 (a) (see memory `hasi-distributor-fix-roadmap`, `hasi-distributor-soil-veto-scope`)

## Problem

In a scheduled distributor cycle, `_dist_run_sweep` applies the soil-moisture veto
to the **whole** member ring, BEFORE the due-check and BEFORE the target-subset
filter (`distributor.py`, scheduled `else` branch):

```python
survivors = await self._apply_soil_moisture_veto(list(members))   # WHOLE ring
survivor_ids = {m[ZONE_ID] for m in survivors}
to_water = {m[ZONE_ID] for m in members if m[ZONE_ID] in survivor_ids and _dist_needs_water(m)}
if only_zone_ids is not None:                                      # subset filter AFTER
    to_water = {zid for zid in to_water if zid in allow}
```

So on a subset-targeted cycle (schedule targets e.g. `{Test2, Test4}` of a `{Test2,
Test4, Test6}` ring), a wet non-targeted member (`Test6`) still gets its bucket
re-anchored to 0 + a soil-skip run-log entry + a `zone_skipped` event — even though
the cycle would never water it. This is functionally correct (FAO-56 soil-truth
assimilation) but is an **asymmetry** with the normal-zone path, which vetoes only
the zones actually in the run: `_irrigate_linked_entities` filters `zones_to_irrigate`
to due zones BEFORE `_apply_soil_moisture_veto`.

This is a scope/UX decision, not a bug — the observed re-anchor was correct.

## Decision (user, 2026-07-06)

**Scope the veto to the cycle's watering candidates** — the members this cycle would
actually water (due AND, if a subset target is set, in the target). A wet member that
is non-targeted OR non-due is left untouched; it is re-anchored on its OWN cycle. This
matches the normal-zone path and removes the surprise off-scope re-anchors/skip-logs.

## Design

Reorder the scheduled `else` branch: build the watering candidates FIRST (due,
intersected with the target subset), then veto ONLY those. The separate `only_zone_ids`
subset filter folds into this pre-filter.

```python
if self._rain_delay_active():
    return False
# Soil-veto scope (2026-07-06): veto ONLY the members this cycle would actually
# water — due, intersected with the target subset — so a wet member that isn't this
# cycle's target (or isn't due) is left untouched (re-anchored on its OWN cycle),
# matching the normal-zone path (which vetoes only due zones).
allow = None if only_zone_ids is None else {int(z) for z in only_zone_ids}
candidates = [
    m
    for m in members
    if self._dist_needs_water(m)
    and (allow is None or int(m.get(const.ZONE_ID)) in allow)
]
survivors = await self._apply_soil_moisture_veto(candidates)
to_water = {m.get(const.ZONE_ID) for m in survivors}
if not to_water:
    return False
```

### Effect

- The veto (bucket re-anchor + skip-log + `zone_skipped` event) touches ONLY the
  cycle's targeted+due members.
- A wet **non-targeted** member (subset cycle) → untouched.
- A wet **non-due** member → untouched (today it is re-anchored; after this change it
  is not — consistent with the normal-zone path, which vetoes only due zones).
- A targeted+due+**wet** member → still vetoed + skip-logged (unchanged, visible in
  Recent runs).
- The physical ring still skip-pulses every non-`to_water` outlet between `current`
  and the last watered one (unchanged — the sweep/early-stop logic downstream is
  untouched).

### Visibility

Resolved as a consequence of the scope decision: the only bucket changes now happen on
vetoed (targeted+due+wet) members, which each get the standard soil-skip run-log entry
(`_record_run(SKIPPED, SKIP_REASON_SOIL_MOISTURE)`) plus the `zone_skipped` event. No
silent off-scope bucket change remains to be confused with a watering credit.

## Rationale

- **Consistency:** aligns the distributor path with the normal-zone path (filter to
  due, then veto) on both dimensions (targeted + due).
- **No over-water risk:** a non-targeted/non-due wet member keeps its (possibly
  open-loop-drifted) deficit only until a cycle actually targets it — at which point
  the veto re-anchors it BEFORE watering. So delaying assimilation never causes an
  over-guss; it only defers the bucket reset to the member's own run.
- **Less noise:** non-targeted members no longer accumulate soil-skip entries on
  unrelated subset cycles.

## Tests (TDD)

New regression tests (cycle-level, scheduled non-test non-force path):
- A subset-targeted cycle with a wet **non-targeted** member does NOT veto/re-anchor it
  (`_apply_soil_moisture_veto` never sees it; its bucket + run-log untouched).
- A wet **non-due** member is not re-anchored.
- A targeted+due+**wet** member IS vetoed (dropped from `to_water`, skip recorded) —
  unchanged behaviour.

Must stay green: the existing subset-target cycle tests (a subset run waters ONLY the
targeted members; non-targeted-but-due members are skip-pulsed, not watered) and the
soil-veto unit tests in the normal-zone path.

## Out of scope

The normal-zone veto (unchanged), the soil-veto mechanism itself (sensor read,
re-anchor value, fail-open), and the other Phase 2 design questions (foreign-pulse
without watch; self-closing watch field).
