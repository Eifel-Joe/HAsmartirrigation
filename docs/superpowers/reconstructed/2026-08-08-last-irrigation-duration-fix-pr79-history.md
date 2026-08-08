# Stamp last_irrigation + reset duration for all direct-credit runs

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-08-08  ·  **PR:** https://github.com/JustChr/HAsmartirrigation/pull/79  ·  **Branch(es):** fix-self-closing-last-irrigation → fix-last-irrigation-direct-credit
**Commit(s):** b3291b61, ac3bdda3

## Problem / Context
On HA-Prod (2026-08-05) self-closing zones (Kirschlorbeer/Beet) showed a "Letzte Bewässerung" timestamp three weeks stale and a frozen "Dauer", despite watering daily. Three run-paths credit the moisture bucket directly — self-closing (`_sc_finish_run` / `async_stop_self_closing`), distributor members (`_dist_credit_zone`), and observed watering (`_credit_observed_watering`) — and none pass through `_commit_run_progress`, the only path that stamps `ZONE_LAST_IRRIGATION` on water flow. The store's `bucket == 0 → duration 0` shortcut also missed, because a metered/observed run lands the bucket slightly positive (overshoot), never exactly 0, so "Duration" never reset either. The watering decision itself was always correct — bucket, "irrigation needed" and the days-between guard were unaffected; only the two display sensors were stale.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Add one shared helper that reproduces the free bookkeeping a metered run gets, rather than patching each finalize path independently. It stamps `last_irrigation` when water was delivered and zeroes duration once an automatic zone is left satisfied (`bucket >= 0`) — a strict superset of the store shortcut that also covers overshoot. Commit b3291b61 first fixed the self-closing/distributor paths; ac3bdda3 generalised it to observed watering (a REGEL-8 sister check) and is the final PR #79 state, rebased onto upstream v08.06's `async_write_watered_bucket`.

## Implementation
`irrigation.py` gains `_stamp_run_finalized(zone_id, volume_l)` beside `_commit_run_progress`/`_record_run`. It is called from `self_closing.py` (both `_sc_finish_run` and `async_stop_self_closing`) and `distributor.py::_dist_credit_zone`, after the bucket write. `observed_watering.py` already stamped `last_irrigation` itself but never reset duration, so the same `automatic & bucket>=0 → duration 0` reset is folded into its `async_write_watered_bucket` extra-changes so the credit keeps its own timestamp.

## Evidence
- PR: https://github.com/JustChr/HAsmartirrigation/pull/79
- Commit(s): b3291b61 — fix(runner): stamp last_irrigation + reset duration for self-closing/distributor runs; ac3bdda3 — fix(runner): stamp last_irrigation + reset duration for all direct-credit runs
- Tests: tests/test_self_closing.py, tests/test_distributor_cycle.py, tests/test_experimental_features.py
- Memory: [[hasi-last-irrigation-duration-fix]]

## Related
[[hasi-unified-flow-engine]], [[hasi-production-on-upstream]], [[hasi-pr-build-recipe]], [[hasi-review-findings-pr60]]
