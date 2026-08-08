# Drop server-owned run accounting from client zone save

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-13  ·  **PR:** —  ·  **Branch(es):** fix-zone-save-run-history-clobber
**Commit(s):** 7826185d

## Problem / Context
The panel saves a zone by POSTing the *whole* zone object to `SmartIrrigationZoneView.post`. That object carries server-owned run-accounting fields — `water_used_total`, the run log, and `last_irrigation` — from the browser's snapshot. If the zone-settings page was left open across an irrigation run, that snapshot is stale. Saving *any* setting (e.g. a rename) then overwrote the live values: it reverted the run's usage total and deleted its freshly written history entry. The runner writes these fields to the store directly, so a concurrent client save clobbered them.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Make the runner the sole writer of run accounting by stripping the three server-owned fields from any client save, rather than trying to merge or version the client snapshot. The client keeps authority over editable settings; run accounting flows only through the store.

## Implementation
In `custom_components/smart_irrigation/websockets.py`, `SmartIrrigationZoneView.post` now pops `ZONE_WATER_USED_TOTAL`, `ZONE_RUN_LOG`, and `ZONE_LAST_IRRIGATION` from the incoming `data` before calling `coordinator.async_update_zone_config`, so those keys never reach the store via a client path.

## Evidence
- PR: —
- Commit(s): 7826185d — fix(zones): drop server-owned run accounting from client zone save
- Tests: `tests/test_distributor_integration.py` (`test_zone_view_ignores_server_owned_fields` — asserts a legitimate `name` edit is forwarded while the three accounting fields are stripped)
- Memory: —

## Related
[[hasi-last-irrigation-duration-fix]]
