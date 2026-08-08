# No-demand run-log — PR #71 review follow-up (Option C)

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-08-01  ·  **PR:** https://github.com/JustChr/HAsmartirrigation/pull/71  ·  **Branch(es):** local/log-no-demand
**Commit(s):** 302bfed1, 2bd05be5, f5ce12fe, 5d74d3ba, 388fe63a

## Problem / Context
The base opt-in no-demand run-log feature (spec+plan `2026-07-11-log-no-demand-skips`, already archived) was live and PR #71 was open. JustChr's review returned **CHANGES_REQUESTED**, raising a design question plus nits. The run log is bounded at `RUN_LOG_MAX_ENTRIES` (50) and previously trimmed with a plain oldest-first `del log[MAX:]`. With `log_no_demand` on, a zone that rarely waters writes one `no_demand` entry per day, so under a plain trim those markers steadily push the zone's **real** runs out of history — the log becomes least useful for exactly the zone the user is trying to understand. Separately, the off-path was doing avoidable work and a German label had a bad close-quote.

## Options considered
Only the log-overflow trade-off is recorded: a plain oldest-first trim (baseline, lets `no_demand` rows evict real runs) versus the chosen **Option C**. The "Option C" label implies alternatives were weighed on the PR thread, but their content is not in the record.

## Decision
Adopt **Option C**: on overflow, evict the OLDEST `no_demand` entries first, falling back to trimming the oldest overall only when none remain — a `no_demand` entry can never displace a real run. Also: gate the `no_demand` call sites on the flag (review nit **N1**, off-path is a pure no-op), fix the `de.json` close-quote (U+201C), and dedup by scanning the whole log rather than only the newest entry (review finding **H**). Rebased onto current `upstream/master` (incl. #67 keep-both, #70), dist bundles rebuilt, CI green.

## Implementation
`irrigation.py` `_record_run` gained the Option C eviction loop; `_record_no_demand_skips` now scans for any today-dated `no_demand` entry instead of only `log[0]`, preserving the one-per-zone-per-day invariant across an intervening same-day run. N1 flag-gates the call sites in `irrigation.py` (`_irrigate_linked_entities`) and `distributor.py` (`_dist_run_sweep`); `de.json` quote corrected. Merged via squash `5d74d3ba`. JustChr then filed follow-up `388fe63a`: Option C's scan started at index 0 — the just-inserted entry — so on a log full of real runs the new `no_demand` marker evicted itself and nothing recorded; fixed by starting the scan at index 1, softening the invariant to "`no_demand` never occupies more than one slot". Backlog M1/M2/M3 stayed LOW (not in PR).

## Evidence
- PR: https://github.com/JustChr/HAsmartirrigation/pull/71
- Commit(s): 302bfed1 — protect real runs from no_demand log eviction (Option C); 2bd05be5 — dedup by scanning the log (finding H); f5ce12fe — keep the off-path free (N1) + fix German close-quote; 5d74d3ba — squash-merge "feat: opt-in no-demand run logging (#71)"; 388fe63a — stop the incoming entry from evicting itself (JustChr follow-up)
- Tests: tests/test_no_demand_logging.py
- Memory: [[hasi-no-demand-logging]]

## Related
Base spec+plan `2026-07-11-log-no-demand-skips` (archived on `archive/design-history`) · [[hasi-pr-build-recipe]] · [[hasi-production-on-upstream]] · [[preserve-design-docs-archive-branch]] · [[hasi-distributor-fix-roadmap]]
