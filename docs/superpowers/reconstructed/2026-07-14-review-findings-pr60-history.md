# Post-merge adversarial review findings

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-14  ·  **PR:** https://github.com/JustChr/HAsmartirrigation/pull/60  ·  **Branch(es):** fix-review-findings
**Commit(s):** aeee6661

## Problem / Context
After JustChr's own flow-engine ultrareview (#59), the question was whether more latent bugs hid in the freshly merged distributor/observed/metered work (PRs #40+). An in-session multi-agent adversarial review (5 subsystem reviewers + a verify pass) surfaced **10 confirmed findings (1 high) plus 1 plausible; verify refuted 4 false alarms.** The high-severity one (A): the scheduler reset the days-since-irrigation counter even for a zero-water run (rain-delayed or fully soil-vetoed), so the days-between guard then skipped the next due run and stranded the zone dry.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Fix every verified finding in one PR, each backed by a new/extended regression test (TDD per fix), on a `fix-review-findings` branch cut from upstream/master. One borderline finding (K, minute-hardware master timing) was deliberately **not** changed — a naive fix would worsen bucket accounting — and left as a body note only.

## Implementation
Nine fixes across seven modules. `scheduler.py` gates the days-since reset on a "delivered water" bool now returned by `_irrigate_linked_entities`/`_dispatch_distributor_cycles`. `distributor.py` skips the rain-delay guard for manual (duration_override) member runs and books a ring advance for the defensive inlet-close on mid-watering restart. `self_closing.py` tracks/cancels the per-zone cleanup timer handle and reconciles an early-stopped bucket from measured volume. `irrigation.py` tightens the observed-watering suppression window when the valve actually closes (linked and rotating-slot). `store.py`, `services.py` and `websockets.py` carry the max-bucket clamp guard, `ZONE_STATES` validation, and the weather-watermark strip on zone save.

## Evidence
- PR: https://github.com/JustChr/HAsmartirrigation/pull/60
- Commit(s): aeee6661 — fix: address post-merge adversarial-review findings across metered/distributor/scheduler paths
- Tests: tests/test_distributor_cycle.py, tests/test_distributor_dispatch.py, tests/test_distributor_integration.py, tests/test_metered_run.py, tests/test_scheduler.py, tests/test_self_closing.py, tests/test_service_handlers.py, tests/test_store.py
- Memory: [[hasi-review-findings-pr60]]

## Related
[[hasi-unified-flow-engine]] · [[hasi-production-on-upstream]] · [[hasi-no-demand-logging]]
