# Forecast weighting measures its window from the run, not from the calculation

`Eifel-Joe#21` · upstream report `JustChr#159` · base `upstream/master` = **`fa863aa9`** (was `10bb8077`, then `c5330c7f`; see §9.6 and §9.11)

**Former designations:** `S` (work order of 2026-09-21).

---

## 1. Problem

The experimental forecast weighting waters less when rain is coming. It decides how much
less by summing precipitation out of the weather client's forecast list:

```python
forecast_precip = sum(
    day_data.get(const.MAPPING_PRECIPITATION, 0.0)
    for day_data in fd[:days]
)
```

`fd[:days]` is a positional slice. It carries no date and no knowledge of when the run
will happen, so the window is anchored at the calculation rather than at the run. The list
starts **tomorrow** by contract, so the weighting always prices calendar days from tomorrow
on, whatever day and hour the run actually falls on.

The precipitation skip guard — the other half of the same *Precipitation forecast days*
setting — had exactly this defect and it was fixed in `JustChr#146`. `forecast_window.py`'s
own docstring describes it. The two halves of one dropdown have diverged.

### 1.1 What was measured, not read

All three assertions hold on `10bb8077`, i.e. they describe today's behaviour. They live in
`tests/test_zz_repro_issue21.py` (throwaway) and reuse the fixtures in
`tests/test_experimental_features.py`.

Scenario: zone with a 10 mm deficit, precipitation rate 60 mm/h, look-ahead 1 day,
weighting on. Forecast: dry tomorrow, **8 mm the day after**, dry thereafter, seven dated
days. The run this zone will make is the day after tomorrow at 06:00.

| Measurement | Result on `10bb8077` |
| --- | --- |
| The weighting's own output | `duration 600 s`, `irrigation_target_bucket 0.0` — **the full 10 mm is watered**, because position 0 of the list is the dry day |
| `forecast_window.expected_rain` on the same forecast, anchored at the run | **6.0 mm**, `first_24h_covered True`, `complete True` |
| The gap | master delivers **10.00 mm** where the run's own window would deliver **4.00 mm** — **6 mm over-watered**, the night before 8 mm of rain |

The direction is the harmful one: the feature exists to water less before rain, and it
waters the full amount precisely when the rain is inside the run's window but outside the
list's first entries.

### 1.2 Established at the code, on this base

| Fact | Where |
| --- | --- |
| `forecast_weighting_enabled` is read in exactly **one** place in the package | `calculation.py:1108` |
| The window is a positional slice | `calculation.py:1123-1126` |
| Guard and weighting share the same setting | both read `CONF_PRECIPITATION_FORECAST_DAYS` |
| `calculation.py` knows no run start | no occurrence of `run_start` in the file |
| The reusable entry point exists and fits | `forecast_window.expected_rain(run_start, evaluated_at, days, hourly, daily)` |
| It reports coverage so a caller can abstain | `ExpectedRain.first_24h_covered` |
| The coordinator reaches the scheduler | `self.recurring_schedule_manager`, set at `__init__.py:739` |
| Occurrence resolution is bucket-free | `_next_governing_time` --> `_resolve_bound`: clock, sun and recurrence only |
| **An end-anchored schedule's start is NOT bucket-free** | `_project_schedule` derives it as `target - _estimate_duration(schedule)`, and `_estimate_duration` --> `coordinator.get_total_irrigation_duration` reads each zone's duration, which comes from the bucket |

That last row is the whole difficulty: the obvious route — ask
`async_get_next_run_projection` — is a cycle. The projection sizes each zone "from each
zone's bucket AT THE DECISION POINT" and filters through the runner's guards, so it
consumes what the calculation is in the middle of producing.

---

## 2. Requirements

1. The weighting's window starts at the run, spans the configured look-ahead, and is
   measured by `forecast_window.expected_rain` — not by a second windowing rule.
2. No dependency cycle: nothing on the path from the calculation to a run start may read a
   bucket or a zone duration.
3. A zone whose next run cannot be resolved is **not weighted**, and says so.
4. The precipitation skip guard's behaviour does not change.
5. The live path stays out (see §5).

---

## 3. Options considered

### 3.1 Where the run start comes from

| Option | Verdict |
| --- | --- |
| **A narrow, bucket-free resolver on the schedule manager** | **Chosen** (user, 2026-09-26). Touches recurrence resolution only. |
| Ask `async_get_next_run_projection` | Rejected: cycle, established at the code (§1.2). |
| Move the weighting to the decision point, where the start is known exactly | Rejected for this change: that *is* the live-path question JustChr wants decided separately, and it would make this pull request the thing he asked not to have merged along. |

### 3.2 What to use when the start is not bucket-free

An end-anchored schedule has no bucket-free start. The projection already prefers an
**armed** run's `start_utc` when one exists, and that value is free to read — it was written
earlier, by someone else.

| Option | Verdict |
| --- | --- |
| **Armed `start_utc`, else the schedule's governing target** | **Chosen** (user, 2026-09-26). For an end-anchored schedule the window is then anchored at the run's *end* instead of its start: an error of at most one run length against a 24-hour block, bounded and stated. |
| Weight only where the start is exact | Rejected: the feature would fall silent for a whole anchor mode with nothing saying so. |
| Always the governing target, no special case | Rejected: gives up exactness where it is free to have. |

### 3.3 Zone in several schedules

Not a trade-off. The **earliest** resolvable next run wins: that is the run whose window
the weighting is about to price.

---

## 4. Design

### 4.1 The new seam

`RecurringScheduleManager.async_next_run_start_for_zone(zone_id)` --> aware UTC datetime or
`None`.

- Considers enabled schedules whose `SCHEDULE_CONF_ZONES` is `"all"` or names the zone.
- Per schedule, in order: the armed run's `start_utc` if one is armed for it; otherwise
  `_next_governing_time(schedule, governing)` passed through
  `_advance_past_fired_occurrence`, so an occurrence that has already fired is not offered
  as the next one.
- Returns the earliest; `None` when none resolves — no enabled schedule names the zone, or
  the schedule is an un-anchored interval one, which has no clock target at all.
- **Bucket-free by construction:** never calls `_estimate_duration`, `_duration_bound`,
  `get_total_irrigation_duration` or `_decision_point`. This is the load-bearing property
  and it gets its own test (§6).

### 4.2 The weighting

In `calculate_module`, replacing the positional slice and nothing else around it:

1. `start = await self.recurring_schedule_manager.async_next_run_start_for_zone(zone.get(const.ZONE_ID))`
   — `calculate_module` receives the zone dict, not an id.
   `None` --> do not weight, `debug` line naming the zone and the reason.
2. `days` from `CONF_PRECIPITATION_FORECAST_DAYS`, unchanged, still shared with the guard.
3. `covering_until = start + 24 * days hours`; `hourly` from
   `client.get_hourly_precipitation_forecast(covering_until=...)` where the client offers it
   — the same plumbing the guard uses, so a client that holds two products of different
   reach can pick the right one.
4. `rain = expected_rain(run_start=start, evaluated_at=dt_util.utcnow(), days=days,
   hourly=hourly, daily=fd)`.

   **`dt_util.utcnow()`, deliberately not the method's own `now`.** `calculate_module`
   already takes an injectable `now` and defaults it to a bare `datetime.now()`
   (`calculation.py:883`) — naive, process-local, and the exact seam `Eifel-Joe#22` is
   about to move. `expected_rain` compares against aware instants, so the weighting needs
   an aware one either way; taking it from `dt_util` rather than from that parameter keeps
   this change independent of how `Eifel-Joe#22` resolves, and means neither pull request
   has to land before the other.
5. `not rain.first_24h_covered` --> do not weight, `debug` line. This mirrors the guard,
   which refuses to decide on a first 24 hours nothing forecast. Abstaining means watering
   the full amount, which is the safe direction for a feature whose job is to water less.
6. Otherwise `effective_bucket = min(0.0, newbucket + rain.mm)` — the same arithmetic as
   today, a different number.

The bucket/duration separation is untouched: `newbucket` stays the persisted deficit,
`effective_bucket` drives the duration, `irrigation_target_bucket` carries the leftover.

### 4.3 The existing tests need dated fixtures

The four weighting tests in `tests/test_experimental_features.py` pass **undated** entries
(`{const.MAPPING_PRECIPITATION: 4.0}`). `forecast_window.day_span` returns `None` unless both
`FORECAST_DAY_START` and `FORECAST_DAY_END` are present and aware, so those entries would
contribute nothing and all four would stop weighting. Real clients have supplied both since
`JustChr#145`, so the fixtures are simplified rather than impossible: each grows a date, and
each test also grows a resolvable run start. This is a known cost of the change, not a
surprise to be discovered during implementation.

---

## 5. Explicitly not in scope

- **The live path.** `forecast_weighting_enabled` never reaches the live estimate, so a zone
  under `live_estimate_enabled` is sized without the weighting at all. JustChr: "the live
  deficit is a pure actuals balance by construction, and putting a *forecast* into it changes
  what that number means. I do not want the second riding along on the first's merge."
  Separate decision, separate pull request.
- **What the weighting does with the rain.** The `min(0.0, ...)` clamp, the decision to keep
  the true deficit in the bucket, and the leftover target all stay exactly as they are.
- **The skip guard.** Untouched, and its tests are the oracle that says so.
- **The end-anchored inexactness.** Anchoring at the run's end rather than its start for
  end-anchored schedules is accepted and stated, not fixed. Fixing it needs a bucket-free
  duration estimate, which is its own piece of work.
- **A zone in several schedules getting several windows.** One window, from the earliest run.

---

## 6. End-to-end criterion

1. The three measurements of §1.1 flip from asserting the defect to asserting the fix, and
   enter the suite as real tests: the zone whose run is the day after tomorrow weights on
   the 8 mm that falls inside its own window, and delivers 4 mm instead of 10.
2. **The cycle pin:** with `get_total_irrigation_duration` patched to raise,
   `async_next_run_start_for_zone` still answers. A resolver that reaches the bucket fails
   this test, which is the only mechanical guard against the cycle coming back.
3. `tests/test_precipitation_guard.py` and `tests/test_forecast_window.py` pass
   **unchanged** — the guard is the oracle for the module being reused.
4. A zone with no enabled schedule is not weighted, and the `debug` line says which zone and
   why.
5. Full suite with no new failures, compared against a baseline measured on **this** base
   commit rather than an older one (`10bb8077` carries 349 collection errors on our Windows
   environment where `965a4f9d` carried 320; the difference is `JustChr#167`, not us).
6. `uvx black --check` and `uvx ruff check` on `custom_components/irrigation_plus/`.

---

## 7. Traps

- **A short forecast fixture makes the window abstain, and it looks like the design
  failing.** The first repro used two dated days; the run's 24-hour block was then only
  18/24 covered, `first_24h_covered` came back `False`, and under requirement 3 the fix
  would have declined to weight the very case it exists for. Measured across list lengths:
  2 days abstains, **3 and above cover**, and every real client serves 7 or more. Any test
  of this path needs a realistic number of days or it tests the fixture.
- **`get_forecast_data` starts tomorrow, not today.** Stated in `forecast_window.py`'s
  docstring. A repro that assumes index 0 is today measures the wrong thing.
- **Do not reach for `async_get_next_run_projection`.** It is the obvious call and it is a
  cycle (§1.2). The resolver exists precisely to avoid it.
- **`self.recurring_schedule_manager`, not `self.scheduler`.** Searching for the latter
  suggests the coordinator cannot reach the schedule manager at all.
- **`calculate_module`'s `now` is naive process-local**, and `expected_rain` takes aware
  instants. Threading that parameter through would both break on the type and couple this
  change to `Eifel-Joe#22`'s outcome. The look-ahead's own `forecast_first_day` is derived
  from it as `now.date() + 1 day`, which is where the "list starts tomorrow" contract is
  visible in the calculation itself.
- Throwaway repro at `tests/test_zz_repro_issue21.py`. It asserts today's behaviour and must
  be deleted by the change that inverts it.

---

## 8. Decisions taken

| Decision | By whom, when |
| --- | --- |
| A narrow bucket-free resolver on the schedule manager, not the projection | User, 2026-09-26 |
| Armed `start_utc` first, the schedule's governing target second | User, 2026-09-26 |
| No resolvable run start means no weighting, with a `debug` line | User, 2026-09-26 |
| The earliest of several schedules wins | This analysis, §3.3 |
| The live-path half stays a separate product decision | JustChr, `JustChr#159`, 2026-09-21 |
| Reuse `forecast_window`, do not add a second windowing rule | JustChr, `JustChr#159`, 2026-09-21 |

---

## 9. What the maintainer's review changed (2026-09-27, `CHANGES_REQUESTED`)

Two findings, each handed over with a failing test, and one question. All three
are confirmed against the code and the clock rather than taken on trust — and one
of them is **one call site wider** than the review says.

### 9.1 The tests were dated, not pinned, and they failed the next day

`RUN_START` is `2026-09-27 00:00 UTC` and the new file uses `2026-09-28 06:00` /
`2026-09-29 06:00`, while the production path takes `evaluated_at=dt_util.utcnow()`
— which nothing pins. `expected_rain` treats a block already past at evaluation as
uncovered, so the verdict rides the real calendar.

Reproduced on the branch as submitted, with no clock patching at all, on
2026-09-27:

| test | expected | got |
| --- | --- | --- |
| `test_forecast_weighting_reduces_duration_and_sets_target` | `360` | **`490`** |
| `test_forecast_covering_deficit_skips_run` | `0` | **`269`** |
| `test_forecast_weighting_sums_lookahead_days` | `300` | **`365`** |

`3 failed, 35 passed`, and exactly the three names the review predicted. Every
actual is **above** its expectation, which is the tell: a partially covered window
sums part of the rain, a smaller reduction survives, and the zone waters *more*.
The same direction the whole change exists to remove.

The worse half is the one that does not show up as red. Past those dates
`test_rain_outside_the_runs_window_is_not_weighted` and both abstention tests keep
passing **for the wrong reason** — the window has moved into the past, so the
weighting abstains and the assertions hold without exercising anything. That is
the `JustChr#141` class: a green test pinned to the clock instead of to the
behaviour.

**Fix:** an autouse fixture pinning `calculation.dt_util.utcnow` to a moment
before the run, in both files. Targeted rather than `freezegun`: `expected_rain`
already takes `evaluated_at` as a parameter, so the single read in
`calculation.py` is the whole clock surface, and freezing the world tends to take
Home Assistant's own internals with it. Each pinned test is then re-checked by
moving the pin, so it still fails for its own reason.

### 9.2 Under "before each irrigation run" the resolver prices the next run

With `autocalcmode: before_run` the calculation that runs the weighting is
`async_commit_pre_run_calculation`, reached **from inside the run's own dispatch**.
The resolver then answers for the run *after* the one being dispatched. Two
independent mechanisms produce it:

- **(A) the fired-occurrence guard.** `finish_callback` (`scheduler.py:1656-1658`)
  writes `_finish_last_target[sid]` and pops `_armed_runs[sid]` *before* calling
  `_execute_schedule`. `_advance_past_fired_occurrence` then sees this run's own
  target as already fired and moves past it, and the popped arm can no longer
  supply `start_utc`.
- **(B) strictly-after-now.** `_next_governing_time`'s own contract is "the moment
  the next occurrence must fall strictly after; defaults to now". At dispatch
  *now* **is** the occurrence, so the bound resolves to the following one. This
  one needs no `_finish_last_target` at all.

Measured with the **real** `_next_governing_time` and the **real**
`_advance_past_fired_occurrence`, standing in only for the clock/sun layer
(`_resolve_bound`) with a plain daily 06:00 UTC bound. Probe, archived beside this document as
`docs/superpowers/probes/2026-09-27-before-run-anchor.py` (it ran from
`D:\Entwicklung\HASI\issue21-work\probe_before_run_anchor.py`, which is scratch and
will not survive a cleanup).

| situation | the run really starts | the resolver says | |
| --- | --- | --- | --- |
| calculation **ahead** of the run (a fixed-time autocalc at 03:00) | `2026-09-28 06:00` | `2026-09-28 06:00` | correct |
| dispatch, finish callback — mechanism (A) | `2026-09-28 06:00` | `2026-09-29 06:00` | **+1 day** |
| dispatch, plain start-time schedule — mechanism (B) | `2026-09-28 06:00` | `2026-09-29 06:00` | **+1 day** |

So a daily schedule prices tomorrow's window and a weekly one next week's: the
same day offset this change exists to remove, in a different setting.

**Why the existing tests cannot see it.** `test_next_run_start_for_zone.py`'s
`_fixed_target` replaces `_next_governing_time` *and*
`_advance_past_fired_occurrence` (lines 47-48, 162-163, 180-181). It was written
to test the resolver's own decisions rather than re-test recurrence maths, and it
bought that isolation by stubbing out both places the defect lives.

#### 9.2.1 It is two commit sites, not one

The review sorts `_decide_and_run_start_pinned` under "the two `pre_committed=True`
paths [that] commit at the decision point, before the fire, so they are fine". It
does not commit at a decision point. Its own docstring:

> The Start bound already fixed the fire time […] so there is no separate
> decision point to read the demand ahead of the run — this runs the same
> rank/select sequence `_decide_and_arm` applies at ITS decision point, **but at
> the moment the schedule actually fires**.

`run_callback` (`:1731`) sets `_finish_last_target[sid]` and then hands off to it,
and its commit sits at `:1820`. It does *not* pop `_armed_runs`, so mechanism (A)
is partly defused — but the arm it finds carries **today's** target while the
resolver has already advanced to tomorrow's, `abs(armed["target"] - target)` is
about 24 h, and the `SAME_OCCURRENCE` proximity test rejects it. Mechanism (B)
then stands alone and the site is wrong too.

The three commit sites, settled:

| site | when it commits | affected |
| --- | --- | --- |
| `_perform_scheduled_irrigation` `:2332` (`pre_committed=False`) | at dispatch — plain start-time, interval, one-shot, finish callback | **yes** |
| `_decide_and_run_start_pinned` `:1820` | at the fire, by its own docstring | **yes** |
| `_decide_and_arm(commit=True)` `:1962`, via the `decide_callback` registered only when `decision_point > now_utc` `:1889-1894` | genuinely ahead of the run | no, by design |

This is the sister-path check paying for itself: fixing only the site the review
named would have left the start-pinned anchor mode with the defect and a green
suite.

### 9.3 The anchor: the caller that knows the run start says so

The review offers two shapes. They are not equivalent.

| shape | verdict |
| --- | --- |
| **Pass the run start through the pre-run commit** | **Chosen.** The dispatch moment *is* the run start — exact, no resolution, no heuristic — and it covers (A) and (B) and all three schedule kinds at once, because they funnel through the same two commits. |
| Have the resolver return an occurrence fired within `SAME_OCCURRENCE` of now | Rejected: **it does not cover mechanism (B).** A plain start-time schedule never records a fired occurrence, so there is nothing within `SAME_OCCURRENCE` to return — row 3 of §9.2's table is reached with `_finish_last_target` empty. It would also change the answer for callers that are *not* in a dispatch: a fixed-time calculation running within the hour after a run would price the run that already happened. |

`run_start` becomes a keyword-only parameter with a `None` default, threaded from
the commit to the weighting:

```
async_commit_pre_run_calculation(zones, *, run_start=None)
  ├─ selection is None -> _async_calculate_all(run_start=run_start)
  └─ else              -> async_update_zone_config(zone_id, {ATTR_CALCULATE: True},
                                                   run_start=run_start)
                            -> async_calculate_zone(zone_id, ..., run_start=run_start)
                                 -> calculate_module(..., run_start=run_start)
```

and the weighting resolves in three steps, each separately observable:

1. a `run_start` given by the caller wins — this is a dispatch, the run is now;
2. otherwise the resolver answers — the calculation is ahead of a scheduled run;
3. otherwise `evaluated_at` (§9.4).

**A dict key was the wrong seam and was rejected.** The zone branch reaches the
calculation through `async_update_zone_config(zone_id, {ATTR_CALCULATE: True})`,
and `ATTR_CALCULATE` is schema-validated as a websocket field
(`websockets.py:295`). A run start carried in that dict would become part of an
external API. A keyword-only parameter *beside* the dict is invisible to all eight
existing callers — `websockets.py:384` passes `(zone, data)` positionally — and
adds no surface at all.

**NOT-TO-DO:** do not carry the run start on the coordinator as transient state
for the duration of the commit. It reads as the smaller change and is not: the
commit awaits throughout, so a fixed-time calculation interleaving at any `await`
would read another run's anchor.

### 9.4 A zone no schedule names falls back to the calculation

This **reverses requirement 3 of §2 and the third row of §8**, which said an
unresolvable run start means no weighting with a `debug` line. Recorded as a
reversal rather than edited into §2, because the reason it changed is the
interesting part.

The review's objection: someone who irrigates from their own automations turns on
an experimental feature and it silently does nothing.

What settles it is not the objection but the sister half. The precipitation skip
guard — the *other* half of this same `Precipitation forecast days` setting, and
the module this change reuses — already does exactly what is being asked for:

```python
# skip_conditions.py:235
start = dt_util.as_utc(run_start) if run_start is not None else now
```

with its docstring: *"without `run_start` it starts now, which is dispatch —
every preview names a start"*. The whole thesis of this change is that the two
halves of one dropdown had diverged. Abstaining where the guard anchors would
leave them diverged in a second place, by our own hand.

**The cost, stated:** someone who calculates at 03:00 and waters from an
automation at 20:00 gets a window anchored 17 h early. Bounded by one day against
a 24-hour block, and the same trade the guard already makes. Rain inside the
anchored window that falls before the run has landed on the soil before the run
anyway, so counting it is not simply wrong; rain past the anchored window is
missed, which waters *more* — the safe direction, and what abstaining did in every
case.

Decided by the user, 2026-09-27, on that evidence.

### 9.5 The references come out, and his go in

Three added lines in the diff name our own tracker: a `calculation.py` comment
citing `Eifel-Joe#22` and the module docstrings of both new test files citing
`Eifel-Joe#21`. Nobody reading the upstream repository can resolve those.

Unlike `JustChr#174`, substituting numbers is right here rather than evasive:
`JustChr#159` and `JustChr#160` already exist in his repository as bug reports we
filed, and their titles are the same defects — so the replacement cites *his*
issues, which is what he asked for. No issue is opened anywhere in order to be
citable. `JustChr#159` is already named in the pull request body.

**And the rewrite has to reach the commits, not sit on top of them.** Checked per
commit: the eight commit messages are clean, but `21aa6f4e` and `677b9bfc`
introduce the three lines as **added** content, so a correcting commit on top
leaves `git show <sha> | grep -E 'Eifel-Joe'` matching on those two. That is what
cost `JustChr#174` a branch reshape. The branch is rebased onto `c5330c7f` and
needs real changes anyway, so the history is rebuilt with the references never
present. Only the author line may match.

### 9.6 The baseline moved with the base

`10bb8077` is 8 commits behind; the review asks for a rebase onto current master.
On `c5330c7f` the suite measures **7 failed / 3322 passed / 9 skipped / 367
errors — 374 non-green names**, already captured at
`D:\Entwicklung\HASI\pr174-work\baseline-names.txt`. §6's figures (349 errors,
356 names) are void. Only a full run with a name diff decides; a subset does not.

### 9.7 What this adds to the end-to-end criterion

Beyond §6, unchanged:

7. **The dispatch anchor, through the real advance.** A test that drives
   `_advance_past_fired_occurrence` and `_next_governing_time` for real — stubbing
   only the clock/sun layer — and pins that a commit made from inside a dispatch
   prices the window from *now*, in both mechanism (A) and mechanism (B) shapes.
   The §9.2 probe becomes that test.
8. **The start-pinned site.** The same pin for `_decide_and_run_start_pinned`, the
   site the review did not name.
9. **The clock pins hold when the clock moves.** Each pinned test still fails for
   its own reason with the pin shifted, so §9.1's silent-green class cannot return.
10. **A zone no schedule names is weighted from `evaluated_at`**, and a zone whose
    resolver answers is weighted from that answer — three distinct paths, three
    tests.
11. Three reference checks before the push — diff, commit messages, **and the
    content of every individual commit** — all empty but the author line.

### 9.11 The base moved twice, and the second time mid-verification

`JustChr#174` was merged while this phase was being verified (2026-09-27 14:17 UTC,
squashed to `d1f3c292`), and a release commit followed, so `upstream/master` went
`c5330c7f` --> **`fa863aa9`**. §9.6's figures for `c5330c7f` are therefore void in
turn, and `pr174-work/baseline-names.txt` with them. Re-measured on `fa863aa9` in
its own worktree (`issue21-work/base`).

Two things checked before the rebase rather than after:

- **The merge is byte-identical to what was submitted.** `git diff 3e372042
  d1f3c292` is empty across every file. The maintainer changed nothing on the way
  in -- worth confirming rather than assuming, because he has amended a merge
  before (a `_dist_uses_master` gate on `JustChr#70`). So the witness form on
  master is exactly
  `_saw_report_after_open and _priced and not _declined`.
- **The two changes are disjoint.** `JustChr#174` touched `flow_metering.py`,
  `irrigation.py`, `self_closing.py`, `distributor.py`, `docs/usage-events.md` and
  three test files; this one touches `calculation.py`, `scheduler.py`,
  `auto_calc.py`, `__init__.py` and five different test files. `comm -12` over the
  two name lists is empty, which is why the rebase carried all three commits with
  no conflict.

### 9.12 The measured result on `fa863aa9`

| | failed | passed | skipped | errors | non-green names |
| --- | --- | --- | --- | --- | --- |
| `fa863aa9` clean (`issue21-work/base`) | 7 | 3344 | 9 | 367 | **374** |
| this branch (`341fa1e7`) | 7 | **3366** | 9 | 367 | **374** |

**Name `diff` between the two runs: empty.** `+22` passed is exactly the 22 tests
this change adds -- 12 in `test_next_run_start_for_zone.py`, 6 in
`test_forecast_weighting_window.py`, 3 in `test_before_run_anchor.py`, 1 in
`test_auto_calc_mode.py`, counted by definition rather than inferred from the
delta. Files: `issue21-work/{baseline-fa863aa9,branch-names-fa863aa9}.txt`.

One thing the two baselines settle in passing: `c5330c7f` and `fa863aa9` carry the
**same 374 non-green names** (`diff` empty). The merged sister fix added 22 passing
tests and no new failure, so nothing here is inherited breakage.

`black --check` 69 files unchanged, `ruff check` clean. Three reference checks
re-run after the rebase: diff and commit messages empty, and one match per commit,
each the `Author:` line.

**What it means for `Eifel-Joe#53`,** which was deferred for exactly this event: the
condition it waited on is met. It can now rebase onto master, **drop its
`flow_metering.py` change entirely** (+41 lines, superseded by the three-condition
form), and its two `distributor.py` `at=` conversions are already there. The
textual conflict its own §4.3 accepted as the lesser evil no longer exists.
