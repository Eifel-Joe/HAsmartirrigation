# Weather buffer: the write side moves into HA's zone

**Revision 3** of `docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md`
(on `archive/design-history`). That document stays authoritative for everything this
one does not restate — in particular its reader inventory (section "Leser (B)") and
its refutation of data-based detection (`D4`).

**Date:** 2026-09-28 · **Issue:** `Eifel-Joe#22` · **Upstream:** `JustChr#160`
**Base:** `upstream/master` = `1876aa03` (v2026.09.27), re-fetched and verified
**Branch:** `fix/weather-buffer-aware-writers` (worktree `issue22-work/wt`)
**Line numbers** in this revision refer to `1876aa03`; the 2026-09-21 spec's refer
to `965a4f9d` and have all moved.

This is the **second half** of `JustChr#160`. The first half shipped as `JustChr#177`
("Ready for the second half whenever you are").

## What has landed since Revision 2

| Rev-2 decision | Status on `1876aa03` |
|---|---|
| `D1` — one shared coerce helper | **shipped** as `coerce_stamp(value, provenance)` in `helpers.py`, but in the **naive** direction, not the aware one `D1` specified |
| `D5` — pin via an injectable process-zone function | **shipped** as `_process_timezone()` + the `split_zones` fixture in `tests/test_time_provenance.py` |
| `D2` — writers to `dt_util.now()` | **open — this document** |
| `D3` — migration, `STORAGE_VERSION` 14 → 15 | **revised below** |
| `D4` — no detection, assumption in a comment | **adopted unchanged** |

`#177` deliberately diverged from `D1`: it normalises **to naive** so that no number
moved, and says so in its own docstring —

> this normalises to NAIVE, not to aware … an aware input is what the **write-side
> change will start producing**.

That divergence reopened the question `D1` had answered, which is what Revision 3
settles.

## Problem (unchanged, restated for self-containment)

The buffer is stamped with a bare `datetime.now()` — the **process's** zone — and read
back against HA's **configured** zone. Both sides are naive, so nothing raises: the
subtraction silently measures across two clocks whenever the zones disagree. Routine on
HA Container without `-e TZ=` and on Core in a venv on a UTC host; HA OS and Supervised
are unaffected because the Supervisor pushes the configured zone in.

The error is **constant through the day**, not a midnight edge case. Confirmed sizes:
~0.8–1.0 mm too negative on the daily deficit at a summer ETo near 4 mm/day — enough to
flip the skip branch — and **+23.5 % / −16 % on the clearness-ratio radiation**, because
Rso sits in a denominator there. The radiation error is the larger one and leads the
release notes.

## Decision R3-1: one internal frame — naive HA-local

`coerce_stamp` keeps normalising to naive, and both provenances come to mean the **same**
frame: naive **HA-local**.

| | naive input | aware input |
|---|---|---|
| `STAMP_FROM_STORE` | *(new)* read in the process zone, lift to HA-local | *(new)* `as_local`, then strip |
| `STAMP_FROM_CLIENT` | unchanged — already HA-local | unchanged — `as_local`, then strip |

Writers move to `dt_util.now()`, so the store holds **aware** values from the upgrade
onward and every new stamp is self-describing. Legacy naive values are read as
process-local — which is what they were when written — and lifted into the one frame.

Both ends move. `now` already *is* naive HA-local
(`coerce_stamp(dt_util.now(), STAMP_FROM_CLIENT)`), so the comparison basis does not move.

### Why not aware internals, which is what `D1` chose

Two reasons that did not exist when Revision 2 was written:

1. **`#177` made the blanket `except` argument concrete.** From the module docstring of
   `tests/test_time_provenance.py`: "Turning a stamp aware would raise `can't compare
   offset-naive and offset-aware` inside a blanket `except`, i.e. silently disable the
   live estimate, which is the opposite of a fix." Under aware internals every
   downstream consumer must move in the same commit or the feature goes quietly
   unavailable with a plausible "last calculated" still on display.
2. **The per-row solar offset becomes correct without being touched.**
   `weather_aggregate.py:1018` already computes `row_offset = tz.utcoffset(hour_start)`
   — "which offset does **HA** have at this wall-clock time". Today that is wrong
   because `hour_start` is process-local while `tz` is HA's. Once the frame is HA-local,
   that line is right as it stands. Under aware internals it has to be rewritten to
   `hour_start.utcoffset()` instead.

`D1`'s reasoning was sound for its time; it simply predates both facts.

## Decision R3-2: no `STORAGE_VERSION` bump — this revises `D3`

`D3` chose a migration to aware with `STORAGE_VERSION` 14 → 15, on a **hard rule** that
still holds and must be honoured either way:

> Watermark and buffer move together or not at all. A wrong assumption is then a
> *uniform translation of the whole stored timeline*; in `select_window` (`rt >
> watermark`) it cancels out completely. Migrating only one of the two is the **only**
> way to create double counting.

Read-time coercion satisfies that rule, because the watermark and the row stamps go
through the **same** call: `weather_aggregate.py:167` coerces the watermark and `:122`
coerces the row stamps, both under `STAMP_FROM_STORE`. The translation is uniform by
construction, so the cancellation `D3` relies on is preserved without a schema step.

**What is new since `D3`, and why it tips the decision: downgrade safety.** A bump
rewrites stored stamps to aware. A user who then rolls back — routine with HACS — runs
code that has no `coerce_stamp` at all and compares those aware values against naive
ones, inside the blanket `except`. The result is the live estimate silently switching
off with a plausible "last calculated" still displayed: precisely the failure this whole
line of work exists to remove, introduced by the fix for it. Revision 2 could not weigh
this, because `coerce_stamp` did not exist yet and the blanket-`except` analysis came
later.

Against that, the bump buys a uniformly aware store and lets the legacy branch be
dropped one day. The legacy branch is three lines inside a function that has to exist
anyway, and the data it serves ages out within `BUFFER_RETENTION` = **7 days**
(`calculation.py:44`).

So: **coerce at read time, no bump.** The allowlist `D3` specified is still the correct
description of *which* stamps are in play, and is carried over unchanged below.

## Decision R3-3: no detection — `D4` adopted unchanged

JustChr asked for our judgement on the one assumption in the migration, and said "if you
see a way to detect it cheaply, better still". `D4` already answered this, and its
answer stands. Restated because it is the part he asked for:

**A data-based detector is not expensive, it is impossible in principle.**

1. **DST collision — decisive.** At the autumn transition the naive sequence in the
   buffer runs an hour **backwards**: exactly the signature a detector must look for.
   The bytes of a DST fall-back and of a container `TZ` fix are identical. A window can
   reach seven days and straddle a transition, so a detector would fire for every DST
   user twice a year, **with the same error magnitude it is meant to prevent**
   (1 h = 4.2 % of a day).
2. **A future-dated clamp is direction-blind.** JustChr's own scenario — UTC → a real
   zone, offset rising — pushes stamps into the **past**. Hit rate exactly 0 %. It is
   additionally false-positive on boards without a buffered RTC, where the read happens
   seconds after boot, before NTP convergence, and the whole buffer reads as "future".
3. **Pairing naive against aware fails quantitatively.** The unknown real gap between a
   naive poll stamp and an aware run stamp enters the estimate 1:1 and is roughly
   uniform over an hour, while the quantity sought is quantised to hours — noise equals
   signal. Worse, on a freshly set-up install, which is exactly the one that just
   corrected its `TZ`, there are **zero** aware stamps to pair against.

**The residual damage is small and heals with certainty.** A watermark error Δ produces
exactly Δ/24 relative error on **one** window; Δ = 2 h is 8.3 % of a day's ETo, about
0.25 mm of bucket at 3 mm/day. After that the error is structurally impossible, because
every new stamp carries its own offset.

So the assumption goes into the code as a comment, naming **the rejected alternative as
well** — otherwise a later reader "repairs" it to `DEFAULT_TIME_ZONE` to match
`sensor.py`, which is the original bug.

**No clamp.** `_window_bounds` already absorbs stamps after `now` non-destructively
(`end = max([now, *stamps])`, its docstring: "so a clock skew cannot yield a
negative-length window"). That is the established idiom here; a second, destructive
mechanism beside it would be worse than none.

## Scope

**In** — 16 persisting writers:

| File | Sites |
|---|---|
| `__init__.py` (behind the `dt_datetime` alias) | 7 — 1429, 1506, 1516, 1632, 1644, 1799, 2023 |
| `calculation.py` | 5 — 267, 379, 432, 498, 934 |
| `continuous_update.py` | 3 — 252, 378, 521 |
| `store.py` | 1 — 1653 (`last_consumed_at` on zone creation) |

**plus** three `now` defaults in `weather_aggregate.py` (370, 938, 1133), all of the
identical shape `coerce_stamp(now, …) if now is not None else datetime.datetime.now()`.
Not persisted, but compared against stored stamps — they must default in the frame the
readers use, and all three move together (sister paths).

**plus** `coerce_stamp`'s `STAMP_FROM_STORE` branch in `helpers.py`.

`__init__.py` is the sister path the upstream issue does not name: same defect, different
caller. 1506 is the on-demand single-zone update, 1632 the interval poll — same commit.

The stamps in play, from `D3`'s allowlist: `zones[i].last_calculated`,
`.last_consumed_at`, `.last_updated`, `mappings[i].data[j].retrieved`,
`mappings[i].data_last_updated`. Untouched because already aware: `last_irrigation`,
`run_log[].ts`, `pending_bucket_events[].ts`.

**Explicitly NOT in scope** — `NOT-TO-DO`, not silently skipped:

- **`weathermodules/*.py`, 11 sites.** `_cached_*_at` compared as `datetime.now() <
  fetched_at + timedelta(ttl)`: same process clock, inside one process, never stored,
  never compared against HA time. No defect, and moving one side of a TTL comparison
  would *introduce* one.
- **`generated_at`, 4 sites** (`services.py:273`, `:289`, `watering_calendar.py:79`,
  `:93`). Display values that never reach the store and are never subtracted.
- **Aware internals** (R3-1), **any reconstruction of the old zone, any future clamp,
  any heuristic** (R3-3).

## End-to-end criterion

Two assertions, and the second is not optional. `calculation.py:796` warns why:

> NOT-TO-DO: do not expect a switch to aware timestamps to fix this by itself. The
> offset does not travel as `tzinfo` — it travels as this float, through
> `SiteGeometry.tz_offset_h` and on into `row["tz_offset_h"]`. A stamp that becomes
> aware leaves this arithmetic untouched **and the suite green**, which is exactly how
> the expensive half of this could be missed.

With the process zone at UTC and HA at Europe/Berlin (`split_zones`), on a store whose
stamps were written under the process zone:

1. **The window length equals the real elapsed time.** Today 1 h is computed as 3 h.
2. **The solar-time correction uses the rows' true offset, not HA's offset applied to a
   foreign wall clock** — i.e. `row["tz_offset_h"]`, the value that carries the
   ±23.5 % / −16 % radiation error. This is the expensive half and it must be pinned
   separately, because assertion 1 can go green while it stays broken.

Both must be seen **RED on `1876aa03` before the fix**, failing as an offset rather than
against an arbitrary constant. Supporting pins:

- a naive legacy `STAMP_FROM_STORE` value is lifted from the process zone into HA-local,
  while a naive `STAMP_FROM_CLIENT` value is still returned untouched;
- an aware stored value — what the writers now produce — reads back as the same instant
  under either zone;
- `tests/test_time_provenance.py::test_a_naive_value_is_returned_unchanged_under_either_provenance`
  **must be split.** "Unchanged under either provenance" becomes false for the store
  provenance by design. That is the deliberate behaviour change, and its pin belongs in
  the same commit (memory `regression-pin-on-removals`).

Verification must call the changed function, not a neighbour of it (memory
`verification-must-exercise-the-change`).

## Traps (measured on this base, not anticipated)

- **Baseline on `1876aa03`:** 7 failed / 3455 passed / 9 skipped / **367 errors**. All
  367 errors are `Failed: Lingering timer after test`, a teardown artifact of the local
  Windows env, not a defect. Only the **delta** is meaningful. The WIP branch's old
  200/105 figures were measured on a different foundation and are **not** a baseline
  here (memory `rebaseline-when-the-base-moves`).
- The filter needs the directory: `^(FAILED|ERROR) tests/`, or a log line counts. Read
  the result file only after the run ends.
- **Do not rebase** `fix/weather-buffer-aware-time`. It is pushed to `origin` (project
  rule forbids rebasing pushed branches), its commit 1 *is* essentially `#177`, and a
  probe rebase collides in `helpers.py` where two drafts of the same idea meet. Idea
  source, not code base.
- From a worktree there is no local `.venv` — address the interpreter absolutely, and
  `_local_socket_unblock.py` must be copied in.
- **`docs/superpowers/` is not gitignored.** It must never be staged on the branch that
  becomes the upstream PR: this file names `Eifel-Joe#22`, and no text reaching JustChr
  may reference our tracker (memory `no-own-issue-refs-upstream`, absolute). Design docs
  go to `archive/design-history` (Regel P1). Adding it to `.git/info/exclude` is *not*
  the fix — that would make the archive's own `git add` fail silently, the trap the
  project already hit with `dist/`.

## Not part of this work

- **The runtime check**, carried over from Revision 2 as still the better idea: compare
  `datetime.now().astimezone().utcoffset()` against `dt_util.now().utcoffset()` and warn.
  It answers the *better* question — not "did the TZ change" but "does the process zone
  differ from HA's **now**" — and so catches the whole "container without `-e TZ=`"
  class permanently. Own PR, so JustChr can decline it without blocking the fix.
- **The `exc_info=True` one-liner** on `_intraday_for_zone`'s blanket `except`, plus
  logging the first failure per refresh at WARNING. JustChr said yes to it "independent
  of both PRs". Own PR.
- **The `TZ=` documentation mitigation** — already shipped as `JustChr#164`.
