# Forecast weighting measures its window from the run, not from the calculation

`Eifel-Joe#21` · upstream report `JustChr#159` · base `upstream/master` = `10bb8077`

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
