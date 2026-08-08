# Drop the unused run_data/stop_data zone fields (refactor)

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-08  ·  **PR:** —  ·  **Branch(es):** refactor/drop-run-stop-data
**Commit(s):** fca1dfd4

## Problem / Context
The self-closing "service" watering mode carried two optional per-zone dicts, `run_data` and `stop_data`, meant to be merged into the run/stop service calls. In practice nothing ever set them and they were never surfaced in the UI or config API. The `run_service`/`stop_service` plus `duration_field` settings already cover the service call fully, so the two fields were dead weight.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Remove the two `ZoneEntry` fields, their constants, and the call-site merges. No storage-version bump was needed: the load path already strips unrecognized keys, so any legacy stored `run_data`/`stop_data` is dropped cleanly on the next load.

## Implementation
`const.py` drops the `ZONE_RUN_DATA` and `ZONE_STOP_DATA` constants. `store.py` removes the `run_data`/`stop_data` attrs from `ZoneEntry` and their `zone.get(...)` reads in the load path. In `self_closing.py`, `_sc_service_open` and the early-stop branch now build `data = {}` directly instead of seeding it from the dropped dicts.

## Evidence
- PR: —
- Commit(s): fca1dfd4 — refactor(self-closing): drop the unused run_data/stop_data zone fields
- Tests: tests/test_self_closing.py, tests/test_store_self_closing.py
- Memory: —

## Related
[[hasi-self-closing-spec]]
