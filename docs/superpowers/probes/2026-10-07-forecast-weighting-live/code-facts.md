# Code facts for the live verification of the forecast weighting

Ref read: `upstream/master` = `6a40e083bfa644254c140268f0edbc31b265ede9`.
Method: `git archive upstream/master custom_components/irrigation_plus tests` extracted into a
scratch directory outside the repo (read-only on the repo; the working tree was never touched).

Conventions
- Paths are relative to `custom_components/irrigation_plus/` unless they start with `tests/` or
  `frontend/`. Line numbers are those of `upstream/master`.
- "(inferred)" marks everything that is a conclusion from code, not a line that says so.
- "Not determinable" is written where the code does not decide it (usually: API content, install
  config values).
- Logger name = module `__name__` = `custom_components.irrigation_plus.<module>`;
  the package `__init__.py` logs as `custom_components.irrigation_plus`.

Config keys used below (const.py): `forecast_weighting_enabled` (:76, default False),
`skip_irrigation_on_precipitation` (:37), `precipitation_threshold_mm` (:39, default 2.0),
`precipitation_forecast_days` (:45, default 1), `live_estimate_enabled` (:91, default False),
`autocalcmode` (:328; values `fixed_time` / `before_run`, :329-330).

---------------------------------------------------------------------------------------------------

## Q1 Pirate Weather client

File: `weathermodules/PirateWeatherClient.py`.

Request (:69): `units=si`, `version=1`, `exclude=minutely,alerts`, `extend=hourly`.

`get_forecast_data()` (:233-339) returns `list[dict]` or `None`.
- The list is built from the API's `daily.data` with `for x in range(1, len(data) - 1)` (:259-261):
  API block 0 (the fetch's own "today") and the last block are dropped. The test fixture (recorded
  2026-09-16, Berlin) has 8 daily and 168 hourly entries (tests/test_pirateweather_daily.py:32-36,
  :98-111), so 6 entries. (inferred: 6 on the live API as long as it keeps returning 8 daily blocks.)
- First entry = the local day AFTER the day of the FETCH, i.e. "tomorrow" relative to fetch time, not
  relative to when the cached list is later read (tests/test_pirateweather_daily.py:3-6: "drops the
  first (today) and the last block"). A list fetched on D covers D+1..D+6.
- Per entry (dict): wind speed (adjusted to 2 m), absolute-pressure estimate, humidity %, mean
  temperature = (max+min)/2 (:285-300), max/min temperature, dew point, and
  `MAPPING_PRECIPITATION` = `precipAccumulation * 10.0` (:301-302; code comment: "SI returns cm,
  convert to mm") -> mm per day. Plus `FORECAST_DAY_START` / `FORECAST_DAY_END` = aware UTC
  datetimes from the block's own `time` stamp and the next block's stamp (:313-320), i.e. the local
  midnight bounds (DST day = 23 or 25 h).
- All daily fields are read with `data[...]`, no `.get`. A missing key raises KeyError, which the
  `except` clauses (:330-333, only `RequestException` and `JSONDecodeError`) do not catch.
  (inferred consequence: `forecast_weighting_credit` raises inside `calculate_module`;
  `_async_calculate_all` catches per zone and keeps the zone's previous values,
  calculation.py:540-549. Whether Pirate ever omits `precipAccumulation` is not determinable here.)

`get_hourly_precipitation_forecast(covering_until=None)` (:189-231): implemented.
- Returns `[(aware UTC datetime, mm/h)]` built from `_cached_doc["hourly"]["data"]` (fields `time`,
  `precipIntensity`, a rate in mm/h under SI). `None` if no document was fetched yet or no usable row.
- Never issues a request (:209-211 docstring, :213-215). `covering_until` is accepted and ignored
  (:203-208).
- Stamp convention: handed back as "rate over the hour ENDING at the stamp". The docstring flags this
  as ASSUMED, not verified (:197-207): Dark Sky documents hours BEGINNING at the stamp, which would put
  the series one hour early. Effect: moves rain between two hours, cannot change a whole-window total.
- Reach: the long block (`extend=hourly`) is 168 entries = `floor(fetch hour) + 167 h`; without it 48
  entries = `+47 h` (comment :51-67). Measured on one key on 2026-09-16; the code itself says "do not
  assume every subscription tier serves the long block" (:65-67).
- `_cached_doc` is set by whichever of `get_forecast_data` (:249) or `get_data` (:357) fetched last.
  `get_data` is called by the update cycle only when a mapping uses the weather service as a source
  (`use_weather_service and owm_in_mapping`, __init__.py:1481-1486, :1604-1609) and by the
  temperature/wind/freeze skip guards when enabled (skip_conditions.py:400, :432, :472). If no mapping
  uses the service, the hourly document is only refreshed by `get_forecast_data` fetches. (Whether the
  test instance's mappings use the service: not determinable.)

Caching / rate limiting:
- `_is_fresh` (:138-143): TTL = `max(cache_seconds, 60 s)` (`_MIN_CACHE_SECONDS` :39), separate
  timestamps per method (`_cached_forecast_at` set at :323, `_cached_data_at` at :441). The 60 s floor
  is explicitly there to cap skip checks / outlook / estimate to one call per method per minute (:32-39).
- `cache_seconds` starts at 0 (constructor); `track_update_time` sets it to `auto-update interval - 1 s`
  (__init__.py:1357-1359; daily = 86399, hourly = 3599; minutely lands on the 60 s floor); set to 0 in
  the "auto calculation disabled" branch of `set_up_auto_calc_time` (__init__.py:1326-1329).
  `override_cache` is never set True by any code path (grep: only the constructor default; the name
  appears in a websocket/HTTP schema, websockets.py:300, but no client reads it from there).
- Failure is NOT cached: `_cached_forecast_at` is only set on success. On a non-200 the client retries
  `RETRY_TIMES = 3` (:71, :237-241) immediately without a sleep, logs ERROR "PirateWeather API
  returned error status code: %s" (:243-246) and returns None. A transport error logs ERROR (:331) and
  falls out of the function (returns None implicitly). No back-off, no 429 handling. (inferred: while
  the API is failing, every caller - the live-estimate refresh runs about every minute, see
  live_estimate.py:307-312 - retries up to 3 requests.)
- Consumers of `get_forecast_data`: skip guard (skip_conditions.py:224), forecast weighting
  (calculation.py:1059-1061), live-estimate refresh (live_estimate.py:307-312), freeze guard
  (skip_conditions.py:481), PyETO forecast days (calculation.py:522-525, __init__.py:2112-2114), WS
  `irrigation_plus/weather_forecast` (websockets.py:1124).
- With DEBUG on `custom_components.irrigation_plus.weathermodules.PirateWeatherClient` every real fetch
  logs the WHOLE raw document (":250-254", "PirateWeatherClient get_forecast_data called API %s and
  received %s", API key masked in the URL) and a cache hit logs "Returning cached PirateWeather
  forecastdata" (:338). `get_data` has the equivalents at :358-362 and :456.

---------------------------------------------------------------------------------------------------

## Q2 `expected_rain` semantics (forecast_window.py)

Signature `expected_rain(*, run_start, evaluated_at, days, hourly, daily) -> ExpectedRain(mm,
first_24h_covered, complete)` (:261-299).

Window (`window_intervals`, :141-173):
- `days` = number of rolling blocks of 24 ABSOLUTE hours counted from `run_start` (not calendar
  days). Block `i` = `[run_start + i*24h, run_start + (i+1)*24h)` in UTC (:164-170).
- The part before `evaluated_at` is cut off: block start = `max(block_start, evaluated)` (:169); its
  END stays at `block_start + 24h`. A block with <= 1 s left (`_COVERAGE_TOLERANCE_SECONDS`, :103) is
  dropped, so a block 0 that lies wholly in the past is missing from the list.

Pricing:
- Hourly series (`_hourly_segments`, :180-218): each rate covers the interval ENDING at its stamp,
  at most one step (= smallest spacing) long; the first sample reaches back one step. A larger spacing
  is a hole (uncovered). Duplicate stamps keep the max; non-finite rates are dropped; negative = dry.
  The series is integrated per second over the overlap with each block (:289-294), i.e. pro rata by
  seconds, partial hours at both ends are counted by the fraction inside the window.
- Daily entries (`_entries_behind`, :221-258) fill in ONLY where the hourly series ends: an entry is
  used only if its span starts strictly AFTER the last hourly stamp (:255). Such an entry is spread
  uniformly over its own span (`mm / (end - start)`, :282-285) and counted pro rata by overlap with
  the block (never as a whole day). Without an hourly series (`hourly=None`, `series_end=None`) every
  dated daily entry is used pro rata.
- `first_24h_covered` (:287, :295-298): True iff block 0 exists (not wholly past) AND the pieces
  cover it to within 1 s. False when (i) block 0 is wholly in the past at the evaluation, or (ii)
  hourly rows + daily fill-ins leave more than 1 s of block 0 uncovered. `complete` = every block
  covered. (inferred: `complete` sums overlapping pieces, so overlapping daily entries would be double
  counted; the module says clients do not produce that.)

Concrete case (Pirate Weather, `days = 1`). Calculation at 23:00 on D-1 (`evaluated_at`), `run_start`
= R:
- `window_intervals` -> one block `[R, R + 24 h)` provided R is later than the evaluation, and the
  first block is NOT cut because `max(R, E) = R`. All 24 h are priced.
- With the long hourly block present (168 entries from the fetch hour): the window lies inside the
  series, so the hourly series alone prices it; daily entries are not used at all. A run starting at
  20:27 means: the hour `(20:00, 21:00]` on the first day counts 33/60 of its rate, hours up to
  `(20:00, 21:00]` of the next day count in full, that last hour counts 27/60. (If Pirate's stamps are
  actually hour-beginning, everything shifts by one hour.) Needs the hourly document to reach R+24 h;
  with 168 entries that holds unless the document is ~6 days old (inferred from reach `+167 h`).
- With `hourly=None` (e.g. no document, or an hourly block without `precipIntensity`) only the daily
  list is used: for R = 20:27 on D that is 3 h 33 m / 24 h = 14.8 % of day D's entry plus 20 h 27 m /
  24 h = 85.2 % of day D+1's entry, if both exist. The Pirate list fetched on D-1 starts at D, so both
  exist; a list fetched ON D starts at D+1, the first 3 h 33 m are uncovered, and `first_24h_covered`
  is False (the weighting returns 0.0 silently, see Q8).
- Important for the planning: for a FINISH-anchored schedule with `start_mode: none`, 20:27 is the END
  of the run. The window starts at the run's START, `20:27 - estimated duration` (see Q3b/Q4), not at
  20:27.
- If the calculation happens inside the dispatch (before_run), R = the fire moment and E = a few ms
  later: block 0 = `[E, R + 24 h)`, practically the full 24 h.

---------------------------------------------------------------------------------------------------

## Q3 `async_next_run_start_for_zone` (scheduler.py:1154-1235)

General: iterates `self._schedules`; skips disabled ones (`enabled` default True, :1177); `zones`
default `"all"` (:1182); `"all"` matches every `zone_id` WITHOUT any look at the zone (no state check,
no existence check) - so disabled-state zones are included (:1183-1189). A list is compared via
`{int(z) for z in zones}`. The earliest start across the matching schedules wins (:1190-1193). Returns
None for a non-numeric id (:1171-1174). It never prices anything: bucket-free by construction, pinned
by tests/test_next_run_start_for_zone.py::test_the_resolver_never_prices_a_zone (:187).

Per schedule (`_next_run_start_for_schedule`, :1195-1235): target = `_next_governing_time(schedule,
governing)` = the first matching occurrence strictly AFTER now (:765-792, `_resolve_event_instant`
"clock", forward: if the candidate is <= reference add one day, :615-631) -> then
`_advance_past_fired_occurrence(quiet=True)` (:1213) -> then, if an arm exists for that occurrence,
the arm's start; else the raw target.

(a) Start-anchored daily schedule, `start_mode: time 08:54`, `finish_mode: none`:
`_bounded_ends` -> governing = start, paired = None (:462-475). Returns the next 08:54 local strictly in
the future, as aware UTC (`dt_util.as_utc`, :631). At 23:00 -> tomorrow 08:54; between 00:00 and 08:54 ->
today 08:54; at the dispatch instant 08:54:00.x -> TOMORROW 08:54 (the "+1 day trap", pinned by
tests/test_before_run_anchor.py:84-97). A start-only schedule is armed with `async_track_time_change`
(:1073-1080), records no `_finish_last_target` and no `_armed_runs`, so there is nothing to advance past
and no arm: the answer is the plain target. If `finish_mode` were also set (both ends bounded, anchor
start) the result is the same instant, but then `run_callback` records the fired occurrence (:1754) so
`_advance_past_fired_occurrence` can move it a day.

(b) Zone covered only by the finish-anchored daily schedule (`finish_mode: time 20:27`, `start_mode:
none`): governing = finish, paired = None (:472-473) -> single-stage finish tracker
(`_setup_finish_tracker(fitted=False)`, :434-435, :1609-1633, `_arm_finish_estimate` :1635-1690).
- The resolver itself does not subtract any duration. It returns `armed["start_utc"]` when
  `_armed_runs[sid]` exists with a start and its `target` is within `SAME_OCCURRENCE` (1 h, :62) of the
  occurrence (:1218-1230); otherwise it returns the finish target itself, i.e. the END of the run
  (:1231-1235: "anchors the window at the run's END ... accepted, not fixed").
- The arm's start was computed at arm time as `target - _estimate_duration(schedule)` (:1644-1645),
  and `_estimate_duration` = `coordinator.get_total_irrigation_duration(zones)` (:794-797;
  skip_conditions.py:579-622): `async_plan_zone_runs(zones)` (irrigation.py:2586-2709) -> per eligible
  zone the STORED `duration` if `duration > 0 and bucket < bucket_threshold` (`_zone_run_decision`
  `_daily()`, irrigation.py:2464-2476; with `live_estimate_enabled` the live-sized figure instead),
  plus `hardware_priced_seconds` rounding for self-closing zones, reduced by `concurrent_wall_clock`
  under the configured sequencing (for `parallel`: `max(b + c)` over zones, run_window.py:490-491),
  combined with a distributor track by `max` (skip_conditions.py:609-622). If that start is already
  past: now + 2 s (:1647-1659). The arm is rebuilt on every `_config_updated` (every calculation, every
  run credit): scheduler.py:193-259 (`async_rearm_finish_schedules`). (inferred: during a calculation
  the armed start can be one calculation stale, because the calculation's own `_config_updated`
  re-arm comes after the weighting has asked.)
- After the finish callback fired (`_finish_last_target[sid]` = the target, `_armed_runs` popped,
  :1679-1680) the re-arm resolves the NEXT occurrence (:1569-1605, advance within 1 h).
- Edge: if the estimated duration at arm time is 0 (no zone due then), the armed start equals the
  finish time itself.

(c) A zone named by no enabled schedule (or only by disabled ones, or by an un-anchored interval
schedule): `best` stays None -> returns None (:1175, :1193). `forecast_weighting_credit` then falls back
to measuring from the calculation itself (calculation.py:1097-1117; DEBUG line, see Q8).

Awareness: every path returns an aware UTC datetime (`dt_util.as_utc`, :631; arm's `start_utc` is
`target - timedelta` or `dt_util.utcnow() + 2 s`; interval targets `as_utc` :937). `expected_rain`
converts with `.astimezone(UTC)` (forecast_window.py:164-165).

For the test instance (inferred): at the 23:00 `fixed_time` calculation, zone 2 resolves to the
EARLIER of tomorrow 08:54 (start schedule) and the armed finish start, i.e. tomorrow 08:54. Zones other
than 2 resolve to the armed start of the "all" finish schedule.

---------------------------------------------------------------------------------------------------

## Q4 `autocalcmode: before_run`

Switch (`_before_run_calc_active`, auto_calc.py:36-44): true iff `autocalcmode == "before_run"` AND
`autocalcenabled` (default True). `set_up_auto_calc_time` (__init__.py:1267-1330) then unsubscribes the
23:00 tracker (:1292-1294) and logs INFO (logger `custom_components.irrigation_plus`) "Automatic
calculation runs before each irrigation run; no fixed-time calculation scheduled" (:1301-1304);
`calctime` keeps its value.

Commit function `async_commit_pre_run_calculation(zones=None, *, run_start=None)` (auto_calc.py:46-74):
no-op unless before_run (:64-65); INFO "Committing the pre-run calculation for zones: %s" (:66);
`normalize_zone_selection(zones)`; selection None ("all") -> `_async_calculate_all(run_start=run_start)`
(:69; every automatic zone), else for each id `async_update_zone_config(id, {calculate: True},
run_start=run_start)` (:71-74) -> `async_calculate_zone(..., run_start=...)` (__init__.py:2078-2125) ->
`calculate_module(..., run_start=...)` -> `forecast_weighting_credit(zone, forecastdata,
run_start=run_start)` (calculation.py:1392-1394).
- The per-zone branch RAISES `SmartIrrigationError` when the zone's mapping has no rows/sensor data
  (__init__.py:2094-2100); `_perform_scheduled_irrigation` logs ERROR "Error irrigating schedule zones
  %s: %s" and re-raises (scheduler.py:2441-2443), so the run does not dispatch (inferred consequence).
- The commit is "deliberately ahead of the skip evaluation" so a rain-skipped run still leaves a fresh
  ledger (auto_calc.py:55-57).

Where it is called and which `run_start`:
1. Single-stage schedules (start-only, finish-only, interval), i.e. BOTH schedules on the test
   instance: at the moment the schedule fires, INSIDE the dispatch. Chain: tracker callback ->
   `_execute_schedule(schedule, now)` (pre_committed False) -> task `_perform_scheduled_irrigation(...,
   run_start=now)` (scheduler.py:2330-2340) -> `async_commit_pre_run_calculation(zones,
   run_start=run_start)` (:2363-2376) -> skip guard `_check_skip_conditions()` (:2378) -> dispatch
   (:2406). Order inside the dispatch: commit, skip decision, events, `_irrigate_linked_entities`.
   - Start-only (zone 2, 08:54): `now` = what `async_track_time_change` hands the callback (:1073-1080),
     an aware local datetime at the firing moment (inferred from HA core; the repo comment
     scheduler.py:2317-2325 says "async_track_time_change passes local").
   - Finish-only ("all", 20:27): fires at `finish target - estimated duration` via
     `async_track_point_in_utc_time` (:1690); `finish_callback(now)` first writes `_finish_last_target`
     and pops `_armed_runs` (:1679-1680), then `_execute_schedule(s, now)` (:1681). `now` = the
     scheduled fire instant (aware UTC; inferred from HA core). Hence `run_start` = the run's START
     = `20:27 - estimated duration`, and selection "all" -> `_async_calculate_all(run_start=...)`
     calculates EVERY automatic zone with this one `run_start`.
2. Two-stage schedule pinned to Finish (both ends bounded, anchor finish): the commit happens at the
   DECISION POINT (= the paired Start bound), `_decide_and_arm(commit=True)` -> `async_commit_pre_run_
   calculation(zones)` WITHOUT run_start (scheduler.py:1978-1992); at that moment no arm exists for the
   occurrence yet, so the resolver answers with the raw finish target (inferred from :1218-1235). The
   fire later runs with `pre_committed=True` (:2047), so no second commit. Not used by the test
   instance.
3. Start-pinned with a Finish bound: commits at the fire, `run_start=now` (scheduler.py:1850), then
   `pre_committed=True` (:1870-1872).
4. `fixed_time` (current instance): `_async_calculate_all` via `async_track_time_change` at calctime
   (__init__.py:1310-1316) with `run_start=None` -> resolver (Q3).
5. Ledger guard (before_run only): the midnight callback (__init__.py:2174-2178) calls
   `async_guard_ledger_staleness` (auto_calc.py:76-120); if an automatic zone's `last_calculated` is
   older than 24 h it runs `_async_calculate_all()` with `run_start=None`, INFO "No calculation
   committed in %sh under the before-run calculation mode; committing one now ..." (:114-119).
Why `run_start` is passed: the resolver would answer for the FOLLOWING occurrence at dispatch because
(A) the fire callback already marked this occurrence fired and (B) `_next_governing_time` is strictly
after now (comments scheduler.py:2364-2373, calculation.py:1079-1085).

What a person can observe on a running instance (before_run, schedule fires):
- Log sequence within the same second (default levels): INFO scheduler "Executing recurring schedule:
  <name>" (scheduler.py:2306) -> INFO `...auto_calc` "Committing the pre-run calculation for zones: all"
  or `['2']` (auto_calc.py:66) -> INFO `...calculation` "Calculating all automatic zones"
  (calculation.py:509) for "all", or per listed zone INFO `custom_components.irrigation_plus`
  "Calculating zone N" (__init__.py:2080) -> [DEBUG lines, Q8] -> either INFO `...scheduler` "Schedule
  '<name>': irrigation skipped due to conditions" (:2379) or the run lines (INFO `...irrigation` "Metered
  (timed) irrigation: zone %s for %.0fs @ %.2f L/min", irrigation.py:1472-1477) -> INFO scheduler
  "Successfully irrigated schedule zones: %s" (:2436).
- State: the zone's `last_calculated` (attribute on the zone's duration sensor, formatted
  `%Y-%m-%d %H:%M:%S` naive local, sensor.py:312, :450; stamped `local_naive_now()` at
  calculation.py:628) equals the dispatch time to the second under before_run, instead of 23:00:00 under
  fixed_time. The ISO value is in WS `irrigation_plus/zones` (`last_calculated`).
- There is NO log line that prints the `run_start` that was passed, and none that prints a resolver
  answer. Only the fallback is logged (Q8). Proof of "right `run_start`" is therefore indirect: the
  DEBUG line "forecast weighting X mm rain" (Q8) against a hand integration of the DEBUG-logged raw
  document (Q1) over `[fire, fire + 24 h)` versus over the following occurrence's window; they differ
  only if the hourly rain differs between the two windows. The armed start of a finish schedule is
  visible in INFO scheduler "Finish schedule '%s': target %s, est. duration %ss -> start %s"
  (scheduler.py:1661-1667, logged on every re-arm).

tests/test_before_run_anchor.py (119 lines), one paragraph: pins the "+1 day" defect of the run-start
resolver when it is asked from inside a dispatch. On a daily 06:00 UTC schedule with the clock frozen at
the dispatch moment, it stubs only the clock/sun layer (`_resolve_bound`) and runs
`_next_governing_time` and `_advance_past_fired_occurrence` for real. Test 1 reproduces mechanism (A):
after the finish callback's own bookkeeping (fired marker written, arm popped) the resolver returns
tomorrow's 06:00. Test 2 reproduces mechanism (B) alone: a plain start-time schedule with no fired marker
still returns tomorrow's 06:00, because the resolution is strictly after now. Test 3 pins that
`_decide_and_run_start_pinned` commits at the fire with `run_start=<the fire time>`, i.e.
`async_commit_pre_run_calculation("all", run_start=TODAY_RUN)`. tests/test_auto_calc_mode.py:347-375
pins the other two sides: the decision-point commit passes `run_start=None` and
`_perform_scheduled_irrigation(..., run_start=fired)` hands exactly that moment to the commit.

---------------------------------------------------------------------------------------------------

## Q5 Live-estimate path with forecast weighting

What must be configured: `live_estimate_enabled` true (tested as `is True` everywhere:
irrigation.py:2348, :2394, :2478, live_estimate.py:1724), `forecast_weighting_enabled` true
(irrigation.py:2396, live_estimate.py:1726, calculation.py:1054), `use_weather_service` true with a
client (calculation.py:1052-1056), and `precipitation_forecast_days` (shared window). Per zone: no
`flow_sensor`, `distributor_id` None, `linked_entity` set (or self-closing), and a live estimate must
exist for the zone (else `_zone_run_decision` falls back to the daily gate WITHOUT credit,
irrigation.py:2485-2490; live_estimate.py:1695-1703 warns once per zone/reason). The weighting still
only acts through the daily balance when `live_estimate_enabled` is false (the instance's current
state): `_apply_live_durations` returns the zones unchanged (irrigation.py:2348-2350) and
`_live_forecast_credits` returns `{}` (:2394-2395).

Which zones are live-sized:
- `_zone_run_decision` (irrigation.py:2414-2510): with the live gate on and no `flow_sensor`
  (:2478-2483: flow zones keep the daily gate), the trigger is `live_deficit < bucket_threshold`
  (:2491-2500; the credit does NOT move the trigger, docstring :2453-2458), the size is
  `min(0, live_deficit + credit)` when `credit > 0` (:2501), `_duration_for_deficit` (:2502); 0 ->
  None (zone dropped).
- `_live_forecast_credits` (:2382-2412): skips zones with `ZONE_FLOW_SENSOR` (:2399-2400), asks
  `forecast_weighting_credit(z, run_start=run_start)` per zone, swallows exceptions (DEBUG), keeps `mm > 0`.
- A Gardena distributor MEMBER (`distributor_id` set, no own `flow_sensor`): NOT live-sized in a
  scheduled run. `_irrigate_linked_entities` only takes zones with `distributor_id is None`
  (irrigation.py:889-896, comment :882-888) before it calls `_apply_live_durations` (:960), and the
  distributor itself uses the daily gate on the stored duration (distributor.py:916-925: "Live-estimate
  gating is out of MVP scope"). The daily weighting (calculate_module) DOES apply to members (no
  distributor check there) and the distributor honours `irrigation_target_bucket`
  (distributor.py:1191, :1709, :1892). The published estimate loop excludes only flow zones
  (live_estimate.py:1733-1734), not members, so (inferred) a member's published `live_duration` /
  `forecast_credit` can show a credit that no run uses.
- Callers and their `run_start`: dispatch `_apply_live_durations` passes `dt_util.utcnow()`
  (irrigation.py:2355); queued-zone re-price `_resize_queued_zone` (sequential/rotating, NOT parallel)
  passes `dt_util.utcnow()` (:3318); the planner `async_plan_zone_runs` passes nothing -> resolver
  (:2648); the published estimate passes nothing -> resolver (live_estimate.py:1736).

What shows the live duration (should match the run):
- Panel zone view: `_zoneRunDuration` (frontend/src/views/zones/view-zones.ts:549-566) shows
  `zone_estimates[id].live_duration` when `config.live_estimate_enabled` and the estimate is available,
  else the committed `zone.duration`. Source: WS `irrigation_plus/irrigation_outlook` -> `zone_estimates`
  (skip_conditions.py:150). Backend computes it in `_live_run_duration` (live_estimate.py:1636-1663: None
  for flow zones; with credit it uses `min(0, deficit + credit)`), set at :1615, rewritten with the credit
  in `_credit_forecast_to_estimates` (:1714-1745, also sets `est["forecast_credit"]`, which the TS type
  does not declare, frontend/src/types.ts:219-232), carried forward in `_carry_estimate_to`
  (:1957-1961).
- The "Live bucket" sensor (`SmartIrrigationZoneLiveDeficitSensor`, sensor.py:714-819) shows
  `live_deficit` (unweighted); its attributes do NOT include `live_duration` or `forecast_credit`
  (:777-819) but do include `unavailable_reason`.
- The `next_irrigation` sensor attribute `projected_duration_seconds` (sensor.py:961) comes from
  `async_plan_zone_runs` -> `_zone_run_decision` with credit (scheduler.py:1386-1389, :1528-1530).
- The committed `duration` sensor (state in seconds) is NOT the live figure.

What the run dispatches and where to read it afterwards:
- `_apply_live_durations` returns COPIES `{**z, duration: decision.duration}` (irrigation.py:2379); the
  stored zone `duration` is not changed (run_chain.py:86: "prices that into a COPY that nothing stores").
  INFO `custom_components.irrigation_plus.irrigation` "Live-estimate watering: zone %s %ss -> %ss (live
  deficit %.2f)" (:2372-2378) prints old stored vs dispatched seconds. Under `parallel` the copy goes to
  `_irrigate_zones_parallel` -> `_run_valve_metered`, which times the run at `zone[duration]`
  (:1470) and logs INFO "Metered (timed) irrigation: zone %s for %.0fs @ %.2f L/min" (:1472-1477).
- run_log entry (irrigation.py:3002-3076, newest first, persisted on the zone, WS `irrigation_plus/zones`
  -> `run_log`): fields `ts`, `trigger`, `planned_s` (the dispatched seconds for timed zones, :1645),
  `actual_s`, `volume_l`, `result` (`completed`/`partial`/`failed`/`skipped`), `detail`. For a normal run
  `detail` is the zone's committed `explanation` text (:1656), NOT live text; a deadline cut sets
  `detail` = deadline and `planned_s` = the planned length (:1645-1655).
- Unit caveat (inferred): `live_deficit` is in DISPLAY units (live_estimate.py:1607, :1614), `credit`
  is in mm, and both are added directly (irrigation.py:2501, live_estimate.py:1662). For a metric install
  (the test instance) there is no mismatch; for imperial it would mix inches and mm.

---------------------------------------------------------------------------------------------------

## Q6 Skip guard interplay

Same window: yes in construction. `_eval_precipitation` (skip_conditions.py:162-288) calls the same
`expected_rain` with `days = max(1, precipitation_forecast_days)` (:227-233), the same client hourly
accessor with `covering_until = start + 24h*days` (:241-249) and the same daily list. Differences:
- Anchor: at dispatch the guard is called with NO `run_start` (`_check_skip_conditions` ->
  `async_evaluate_skip_conditions()`, skip_conditions.py:45), so the window starts NOW = dispatch
  (:234-235). Previews name the next run's start (:119-121, scheduler.py:1450-1451). The weighting uses
  the resolver (fixed_time), or the dispatch-passed `run_start` (before_run), or the live paths' `utcnow`.
  Under before_run both therefore start at the same moment (milliseconds apart).
- It needs the daily list non-empty and silently returns "unavailable" otherwise (:224-226); with an
  uncovered first 24 h it logs INFO at dispatch "Precipitation skip: the forecast does not cover the
  first 24 hours from the run's start, so rain is not deciding this run" (:257-267; DEBUG for previews).
- Decision: `observed = round(rain.mm, 2)`; `would_skip = observed >= threshold` (:282-285).

Skip behaviour: a precipitation `would_skip` makes `_check_skip_conditions` return True (INFO "Irrigation
skipped due to conditions: precipitation", skip_conditions.py:51-58); `_perform_scheduled_irrigation`
then logs INFO "Schedule '%s': irrigation skipped due to conditions" (scheduler.py:2378-2382), writes a
`skipped` run-log row with `detail = "precipitation"` to every enabled targeted zone (:2391-2393,
irrigation.py:3095-3113) and RETURNS before `_irrigate_linked_entities`: the whole schedule run, all its
zones. So with a forecast total >= 2 mm in the window (rounded to 2 decimals) the weighting can never be
seen through a run. It is still visible in the calculation (explanation, `irrigation_target_bucket`).
With the guard on and a total below the threshold: the run happens and the weighting shortens it.

Also note (code facts): the weighting is applied only if the true bucket is negative
(calculation.py:1391); it returns 0.0 silently when the weighting is off, there is no weather service,
the daily forecast is falsy, or the first 24 h are not covered (calculation.py:1052-1062, :1125-1136); a
credit >= the deficit gives `effective_bucket = 0` -> duration 0 -> zone not run (dropped, not shortened)
(:1396, :1598, :1749-1751). The dispatch gate still uses the TRUE bucket against `bucket_threshold`
(irrigation.py:909-913).

Fields to change so that a run with forecast rain in the window still happens and is shortened:
- `skip_irrigation_on_precipitation` (const.py:37) -> false, OR keep it on and raise
  `precipitation_threshold_mm` (const.py:39) above the expected window total (stored in mm; WS config
  converts for imperial). Keeping the guard ON with a high threshold has one practical advantage:
  `_eval_precipitation` returns early when disabled (skip_conditions.py:212-213), so with it off the
  outlook (`irrigation_plus/irrigation_outlook` -> `skip_preview.checks[id="precipitation"].observed`,
  `.threshold`, `.would_skip`, `.available`) no longer publishes the window total; with it on, `observed`
  is the same `expected_rain.mm` (rounded) for the next run, readable without any log level.
- `precipitation_forecast_days` (const.py:45) is shared by the guard and the weighting; changing it moves
  both windows. Leave at 1 unless the window itself is the test subject.
- `forecast_weighting_enabled` must be true (default False), `use_weather_service` true.
- (inferred) rain total between 0 and the deficit is required for "shortened"; zones whose
  `bucket >= bucket_threshold` do not water at all (default `bucket_threshold` = -10.0, const.py:516).

---------------------------------------------------------------------------------------------------

## Q7 Dispatch under `fixed_time`, target bucket

- Under `fixed_time`, `async_commit_pre_run_calculation` returns immediately (auto_calc.py:64-65), so a
  scheduled run does no calculation. `_irrigate_linked_entities` reads the zones from the store
  (irrigation.py:854), with `live_estimate_enabled` false the candidates are zones with stored
  `duration > 0` AND `bucket < bucket_threshold` (:909-913), `_apply_live_durations` returns them
  unchanged (:2348-2350), `parallel` -> `_irrigate_zones_parallel` (:1176, :3350-3412) ->
  `_run_valve_metered`, timed at `zone[duration]` (:1470). So yes: the run uses the `duration` stored by
  the last calculation (23:00 under fixed_time). Single-stage schedules pass no deadline/order, so no
  cut (`_execute_schedule(s, now)`, scheduler.py:1681). Zones with a `flow_sensor` instead deliver a
  target VOLUME computed from the same ceiling (:1451-1454).
- Where `irrigation_target_bucket` is applied: `_zone_target_bucket` (irrigation.py:185-191) read by
  `_run_ceiling` (:2843-2880, target at :2878; result `target if pre is None else max(target, pre)`).
  Timed classic run: `ceiling = self._run_ceiling(zone)` (:1468), `_bucket_for(total) = min(ceiling,
  original_bucket + credited depth)` (:1532-1533), final commit (:1616-1621) via
  `async_write_watered_bucket` (:2882-2930) -> `store.async_update_zone`. Flow zones: :1451-1453.
  Rotating: :1859-1894. Self-closing service: self_closing.py:806-807. Batch: batch.py:344.
  Distributor: distributor.py:1191, :1709, :1892.
- Consequence: the bucket ends at the target, e.g. a true bucket of -10 with target -4 ends at -4.0 (not
  0.0), never lower than the pre-run level. `irrigation_target_bucket = newbucket - effective_bucket`
  when a duration > 0, else 0.0 (calculation.py:1760-1766), stored in display units (:1767-1773).
- Visible: zone `bucket` (the zone's bucket sensor `SmartIrrigationZoneBucketEntity`, sensor.py:479-, the
  `bucket` attribute of the duration sensor sensor.py:448, WS `irrigation_plus/zones` -> `bucket`);
  `irrigation_target_bucket` and `explanation` only in the zone dict (WS `irrigation_plus/zones`, the
  duration sensor's attributes do not carry them, sensor.py:441-457). `explanation` for a weighted
  zone contains, after the bucket line, "<localized forecast-weighting-applied> (<true> &rarr;
  <effective>)." (calculation.py:1621-1628; en text: "Forecast weighting reduced the deficit for the
  expected rain", frontend/localize/languages/en.json:97, German :97; the language is
  `hass.config.language`).
- run_log: row with `result: completed`, `planned_s` = dispatched seconds, `actual_s`, `volume_l`,
  `detail` = the explanation text at dispatch (irrigation.py:1632-1661). The run_log carries NEITHER
  the credit NOR the target. `duration` is not zeroed after the run (store only zeroes it when the
  bucket is exactly 0.0, store.py:1807-1813), so (inferred) the stored duration stays until the next
  calculation; whether the zone is "due" again for a second schedule that day depends on
  `leftover target < bucket_threshold`. With the default threshold -10 a leftover of -4 is not due; with
  a threshold >= the leftover it would be, and zone 2 sits in two schedules (08:54 and "all").
- A calculation that lands while the zone is running is deferred (calculation.py:597-604), so the
  target/duration are not rewritten mid-run.

---------------------------------------------------------------------------------------------------

## Q8 Observability (what `logger.set_level` can switch on)

`forecast_weighting_credit` and `calculate_module` log under `custom_components.irrigation_plus.calculation`.

Credit in mm:
- DEBUG calculation.py:1397-1403 `[calculate-module]: forecast weighting %.2f mm rain -> effective bucket
  %.2f (true %.2f)`. Only when the credit is > 0 and the true bucket < 0. The arrow in the source is a
  Unicode arrow.
- No log of the credit in the live paths (irrigation.py / live_estimate.py log nothing with the mm value).
  The published estimate carries it as `forecast_credit` in WS `irrigation_plus/irrigation_outlook`
  (Q5).
- Zone `explanation` (zone dict) shows `(true -> effective)`.

Anchor:
- Fallback only (no schedule resolves and no run_start passed): DEBUG calculation.py:1112-1117
  `[calculate-module]: no scheduled run resolves for zone %s, so the forecast weighting measures from this
  calculation`.
- Resolver answer and dispatch-passed `run_start`: NOT logged. Indirect: INFO scheduler.py:1661-1667
  "Finish schedule '%s': target %s, est. duration %ss -> start %s" (logger
  `custom_components.irrigation_plus.scheduler`, each re-arm) = the armed start the resolver returns;
  INFO scheduler.py:2306 "Executing recurring schedule: %s" (timestamp of the dispatch).
  Start-only time schedules (zone 2) log no "Registered ..." line (scheduler.py:1073-1080).

`first_24h_covered` refusal:
- Weighting: DEBUG calculation.py:1130-1135 `[calculate-module]: the forecast does not cover the first 24
  hours from zone %s's run, so it is not weighted`.
- Skip guard (separate decision, same window): `custom_components.irrigation_plus.skip_conditions`, INFO at
  dispatch / DEBUG for previews, skip_conditions.py:261-266 "Precipitation skip: the forecast does not
  cover the first 24 hours from the run's start, so rain is not deciding this run"; DEBUG :269-273
  "Precipitation skip: the forecast covers only part of the %s x 24-hour window"; DEBUG :287 "Skip
  preview: precipitation eval failed: %s"; INFO :57 "Irrigation skipped due to conditions: %s".
- Silent returns of 0.0 (no log): weighting off, no weather service, `get_forecast_data` returned
  None/empty (calculation.py:1052-1062, :1138), true bucket >= 0 (:1391).

Live credits (`custom_components.irrigation_plus.irrigation` unless noted):
- INFO irrigation.py:2372-2378 "Live-estimate watering: zone %s %ss -> %ss (live deficit %.2f)".
- DEBUG irrigation.py:2493-2499 "Live-estimate watering: zone %s live deficit %.2f hasn't crossed the
  threshold %.2f - not watering this run".
- DEBUG irrigation.py:2404-2408 "Zone %s: forecast weighting credit unavailable: %s".
- INFO irrigation.py:3341-3347 "Zone %s re-priced from %ss to %ss before its turn (live deficit %.2f)";
  INFO :3327-3331 "Zone %s no longer needs water by the time its turn came (rain or an earlier credit);
  skipping the rest of its run". Sequential/rotating only; not under `parallel`.
- DEBUG `custom_components.irrigation_plus.live_estimate` live_estimate.py:1738 "forecast weighting credit
  unavailable: %s"; WARNING live_estimate.py:1697-1703 "Live-estimate watering is on, but zone %s has no live
  estimate (%s); its runs are sized from the last calculation instead".
- The `[calculate-module]: ...` lines of `forecast_weighting_credit` (calculation logger) also fire from the
  live paths, because they call the same function.

Weather client / document:
- `custom_components.irrigation_plus.weathermodules.PirateWeatherClient`: DEBUG :250-254 (full raw document
  on every real fetch), DEBUG :338 "Returning cached PirateWeather forecastdata", ERROR :243-246 status code,
  ERROR :331/:333 transport/JSON errors, WARNING :325-328 missing `daily` key.

Calculation / dispatch frame (default INFO): `custom_components.irrigation_plus.auto_calc` :66, :114;
`custom_components.irrigation_plus.calculation` :509, :599 ("Zone %s is being watered; deferring its
calculation ..."); `custom_components.irrigation_plus` (package) :1301, :1317, :2080;
`custom_components.irrigation_plus.scheduler` :2306, :2379, :2436, :2441-2443 (ERROR).
Also useful DEBUG: calculation.py:1154 "calculate_module for zone: %s" (prints the whole zone dict, includes
`bucket`, `duration`, `irrigation_target_bucket`), :1234, :1380 ("newbucket").

Suggested `logger.set_level` keys: `custom_components.irrigation_plus.calculation`,
`...skip_conditions`, `...scheduler`, `...auto_calc`, `...irrigation`, `...live_estimate`,
`...weathermodules.PirateWeatherClient`, and `custom_components.irrigation_plus` for the package lines.

---------------------------------------------------------------------------------------------------

## Q9 Reading the forecast data the integration uses

No command exposes the raw Pirate document or the hourly series. What exists (all WS commands are
registered in websockets.py:1169-1420; HTTP views are POST-only except `watering_calendar`, :173/:208/
:251/:341/:462 are `post`, :688 is `get`):

1. WS `irrigation_plus/weather_forecast` (websockets.py:1104-1166, registered :1413-1420): the daily list
   from `client.get_forecast_data` (cache-aware, so it may trigger a fetch): `{"available": bool, "days":
   [{"date", "temp_min", "temp_max", "precipitation", "windspeed"}]}`; `precipitation` = the daily mm used
   as fill-in; metric values; `date` labelled by the span's middle in local time (:1134-1155). Hourly data
   and the day spans are not returned.
2. WS `irrigation_plus/irrigation_outlook` (websockets.py:797-813; skip_conditions.py:88-160): `skip_preview.
   checks[]` with the precipitation guard (`observed` = `expected_rain.mm` rounded, for the next irrigate run
   that has not started, `threshold`, `would_skip`, `available`, `enabled`), `upcoming_runs` (per schedule
   `next_run_utc`, `target_utc`, `duration_seconds`, `estimated`), `zone_estimates` (live deficit, live
   duration, `forecast_credit` when weighting+live apply), `last_skip_evaluation`. `observed` only exists
   while `skip_irrigation_on_precipitation` is on (skip_conditions.py:212-213).
3. WS `irrigation_plus/zones` (websockets.py:521-525): full zone dicts (`attr.asdict` of the zone entry,
   store.py:246-337): `bucket`, `duration`, `explanation`, `irrigation_target_bucket`, `last_calculated`,
   `run_log`, `linked_entity`, `run_service`, `watering_mode`, `distributor_id`, `flow_sensor`, ...
4. WS `irrigation_plus/config` (websockets.py:475-517): config incl. `autocalcmode`,
   `forecast_weighting_enabled`, `live_estimate_enabled`, `precipitation_*`, `recurring_schedules`, and
   `version`.
5. WS `irrigation_plus/schedules` (websockets.py:714-): the schedules (nominal demand per schedule).
6. WS `irrigation_plus/weather_records` (websockets.py:562-659): the mapping's reading buffer (observations,
   NOT forecast; Pirate `get_data` stores the current `precipIntensity` as precipitation).
7. WS `irrigation_plus/watering_calendar` and GET `/api/irrigation_plus/watering_calendar?zone_id=` (websockets.py:
   663-710): 12-month calendar, not the forecast.
8. Entity attributes: the zone's `next_irrigation` sensor: `projected_rain`, `forecast_tier`,
   `projected_duration_seconds`, `projected_start_utc`, `decision_point_utc`, `projection_state`,
   `skip_reasons` (sensor.py:911-970); the "Live bucket" sensor: `live_deficit` state, `forecast_tier`,
   `unavailable_reason` (sensor.py:777-819). These come from `day_projection`, not from the weighting.
9. Services: `calculate_zone`, `calculate_all_zones` (services.py:83, :96) trigger a calculation with
   `run_start=None` (resolver/fallback); no service returns forecast data. `diagnostics.py` contains no
   forecast data (grep).
10. The only way to see the raw document (including the hourly block) is the DEBUG log of the Pirate client
    (Q1/Q8), or an external call with the same URL pattern (key in `D:\Entwicklung\HASI\secrets`, never in
    logs/commits; the client masks it as `***` in its own log line).

---------------------------------------------------------------------------------------------------

## Q10 Classic zone with both `linked_entity` and `run_service`

The run actuates `linked_entity` only; `run_service` is ignored.
- Mode test: `is_self_closing_zone` is true only for `watering_mode` in {`service`, `opensprinkler`, `batch`}
  (self_closing.py:91-103; `_sc_is_self_closing` delegates, :1410-1419). `classic` (also the stored default,
  store.py:301, :757) is not self-closing.
- Dispatch: `_dispatch_by_mode` (irrigation.py:1020-1079): self-closing zones go to the service/OpenSprinkler/
  batch paths; `linked = [z for z in zones if not self._sc_is_self_closing(z)]` -> `_dispatch_sequencing`
  (:1133-1176) -> `_irrigate_zones_parallel` / sequential / rotating, each taking `zone[linked_entity]`
  (:3375, :3226, :2102, :2173) -> `_run_valve_metered` opens it with `async_actuate(hass, entity_id, True)`
  (:1491) and closes it (:1582; the finally-net :1676). `async_actuate` (actuate.py:23-34): `valve.*` ->
  `valve.open_valve` / `valve.close_valve`; everything else (`switch`, `input_boolean`) -> `turn_on` / `turn_off`.
  The open is confirmed by polling `linked_entity`'s state (irrigation.py:1492).
- `run_service` is read only inside self-closing code: `_sc_service_open` (self_closing.py:184-195) and the
  run record (:822-824). `ZONE_RUN_SERVICE` has no other consumer (grep).
- Gate: `_irrigate_linked_entities` requires `linked_entity` OR a self-closing mode (irrigation.py:893), so a
  classic zone with ONLY `run_service` is never dispatched by a schedule at all (manual `run_zone` logs
  "no linked entity", irrigation.py:3511-3513).
- Exception: a classic zone whose `linked_entity` is an OpenSprinkler station switch is refused with an
  ERROR (irrigation.py:1101-1131).
- Reverse case, for completeness: with `watering_mode: service` and both set, only `run_service` is fired
  (self_closing.py:172-195); `linked_entity` is not actuated (it only appears in fault payloads, :535, and for
  OpenSprinkler as the station).
- Which physical output a zone switches: classic = the entity in `linked_entity` (open/close via domain
  service); the Z2M valve script behind `run_service` is not touched in classic mode.
