# Distributor master-hold leak on mid-sweep error

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-08-02  ·  **PR:** https://github.com/JustChr/HAsmartirrigation/pull/70  ·  **Branch(es):** fix-distributor-master-hold-leak
**Commit(s):** 36490a75 (cherry-picked from 3cebb54d)

## Problem / Context
Upstream v07.10 (`f7dc6c17`) reworked master-pump-off from a predicted deadline to a refcount **hold** model: every consumer takes a hold and the pump powers off only when the last one drops. A distributor sweep takes a `dist:<id>` hold in `_dist_master_start` and releases it in the terminal `_dist_master_end`. But `async_run_distributor_cycle`'s `except Exception` handler (audit C1) defensively closes the inlet and re-raises **without** reaching `_dist_master_end`. So an unexpected mid-sweep error (a store write inside `_dist_credit_zone`, a failing service call) leaks the hold. `master.py::_fire` returns while any hold remains and never powers the pump off, so the pump dead-heads against the closed inlet until the next same-distributor cycle re-acquires+releases the identical token or a restart reconcile — potentially ~a day on a daily schedule. `f7dc6c17` converted the start/end helpers to holds but left this except path (and its now-stale "rides its own scheduled-off deadline down" comment) unadjusted.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Release the hold in the except path via `async_master_release(self._dist_master_token(distributor))`. It is idempotent (a plain `set.discard`) and no-ops when no master is configured, so it is safe even if the sweep raised before `_dist_master_start`, and best-effort so a raising release cannot mask the original error. The `CancelledError` path was intentionally left untouched: on shutdown/reload the in-memory holds are dropped and `async_reconcile_master_after_restart` normalizes the master on boot, and awaiting a service call during cancellation is unsafe. A REGEL-8 sister-path check confirmed every other post-acquire exit either runs before `_dist_master_start` or already calls `_dist_master_end` — the except path was the only leak. On merge, JustChr added a `_dist_uses_master(distributor)` gate so a `use_master: false` distributor cannot shut down a shared master it never raised.

## Implementation
`custom_components/smart_irrigation/distributor.py` — added a best-effort master-release block (with logging) in the `except Exception` handler of `async_run_distributor_cycle`, after the defensive inlet close and before the `raise`; the stale master comment was trimmed.

## Evidence
- PR: https://github.com/JustChr/HAsmartirrigation/pull/70
- Commit(s): 36490a75 — fix(distributor): release the master hold on a mid-sweep error
- Tests: tests/test_distributor_cycle.py::test_errored_cycle_releases_the_master_hold
- Memory: [[hasi-distributor-master-refcount]]

## Related
[[hasi-distributor-master-overrun]] · [[hasi-distributor-restart-recovery]] · [[hasi-distributor-fix-roadmap]]
