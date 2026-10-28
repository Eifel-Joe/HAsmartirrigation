# SDD ledger — plan: D:/Entwicklung/HASI/HAsmartirrigation/docs/superpowers/plans/2026-10-23-weather-client-fetch-gate.md

Spec: D:/Entwicklung/HASI/HAsmartirrigation/docs/superpowers/specs/2026-10-23-weather-client-fetch-gate-design.md
Worktree: D:/Entwicklung/HASI/issue89-work/wt, branch fix/weather-client-fetch-gate, MERGE_BASE c46c41fc0ff688febbd74050c0602f9a2d35bc03
Global constraints for reviewers: global-constraints.md (verbatim from the plan)

## Pre-flight scan (2026-10-23)

| Pair / task | Produces --> consumes | Finding |
|---|---|---|
| T1 / T2 | `fetch_gate.is_fresh`, `cache_lifetime`, test table `CASES` --> FetchGate, concurrency test | consistent |
| T1 / T3 | `is_fresh` (patched to False in T1 test) --> gate's own `was_fresh` check | consistent: patched False → fetch every call, success path; T1 test still expects 2 calls |
| T2 / T3 | `FetchGate.run` (lock only) --> extended run with pause | consistent |
| T3 / T4 | `is_replay` --> `failure_log_level` | consistent; T3 tests assert no logs, so ERROR lines of Open-Meteo/Met Office in the pause are expected until T4 |
| T3 / T5 | `_retry_after = 0.0`, `_settle` --> Retry-After term in pause | consistent |
| T5 / T6 | `note_response` calls in Pirate loops --> loops replaced by `_get_with_retries` (which calls `note_response`) | consistent; T5 Pirate 429 assertion written count-agnostic |
| T3–T5 / T6 | Pirate failing runs in integration tests --> T6 adds `time.sleep` + autouse no-op fixture in the same test file | consistent |
| T2–T6 / T7 | gate internals --> mutations M1–M10 | consistent; M2 killer = T3 `test_waiters_served_from_cache_do_not_count_as_failures` |
| T0 | worktree + baseline | self-consistent |
| T1 | tests (is_fresh strict `<`) vs code rule (`now < fetched_at + lifetime`) | consistent |
| T2 | RED "5 == 1" vs 5 threads | consistent |
| T3 | backoff 60/120/240/480/599 vs cap min(60·2^(n−1), 599) | consistent |
| T4 | test assumes no precondition on first-call logs (OWM forecast logs nothing) | consistent after plan fix |
| T5 | `_resp(headers)` helper not defined in the brief | minor: obvious (MagicMock(headers=…)) |
| T6 | `import time` needed for sleep patch target | stated in task |
| T8, T9 | operational, approvals per external step | outside SDD loop |

Rulings:
- Ruling: Task 0 (worktree + baseline) is run by the controller, not a subagent — it writes no code and the commands are fixed verbatim in the plan — cost if wrong: none, nothing to review.
- Ruling: SDD artifacts live in the skill workspace (wt/.superpowers/sdd/…, git-ignored) instead of issue89-work\ as the handover text said; before the workspace is deleted, ledger + briefs + reports are copied to D:/Entwicklung/HASI/issue89-work/sdd/ for the P1 archive — cost if wrong: evidence lost if the copy is forgotten (Memory scratch-dirs-hold-irreproducible-evidence).
- Ruling: Tasks 8 (live test) and 9 (delivery) are not dispatched as SDD tasks; they need approvals per external step and run with the user after the final review — cost if wrong: none, the plan marks them approval-gated.
- Ruling: models — implementers sonnet; reviewers sonnet for T1/T4/T6, opus for T2/T3/T5 (lock, timing, retry logic); final review opus — cost if wrong: a weaker review on a subtle task.

## Progress

Task 0: baseline running (read-wt @ c46c41fc, output D:/Entwicklung/HASI/issue89-work/baseline/suite-c46c41fc.txt)
Task 1: dispatched (BASE c46c41fc, implementer sonnet)
Task 0: complete — baseline on c46c41fc: 7 failed, 4013 passed, 9 skipped, 496 errors (all teardown "Lingering timer"), 420 s; names (strict filter `^(FAILED|ERROR) tests/`): D:/Entwicklung/HASI/issue89-work/baseline/names-c46c41fc.txt (503 = 7 + 496)
Task 1: implementer DONE — commit 9a87d9b1; concerns: (1) trailer Opus vs Sonnet, (2) Open-Meteo `_fetch` with a doc but no stamp now refetches instead of TypeError (unreachable state), (3) extra files green, (4) pre-push grep must read message bodies only
- Ruling: commit trailer stays "Claude Opus 5.5" on every commit of the branch as the plan fixes, though implementers run on Sonnet — one uniform attribution for an orchestrated branch; JustChr squashes — cost if wrong: trailer names the orchestrating model, not the writing one.
- Ruling: Task 9 pre-push grep uses `git log --format=%B upstream/master..HEAD` (message bodies only), because the Author header "Eifel-Joe" would always match — cost if wrong: none.
Task 1: minor (deferred): Open-Meteo `_fetch` refetches on doc-without-stamp instead of TypeError (unreachable, disclosed in commit body)
Task 1: minor (deferred): commit trailer names Opus while implementer ran Sonnet (see ruling above)
Task 1: minor (deferred): shared MIN_CACHE_SECONDS comment keeps OWM wording "per method per minute"; Open-Meteo/Met Office rationale lines dropped — consider "per endpoint" wording
Task 1: minor (deferred): `cache_lifetime` docstring ~95 chars on one line
Task 1: minor (deferred): Task 1 test proves the shared check is consulted, not which stamp is passed (covered by existing tests)
Task 1: complete (commits c46c41fc..9a87d9b1, review clean)
Task 2: dispatched (BASE 9a87d9b1, implementer sonnet)
Task 2: implementer DONE — commit 7b5454b6; concerns: pre-push grep (ruled already), 189 teardown Lingering-timer errors in other files unbaselined at this step (Task 7 compares full-suite names), _owner/_stamp_attr unused until Task 3, no nested same-gate calls
Task 2: minor (deferred): interim — between Task 2 and Task 3 waiters behind a failed fetch each fetch in turn (serialised); Task 3 must prove waiters behind a failure make no request (RF1 test) — this commit must not ship without Task 3
Task 2: minor (deferred): test_weather_fetch_gate.py:133 `holder` thread not daemon (bounded wait, nit)
Task 2: minor (deferred): 189 teardown Lingering-timer errors in implementer's extra run (pre-existing class; Task 7 compares names)
- Ruling: the NOT-TO-DO wording at fetch_gate.py:58-60 ("clients run only in executor threads") is corrected in Task 3, which edits the same file: the real rule is that a gate must never be reached from a loop-side accessor (live_estimate.py:534/:572 call hourly accessors on the loop; they read caches only) — cost if wrong: one extra comment hunk in the Task 3 commit.
Task 2: complete (commits 9a87d9b1..7b5454b6, review clean)
Task 3: dispatched (BASE 7b5454b6, implementer sonnet)
Task 3: implementer DONE_WITH_CONCERNS — commit cb6c83ed; changed two Task 2 unit tests (failure-then-success on one gate now replays); added a gate-logger DEBUG test; concerns: _retry_after unused until T5, uncopyable-exception fallback marks the original (race with first caller's log level), _outcome retains traceback/frames until next fetch
Task 3: minor (deferred → carried to Task 5): order "freshness before pause" unpinned — a pause-first mutant survived all 48 tests; production path: __init__.py:1358 raises cache_seconds during an outage, an old stamp is fresh again and must be served (spec §3)
Task 3: minor (deferred → carried to Task 5): `_outcome` keeps the original exception with traceback/frames until the next fetch — store the replayable copy at settle time
Task 3: minor (deferred): uncopyable-exception fallback marks and clears the traceback of the original (unreachable from the seven paths per reviewer's copy check of 15 exception types)
Task 3: minor (deferred): Task-2 lock-release test now relies on the C10 bypass; asserting the replayed ValueError would decouple it
Task 3: minor (deferred): Open-Meteo 200 with JSON `null` → failures uncounted (pre-PR behaviour)
- Ruling: spec C5 text aligned to ruling 3 (cache_seconds read on every pause check, not only at the failure) — the code follows the controller's ruling and the spec's own rationale (interval changes later) — cost if wrong: none, wording only.
- Ruling: Task 5 (which edits `_settle`/`_pause_left`) also adds the pin test for freshness-before-pause and stores the replayable copy at settle time — both touch exactly the code Task 5 changes; a mutant surviving the brief's own "decision" is a gap worth closing before more edits — cost if wrong: two small extra hunks in the Task 5 commit.
Task 3: complete (commits 7b5454b6..cb6c83ed, review clean)
Task 4: dispatched (BASE cb6c83ed, implementer sonnet)
Task 4: implementer DONE — commit 49a5a3e8; two extra tests (Open-Meteo get_data/get_hourly_data accessors, unit test failure_log_level)
Task 4: minor (deferred → carried to Task 5): uncopyable-exception fallback marks the original — a waiter can mark the first caller's real failure before its accessor logs it → real failure at DEBUG (narrow race)
Task 4: minor (deferred → final fix wave): Met Office first real failure logging at ERROR is not pinned by a test (spec §5 item 7)
Task 4: minor (deferred): table log test couples to the gate's "replaying the last outcome" wording
Task 4: minor (deferred): no `siehe test_…` pointer at the five log sites (optional)
- Ruling: Task 5 replaces the uncopyable-exception fallback: rebuild via `type(exc).__new__(type(exc), *exc.args)` + `__dict__` update and mark only that new instance; if even that fails, raise the stored instance UNMARKED (fails loud: worst case an ERROR line, never a real failure silenced) — the original is never marked — cost if wrong: an exotic exception type replays without the DEBUG downgrade.
Task 4: complete (commits cb6c83ed..49a5a3e8, review clean)
Task 5: dispatched (BASE 49a5a3e8, implementer sonnet)
Task 5: implementer DONE — commit 79d1569f; carried fixes in (pin test kills pause-first mutant; traceback-free copy stored at settle; original never marked, unrebuildable raised unmarked); retry-after gate test over all 7 CASES; concern for Task 6: Pirate keeps the last noted response across attempts (attempt-1 Retry-After survives an attempt-2 ConnectionError)
Task 5: minor (deferred): fail-loud branch (fetch_gate.py:340) re-raises one shared instance — its traceback grows per replay; NOT-TO-DO comment should say so
Task 5: minor (deferred): Retry-After with ≥309 digits returns None (OverflowError) instead of being capped at 24 h; `float(value)` → inf → cap would match C6 literally
Task 5: minor (deferred): "never mark the original" assumes `copy.copy` returns a new object; add `if again is exc` fall-through to `__new__` path
Task 5: minor (deferred): HTTP-date UTC-awareness not pinned (freeze_time tz_offset=0); `tz_offset=2` in the test would pin it
Task 5: complete (commits 49a5a3e8..79d1569f, review clean)
Task 6: dispatched (BASE 79d1569f, implementer sonnet)
Task 6: implementer DONE_WITH_CONCERNS — commit 48945139; no other test file drives Pirate into a non-200 retry; 4 Pirate test files 101 passed, no real sleep
- Ruling: Task 6's autouse fixture patches the Pirate module's own `time` name (`patch(M + "PirateWeatherClient.time")`) instead of the plan's `M + "PirateWeatherClient.time.sleep"` — the plan's target resolves to the global `time` module and would have turned the real 0.01 s/0.2 s waits of the concurrency tests into no-ops, silently weakening them (plan defect) — cost if wrong: if the Pirate module ever uses `time` for something else, the fake swallows it in that test file.
Task 6: minor (deferred): `_PIRATE_CASES` filter by id prefix could shrink silently — pin `len == 2`
Task 6: minor (deferred): network-error test discards `_outcome` — does not pin that the exception still reaches the caller
Task 6: minor (deferred): fixture replaces Pirate's whole `time` name — docstring should warn a future `time.monotonic()` there would be mocked
Task 6: minor (deferred): `status_code == 200 or == 429` → `in (200, 429)` (style)
Task 6: complete (commits 79d1569f..48945139, review clean)
Task 7: steps 1 (sister paths: every _SESSION.get is behind a gate or in validate_key — MetOffice :127 _request/:205 validate_key, OWM :87 validate_key/:104/:254 bodies, OpenMeteo :100 body, Pirate :144 validate_key/:248 _get_with_retries) and 4 (black: 71 unchanged; ruff: all checks passed) done by controller; step 2 full suite running
Task 7: step 2 done — branch 48945139: 7 failed, 4098 passed, 9 skipped, 496 errors (377 s); FAILED/ERROR names identical to baseline; +85 passed = 85 new tests collected; files baseline/suite-branch.txt, names-branch.txt
Task 7: step 3 (mutations) dispatched (implementer sonnet, no commit)
Task 7: step 3 done — mutations 12/12 killed (M1–M10 from plan + M11 pause-before-freshness + M12 note_response after early exit); report task-7-mutations-report.md; git status clean, HEAD 48945139 (verified by controller)
Final review: dispatched (opus) on c46c41fc..48945139, package review-c46c41fc..48945139.diff
Final review: With fixes — 0 Critical, 0 Important, 9 Minor; deferred-minor triage: 2 "must fix before the PR" (Met Office first-failure ERROR pin; traceback comment), rest "can stay"; all rulings "agree"
- Ruling: the fix wave takes Minors 1–9 of the final review (incl. optional 5–9: cheap, and they make the code leaner/neutral for the maintainer) plus two cheap pins (`_PIRATE_CASES` length, HTTP-date under tz_offset=2) — cost if wrong: a slightly larger last commit.
- Ruling: `_copy_of` is simplified to copy.copy-or-raise-unmarked (drops the `__new__` rebuild layer from my earlier ruling) — the layer served exception types none of the seven paths can raise; fail-loud stays — cost if wrong: an exotic uncopyable exception replays with an ERROR log line instead of DEBUG.
- Ruling: commit bodies that describe superseded states are reworded locally via `--fixup=reword:` + non-interactive `rebase --autosquash` (branch unpushed; backup branch first; verify empty content diff) — JustChr reads PR commits carefully; stale claims would mislead — cost if wrong: SHAs in this ledger before the reword no longer exist (the backup branch keeps them).
Final fix wave: dispatched (sonnet), findings file final-fix-findings.md
Final fix wave: DONE — new head 2ba2f05a (7 commits, reworded: 436d66af 6a1ea83a bfe1a9ea efcdf823 2caf6f1e are the rewritten 7b5454b6 cb6c83ed 49a5a3e8 79d1569f 48945139); backup/fetch-gate-pre-reword = bf5579fd; controller-verified: content diff backup..HEAD 0 bytes, no refs in bodies, 7 trailers; deviation A9: tz_offset=2 cannot catch naive now() under freezegun 1.5.1 → separate twin with patched clock
Final fix wave re-review: all A1–A9 and part-B bodies ADDRESSED, no new Critical/Important
Final: parked — "a copy without traceback" shorthand left at fetch_gate.py:101, :154 and tests/test_weather_fetch_gate.py:250 — Ruling: stays; true of the copy itself, the full limit is stated at :246-267 in the same file — cost if wrong: a reader of `_copy_of`'s docstring alone misses the chained-traceback limit.
Final: parked — PirateWeatherClient.py:236-238 two "since" clauses in one sentence — Ruling: stays; wording only, meaning correct — cost if wrong: a clumsy sentence upstream.
Final: parked — commit bodies 6a1ea83a/efcdf823 contradict each other on the uncopyable fallback (6a1ea83a describes the final tree, not its own) — Ruling: stays; branch is squashed at merge and the PR text will describe the final state; optional to drop the clause from 6a1ea83a before the push — cost if wrong: a careful reader of the PR's commit list sees a narrative inconsistency.
Task 7: complete — final head 2ba2f05a: full suite 7 failed, 4101 passed, 9 skipped, 496 errors (376 s), FAILED/ERROR names identical to baseline, +88 passed = 88 new tests collected; black 71 unchanged; ruff all checks passed; tree clean (controller-verified)
SDD loop complete (Tasks 1–7). Tasks 8 (live test HA-Test) and 9 (delivery) open, approval-gated.

## Follow-up after the HA-Test live test (2026-10-23, same session)
Live finding: pause counted from the END of a failed run → at the cap (599 s, cycle 600 s) a Pirate gate (≈3 s of retries) got the next cycle 2 s inside the pause and asked only every second cycle. User: "Bau das noch ein."
- 733861d9: backoff counts from the start of the failed run; Retry-After from the answer (`_asked_until`). TDD: RED `test_the_backoff_counts_from_the_start_of_the_failed_run` (1 == 2); pin `test_retry_after_counts_from_the_answer`; mutants A (end anchor) and B (Retry-After from start) each killed by exactly one of them.
- Review (opus): Important — waiters behind a failed run that outlasts its backoff each went to the network (probe: 60.5 s run, cache 0 → 6 requests instead of 1).
- Ruling: reviewer's option (a) — a caller notes its arrival before the lock; one that arrived before the latest failure ended (`_settled_at`) is handed its outcome regardless of the pause — exact, no guessed margin (option b rejected) — cost if wrong: a caller delayed between arrival and lock could replay a failure it did not strictly wait for (reviewer: only the latest failure, which it did wait through).
- be377f86: waiter rule; TDD RED `test_waiters_behind_a_slow_failure_share_it` (2 == 1); mutants "no waiter rule" and "arrival read inside the lock" killed by it. Scoped re-review: all addressed, Ready yes.
- Ruling: Minor 3 (binds_only no longer kills a mutant that keeps `_asked_until`) not changed — with an absolute deadline a later failure can only be recorded once the pause is over (or under override_cache, unset by the integration), so the mutant is equivalent on every reachable path; reviewer agreed — cost if wrong: none observable.
- 06173427 → amended to 9455f2f5: waiter replay logs "waited through the latest of N failed fetch(es)" instead of "no request for another 0 s"; waiter test uses a clock handshake instead of sleep(0.1) (value read before the signal). RED first on the wording; re-review: addressed, Ready yes.
- Full suite: 733861d9 7/4103/9/496, be377f86 7/4104/9/496, names identical to baseline; 06173427 running.
- Full suite 06173427: 7/4104/9/496, names identical to baseline, 91 new tests; 9455f2f5 = 06173427 + 4/2 lines in the waiter test (5× green)
