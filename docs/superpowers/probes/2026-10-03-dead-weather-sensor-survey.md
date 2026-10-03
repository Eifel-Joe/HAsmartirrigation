# Eifel-Joe#8 factual survey at `e9c79ec4` (release v2026.10.03)

Read-only survey for a later design spec. Facts and open questions only, no recommendations.

## 0. Basis and conventions

- Tree: `D:/Entwicklung/HASI/prodrebuild-1003-work/base`, HEAD `e9c79ec4` ("build: release v2026.10.03", 2026-10-02 21:19 +0200), clean. The earlier check was against `1876aa03` ("build: release v2026.09.27", 2026-09-28), an ancestor of `e9c79ec4`.
- `file:line` are at `e9c79ec4` and relative to `custom_components/irrigation_plus/` (tests: `tests/...`, docs: `docs/...`). "was N" is the line at `1876aa03`.
- EXEC = executed by me, read-only: repo `.venv` Python 3.12.0, `python -B`, stdin script, modules imported from the base tree, nothing written (tree still clean afterwards). Inputs are synthetic, not production data.
- [HA-venv] = Home Assistant 2024.12.5 in `D:/Entwicklung/HASI/HAsmartirrigation/.venv/Lib/site-packages/homeassistant/` (outside the repo). `hacs.json:4` declares the floor 2025.5.0. What production runs is not derivable from the code.

---

## A. Re-check of claims 1-6

### A.0 What changed in the two files since `1876aa03`

`git diff 1876aa03 e9c79ec4 --stat -- calculation.py weather_aggregate.py`: 2 files, +299/-184 (`calculation.py` +266/-120, `weather_aggregate.py` +33/-64).

Three commits touch them. `a503dc40` (#186) is not among the commits named in the task, but it is the one that touches both files.

| Commit | `calculation.py` | `weather_aggregate.py` |
|---|---|---|
| `a503dc40` (#186, 2026-10-01, "weather buffer on one clock - HA's") | default `now`: `datetime.now()` -> `local_naive_now()` in `_async_clear_all_weatherdata` (338), `_prune_mapping_buffer` (450), `_async_calculate_all` (503), `async_calculate_zone` (569), `calculate_module` (1161); comments in `pending_bucket_events` (58-84) and `_hourly_et_for_zone` (910-930); imports | `_parse` docstring (103-114); `now` default `local_naive_now()` in `aggregate_window` (356), `build_hourly_rows` (916), `build_substeps` (1103); import (45) |
| `faa05b0b` (#159, 2026-10-01) | `forecast_weighting_credit` extracted (1030-1129); weighting block in `calculate_module` replaced by one call (1382-1394) | none |
| `98859077` (#187, 2026-10-02) | `hourly_radiation_series` (190-206), `trailing_radiation_calibration` (209-246), `_record_window_radiation` (685-743) and its call (617) | none |

`4b417066` is tests-only; `07891c6e`, `fcb88258`, `e9c79ec4` are release commits. None of them touches these two files.

EXEC (AST comparison of both revisions, docstrings and comments stripped, `datetime.now()` and `local_naive_now()` treated as equal): 26 functions of `weather_aggregate.py` (incl. `select_window`, `merge_latest_per_field`, `_group_by_sensor`, `_window_bounds`, `_time_weighted_mean`, `aggregate_window`, `effective_aggregate`, `_aggregate`, `_effective_series`, `build_hourly_rows`, `build_substeps`) and 9 of 11 functions of `calculation.py` (incl. `_prune_mapping_buffer`, `_aggregate_for_zone`, `_hourly_et_for_zone`, `_substeps_for_zone`, `strip_foreign_source_values`) are identical. The two that differ are `async_calculate_zone` (the added `_record_window_radiation` call, `98859077`) and `calculate_module` (`faa05b0b`). The comparison deliberately does not see the clock-frame change; that one is read from the hunks above.

Verdict per item:

| Item | Changed since `1876aa03`? |
|---|---|
| Pruning (`_prune_mapping_buffer`) | No logic change. Only the default clock of `now` (`a503dc40`, `calculation.py:450`). |
| Re-stamping of the boundary row | No. |
| `last_entry` backfill | No. |
| Carry-forward (window end, hold) | No. |
| Single-sample branch | No. |
| `aggregate_window` returns None | No. |

Indirect: the `now` that closes windows (`_window_bounds`, `weather_aggregate.py:224`) is now HA's clock by default (`a503dc40`), and the store's 14.2 migration lifts stored `RETRIEVED_AT` stamps onto HA's clock (`store.py:616-661`, `664-678`).

### A.1 `_prune_mapping_buffer` keeps, per field, the latest pre-cutoff row with no age limit

Now `calculation.py:431-490`, loop and boundary part at `458-481` (was 400-410). Holds verbatim.

```
458:        cap_cutoff = now - BUFFER_RETENTION
459:        watermarks, any_unconsumed = self.store.get_enabled_zone_watermarks(mapping_id)
460:        if any_unconsumed or not watermarks:
461:            cutoff = cap_cutoff
462:        else:
463:            cutoff = max(cap_cutoff, min(watermarks))
465:        kept = []
466:        boundaries = {}  # field -> (rt, row): latest pre-cutoff row per field
467:        for r in readings:
...
471:            if rt is None or rt > cutoff:
472:                kept.append(r)
473:            else:
474:                merge_latest_per_field(boundaries, rt, r, keep_row=True)
...
481:        kept[:0] = [row for _, row in boundary_rows]
```

- `BUFFER_RETENTION = timedelta(days=7)` (`calculation.py:55`) is only used at 458, i.e. it moves the cutoff. Nothing tests the age of a boundary row (`merge_latest_per_field`, `weather_aggregate.py:118-134`, keeps the latest-stamped non-null value per field).
- The docstring says the prune "hard-drops anything older than the retention cap" (`calculation.py:436-437`). The code does not drop a field's latest pre-cutoff row past the cap.
- Rows whose `RETRIEVED_AT` does not parse are always kept (`471-472`).
- EXEC-1 below: 160 rows -> 2 rows, one of them 30 days old.

### A.2 The boundary row is re-stamped to the watermark before aggregation

Now `weather_aggregate.py:365-368` (was 380-383). Holds verbatim.

```
365:    effective = []
366:    if boundary is not None:
367:        effective.append({**boundary, const.RETRIEVED_AT: watermark})
368:    effective.extend(window)
```

- The per-field stamp is already gone one step earlier: `select_window` returns `{key: val for key, (_, val) in fields.items()}` (`weather_aggregate.py:178`), and `boundary[RETRIEVED_AT]` (`179`) is the stamp of the newest pre-watermark row (`164-172`), not of any field. EXEC-1: a 30-day-old Temperature value comes back under a 6-hour-old boundary stamp.
- The stored buffer rows keep their original stamps (prune keeps the rows themselves, `calculation.py:474,481`).
- Sibling re-stamp in `_effective_series` (`weather_aggregate.py:712-715`), the entry for `build_hourly_rows` and `build_substeps`.

### A.3 `last_entry` backfills a field missing from the window with an unstamped single value

Now `weather_aggregate.py:370-396` (was 385-411). Holds verbatim.

```
371:    if last_entry:
372:        for key, val in last_entry.items():
373:            if key in by_sensor or val is None:
374:                continue
...
392:            if effective_aggregate(key, mappings_config) in _INTEGRAL_AGGREGATES:
393:                continue
394:            # No stamp: a carry-forward is a single value, which every aggregate
395:            # resolves without needing to know when it was read.
396:            by_sensor[key] = [(None, val)]
```

- `_INTEGRAL_AGGREGATES` = riemannsum, sum (`weather_aggregate.py:96-99`); DELTA is deliberately backfilled (comment `388-391`).
- `last_entry` stores values without stamps: `store.set_mapping_last_entry_value` writes `{key: value}` (`store.py:2130-2133`). Written only by the event path (`continuous_update.py:289`, `450`). Passed to the aggregation unconditionally, i.e. also with `continuousupdates` off (`calculation.py:415`, `937`; `live_estimate.py:616`, `759`). Keys are never removed (`store.py:2175-2180`); reset and source change set the values to None (`calculation.py:361-363`, `__init__.py:1783-1790`).
- Sibling: `build_hourly_rows` uses `last_entry[key]` as one sample at the window start (`weather_aggregate.py:931-936`). `live_estimate._latest_temperature` reads `last_entry[Temperature]` directly as "the CURRENT reading" (`live_estimate.py:880-900`).

### A.4 Carrying forward is deliberate

Now `weather_aggregate.py:217-220` docstring and `222-227` code of `_window_bounds` (was 224-227). Holds verbatim.

```
217:     End is ``now``, not the last reading. A field that stopped producing rows has
218:     not stopped existing, and for solar radiation "produced no rows" is precisely
219:     what a night looks like. Clamped past any reading stamped after ``now`` so a
220:     clock skew cannot yield a negative-length window.
...
224:     end = max([now, *stamps]) if stamps else now
```

- The same hold in `_time_weighted_mean` (`weather_aggregate.py:282-300`: first sample held back to the start, last held forward to the end) and `_hold_integral_table` (`612-637`, extension at `629-631`); hourly rows state it as the missing-hour policy (`874-880`).
- The comment at `weather_aggregate.py:283-284` says "the buffer retains only a single pre-watermark row"; the prune keeps one per field (`calculation.py:439-445`). Facts only: the comment predates that change.

### A.5 `aggregate_window` returns None only without boundary and window

Now `weather_aggregate.py:359-361` (was 374-376). Holds verbatim. It is the only `return None`; the other exit is `return resultdata` (`409`).

```
359:    boundary, window = select_window(readings, watermark)
360:    if boundary is None and not window:
361:        return None
```

`select_window` puts every dict row after the watermark into `window` (`166-175`), so a window of stamp-only rows is a window (EXEC-3: result `{'data_multiplier': 1.0}`).

### A.6 The single-sample branch passes the boundary on as the value

Now `weather_aggregate.py:523-527` in `_aggregate` (was 538-542). Holds verbatim.

```
521:        if aggregate == const.MAPPING_CONF_AGGREGATE_DELTA:
522:            resultdata[key] = cumulative_delta_total(d)
523:        elif len(d) < 2:
524:            if key == const.MAPPING_TEMPERATURE:
525:                resultdata[const.MAPPING_MAX_TEMP] = d[0]
526:                resultdata[const.MAPPING_MIN_TEMP] = d[0]
527:            resultdata[key] = d[0]
```

The branch precedes the dispatch on aggregate type, so it serves average, first, last, maximum, minimum, median, sum and riemannsum alike; DELTA gets 0.0 from a single sample (`cumulative_delta_increments`, `463-477`).

### A.7 Executed checks (EXEC, synthetic, against `e9c79ec4`)

- EXEC-1. Poll-style full rows every 6 h for 40 days, Temperature only up to 30 days before `now`; one zone, watermark 1 h before `now`; then one fresh row after the watermark without Temperature. `_prune_mapping_buffer`: 160 -> 2 rows (the newest pre-cutoff row and a row 30 days old carrying Temperature). `aggregate_window` over that buffer: Temperature = Tmax = Tmin = 12.0, with `time_weighted` False and True. Boundary-only window (no row after the watermark): same 12.0. `select_window` boundary stamp: the newest pre-watermark row (6 h old). `last_entry={Temperature: 12.0}` with no Temperature row anywhere: Temperature = Tmax = Tmin = 12.0.
- EXEC-2. Sensor dies 2 h into a 24 h window (last Temperature row 30, boundary 10): `time_weighted` False -> Temperature 20.000; True -> 28.333 (value held to the window end); Tmax 30 and Tmin 10 in both.
- EXEC-3. Boundary-only Solar Radiation 40.0: every aggregate returns 40.0 except delta (0.0). Weather-service Precipitation (default riemannsum), boundary-only rate 2.0 -> 2.0. Sensor Precipitation (default delta), 30-day-old boundary only -> 0.0. Stamp-only window -> `{'data_multiplier': 1.0}`; empty buffer -> None.
- EXEC-4. `build_hourly_rows` from a single 30-day-old boundary row: 24 rows carrying the frozen values (temperature 18.0, humidity 60.0, wind 2.0, solar_mj_h 0.625). Without any Solar Radiation sample -> None; with `last_entry` Solar Radiation -> rows.

---

## B. Data flow inventory

### B.1 Writers of buffer rows

All rows reach `store.buffers` through `append_mapping_reading` (`store.py:1953-1968`) or `merge_or_append_mapping_reading` (`store.py:2024-2081`, 100 ms coalescing, never into a row at or behind the lowest enabled-zone watermark). Neither schedules a save; `set_mapping_buffer` (`store.py:2084-2098`) does and is the replace path (prune, clear, source change). Stamp function everywhere: `local_naive_now()` = `dt_util.now().replace(tzinfo=None)` (`helpers.py:1061-1076`). Tests that drive each writer once and pin its clock, plus an AST tripwire against a bare `datetime.now()` in the buffer modules: `tests/test_weather_buffer_one_frame.py:349-446`, `491-545`.

| # | Writer | Where | Trigger | Row content | Stamp |
|---|---|---|---|---|---|
| 1 | `_async_update_zone` | `__init__.py:1449-1538` (append `1504`) | single-zone refresh (`__init__.py:2108-2110`) | service row if the group has a service-sourced field (`1464-1477`), minus fields mapped to sensor/static (`1484`), plus sensor values (`1486-1489`), plus static values (`1490-1494`), pressure normalised (`1495-1496`) | `1500` |
| 2 | `_async_update_all` | `__init__.py:1540-1663` (append `1629`) | timer `async_track_time_interval` (`1348-1350`; default hourly, `const.py:343-348`), button (`button.py:306`), service (`services.py:102`), `__init__.py:2111-2113` | same shape as 1; pure-sensor groups skipped when `continuousupdates` is on (`1559-1584`); a failing weather service skips the whole group, sensor fields included (`1593-1605`) | `1626` |
| 3 | `_continuous_seed_baseline` | `continuous_update.py:231-296` (append `281-286`, last_entry `289`) | (re)subscription | one field per readable sensor-mapped field; `None`/`unknown`/`unavailable`/non-numeric skipped (`264-269`) | `253`, captured once |
| 4 | `_sensor_state_changed` | `continuous_update.py:349-461` (append `439-445`, last_entry `450`) | `async_track_state_change_event` (`186-188`) | `{field: value, RETRIEVED_AT}` per target (`385-445`); deadband (`391-392`, `463-477`) | `380` |

`MAPPING_DATA_LAST_ENTRY` is written only by `set_mapping_last_entry_value` (`store.py:2101-2133`) from writers 3 and 4. The poll never writes it. Defaults: `continuousupdates` off (`const.py:112-113`), `hourlycalculation` off (`const.py:122-123`), poll hourly every 1 (`const.py:343-348`).

### B.2 Prune call sites

| Call site | Where | `now` | Note |
|---|---|---|---|
| `_async_calculate_all`, once per touched mapping after all zones | `calculation.py:543-545` | shared `local_naive_now()` (`503`) | zones run with `prune=False` (`528`) |
| `async_calculate_zone` (default `prune=True`) | `calculation.py:626-627` | caller's `now` | single-zone calculation (`__init__.py:2101`) |
| continuous flush, every 20th debounced flush | `continuous_update.py:541-547` (`CONTINUOUS_PRUNE_EVERY`, `116`) | `local_naive_now()` (`523`) | then `_continuous_enforce_row_cap` (`558-589`): keeps `data[0]` plus the last 20000 rows (`574-575`), not per-field boundaries |

The poll writers never prune. Cutoff: `now - 7 days`, or `max(that, min(watermarks))` when every enabled zone has consumed (`calculation.py:458-463`); "enabled" = not DISABLED (`store.py:1992-1993`); a never-consumed enabled zone makes the cutoff the 7-day cap (`calculation.py:460-461`). New zones are anchored at creation (`store.py:1727-1731`), legacy zones may still have no watermark (`store.py:1234-1240`).

### B.3 Consumers of the pruned buffer

Case key for the last two columns: S = field silent for N hours, last row inside the window; B = last row before the watermark (only the per-field boundary); X = never produced and no `last_entry`.

| Consumer | Entry and route | S | B | X |
|---|---|---|---|---|
| Daily commit | `async_calculate_zone` (`calculation.py:551-633`) -> `_aggregate_for_zone` (`388-429`) -> `aggregate_window` with `last_entry` (`415`) and `time_weighted` = `continuousupdates is True` (`420-427`) | flag off: plain mean over rows (`542`); on: last value held to the window end (`222-227`, `282-301`) | re-stamped to the watermark; single sample returned verbatim (`523-527`) or first sample of the series | `last_entry` single value (`371-396`), else field absent: PyETO daily form needs Dewpoint, min/max Temperature, Windspeed, Pressure, else WARNING and delta 0 (`calcmodules/pyeto/__init__.py:114-120`, `303`, `438-463`); watermark still advances (`calculation.py:622`); Precipitation absent -> 0 (`calculation.py:1209`); Passthrough without Evapotranspiration -> error, calculation returns None (`1213-1223`) |
| Hourly commit (opt-in) | `_hourly_et_for_zone` (`calculation.py:853-957`, gates `885-897`) -> `hourly_eto_priced` (`et_estimate.py:148-191`) -> `build_hourly_rows` (`weather_aggregate.py:854-1021`) with `last_entry` (`calculation.py:937`) | zero-order hold per hour (`874-880`, `629-631`); solar: held clearness ratio for hours without a reading (`756-851`, `1017-1020`) | re-stamped (`712-715`), held over the whole window (EXEC-4) | `last_entry` as a sample at the window start (`931-936`); a required field (Temperature, Humidity, Windspeed, Solar Radiation, `70-75`) still missing -> None -> daily form (`calculation.py:943-944`, `1192-1207`); Pressure optional (`927-942`) |
| Replayed balance | `_substeps_for_zone` (`calculation.py:959-1009`) -> `build_substeps` (`weather_aggregate.py:1058-1208`) | reads only Precipitation (`1111-1122`) and Solar Radiation weights (`1159-1166`); no `last_entry` | as above via `_effective_series` | no solar -> elapsed-time weights (`1174-1177`) |
| Live estimate, precipitation and daily mirror | `_aggregate_live_window` (`live_estimate.py:589-628`; anchor = `max(last_calculated, last_consumed)`, `240-260`) -> `aggregate_window` with `last_entry` (`616`) and the same flag (`620-627`); used by `_observed_precip_since_mm` (`630-652`), `_daily_mirror_et` (`1095-1134`), `_carry_estimate_to` (`1882`) | as the daily commit, window closes at `now` | as the daily commit | as the daily commit |
| Live estimate, hourly source | `_buffer_hourly_et` (`live_estimate.py:710-785`, gate `654-708`) -> `hourly_eto_priced` with `last_entry` (`759`); completed hours carried (`181-205`, `766-785`) | as hourly commit | as hourly commit | as hourly commit; None -> falls through to mirror, client rows or proxy (`1383-1506`), else `REASON_NO_ET_SOURCE` (`1455`, `1477`) |
| Live estimate, water steps | `_buffer_water_steps` (`live_estimate.py:1136-1196`) -> `build_substeps` | as replayed balance | | |
| Live estimate, temperature anchor | `_latest_temperature` (`live_estimate.py:880-900`) reads `last_entry[Temperature]` directly, window mean only as fallback; used by `_projected_extremes` (`936-944`) | n/a | n/a | n/a |
| Radiation calibration (PR 187) | `_record_window_radiation` (`calculation.py:685-743`, called `617`) records `weatherdata[Solar Radiation]` of the commit's own `aggregate_window` result (`693`, `720`) as `[date, measured, forecast, ceiling]` (`735`); read by `trailing_radiation_calibration` (`209-246`) -> `_projected_radiation` (`live_estimate.py:1058-1093`) -> `_composed_day_et` (`1029-1038`) | inherits the commit's hold | inherits the verbatim boundary value | no `Solar Radiation` -> nothing recorded (`695`) |
| Temperature amplitude record | `_record_window_amplitude` (`calculation.py:635-683`) reads min/max Temperature of the same result | inherits | inherits | skipped if either is None (`661-662`) |
| Panel weather records | `websocket_get_weather_records` (`websockets.py:561-659`), shown in `frontend/src/views/weather/view-weather-data.ts:70-86`, `345`, `382` | raw rows with `retrieval_time` | raw rows | raw rows |
| Row cap | `continuous_update.py:558-589` | raw | n/a | n/a |

`irrigation.py:2323-2380` (`_apply_live_durations`) sizes runs from the live estimate when `live_estimate_enabled`; `scheduler.py:1374-1382` projects it to the decision point; `skip_conditions.py:130-152` publishes it with `zone_faults` in the outlook.

Not buffer consumers: the freeze/temperature/wind guards read the weather client (`skip_conditions.py:379-494`); the soil-moisture veto and the rain sensor guard read HA states (`irrigation.py:709-735`, `skip_conditions.py:496-516`).

### B.4 Facts about "no rows"

- Poll mode (the default): every tick appends a row with each field readable at that moment (`__init__.py:1871-1930`). A field absent for hours means unreadable at every tick, or a unit conversion that returned None (`helpers.py:128-141`; the poll stores the None, `__init__.py:1907-1923`; later skipped, `weather_aggregate.py:130-131`, `201`).
- A numeric but stale state is rewritten at every tick with a fresh stamp; `State.last_reported` / `last_updated` are not read for weather sensors.
- Event mode: a field gets a row only on a HA state change beyond its deadband (`continuous_update.py:93-102`, `463-477`). `async_track_state_change_event` is the subscription (`186-188`). [HA-venv] `helpers/event.py:309-328`: it follows `state_changed`; a write with equal state and attributes fires `state_reported` instead and only bumps `last_reported` (`core.py:2350-2359`). The repo subscribes to no `state_reported` event.
- The poll can append a stamp-only row: pure-sensor group, every sensor unreadable -> `merge_weatherdata_and_sensor_values(None, {})` returns `{}` (`calculation.py:306-307`) -> row `{RETRIEVED_AT}` (`__init__.py:1625-1629`); zone `last_updated` and the data-point count still advance (`1636-1648`).
- After an outage, a first recovered value within the deadband of the last appended one produces no row (`continuous_update.py:391-392`, `463-477`); the reference `_continuous_last_value` is in memory only (`316-317`, `336-337`).
- Per-mapping bookkeeping stamps: `MAPPING_DATA_LAST_UPDATED` (`__init__.py:1511-1513`, `continuous_update.py:524-526`) and zone `last_updated` are written but read by none of the B.3 consumers (zone `last_updated` is shown by the `last_weather_update` diagnostic sensor, E.4). They are not per field.
- Age-like constants in the weather paths: `BUFFER_RETENTION` 7 days (`calculation.py:55`); hourly window cap 168 h (`weather_aggregate.py:61-65`, `921-922`); `MAX_REMAINDER_HOURS` 48 (`day_projection.py:88`); radiation calibration max age 7 days and min window 18 h (`const.py:682-685`); `AUTO_CALC_MAX_LEDGER_AGE_HOURS` 24 (`const.py:337`; `auto_calc.py:76-120`). None is an age limit on a sensor value.
- Never-consumed path (`watermark is None`): `select_window` returns every row as window (`weather_aggregate.py:155-156`), so aged boundary rows appear with their real stamps, and `_hour_multiplier` becomes the stamp span over 24 h (`310-318`). Reachability not verified (see G.5).
- Persistence: the buffer is written into the store document with every write (`store.py:1583-1610`, `1638-1649`; mappings serialised at `1629-1631`) and `data_last_entry` is a `MappingEntry` field (`store.py:364`), so a frozen boundary row and a carry-forward value survive restarts. Rows loaded from disk carry `retrieved` as an ISO string (`store.py:2062-2066`).

### B.5 Existing paths that remove stored per-field values (none is age-triggered)

- "Reset all weather data", `_async_clear_all_weatherdata` (`calculation.py:329-386`): empties every buffer (`351`), sets every `last_entry` value to None (`361-363`), moves every zone watermark to now (`366-379`), clears the deadband references (`343`) and the live-estimate carry (`348`).
- A change of a field's source or sensor entity, `async_update_mapping_config` (`__init__.py:1734-1823`) via `_mapping_source_changed` (`1698-1732`): empties that group's buffer and `last_entry` values (`1783-1790`), moves the group's zone watermarks (`1792-1805`), invalidates the live carry (`1774`). `tests/test_mapping_source_change.py:175`.
- The continuous-update row cap keeps only the oldest row, not per-field boundaries (`continuous_update.py:574-575`).

---

## C. Per-field table

Fields in a sensor group: Dewpoint, Evapotranspiration, Humidity, Precipitation, Current Precipitation, Pressure, Solar Radiation, Temperature, Windspeed (`const.py:692-702`; new groups, `frontend/src/views/mappings/view-mappings.ts:189-202`). Maximum/Minimum Temperature are derived (`weather_aggregate.py:516-518`), never mapped (`frontend/src/views/mappings/view-mappings.ts:193-195`, stripped at `store.py:1346-1350`, dropped from `by_sensor` at `weather_aggregate.py:204-205`). User-selectable aggregates for every field: average, first, last, maximum, median, minimum, riemannsum, sum, delta (`frontend/src/const.ts:118-128`); override read at `weather_aggregate.py:434-438`. Default `average` for all except Precipitation (`weather_aggregate.py:412-439`, `const.py:725-726`). Per-field config keys: `source`, `sensorentity`, `static_value`, `unit`, `pressure_type`, `aggregate` (`const.py:709-715`). The mapping endpoint takes `mappings` as an unvalidated `dict` (`websockets.py:240`) and strips the server-computed `data`, `data_last_updated`, `data_last_entry`, `data_last_calculation` (`websockets.py:242-267`). In the table below, bare line numbers are `weather_aggregate.py`, and `pyeto:` is `calcmodules/pyeto/__init__.py`.

| Field | Default aggregate | Used by | Event deadband (`continuous_update.py:93-102`) | Is "no rows for hours" normal? (code statement) |
|---|---|---|---|---|
| Temperature | average; also Tmax/Tmin over all samples incl. boundary (`516-518`) | daily via Tmin/Tmax (`pyeto:298-299`); hourly required (`70-75`); `_latest_temperature` | 0.2 degC | no code statement of hours-long silence; "minutes for temperature" (`continuous_update.py:326-330`) |
| Humidity | average | hourly required only; not in the daily form (`pyeto:114-120`) | 1.0 % | "hours for pressure or humidity" (`continuous_update.py:326-330`); slow-moving field (`calculation.py:409-414`, `weather_aggregate.py:931-935`, test `tests/test_weather_aggregate.py:355`) |
| Dewpoint | average | daily required; not in hourly rows | 0.2 degC | no statement |
| Pressure | average | daily required; hourly optional, derived from elevation when absent (`927-942`, `749-751`) | 0.5 hPa | "hours for pressure" (`continuous_update.py:326-330`). Relative -> absolute at ingest (`__init__.py:1370-1398`); poll writes standard-atmosphere pressure for a missing relative reading (`1391-1398`) |
| Windspeed | average | daily required; hourly required | 0.3 m/s | "a calm night's wind at 0" (`continuous_update.py:236-241`) |
| Solar Radiation | average | daily optional (PyETO estimates when absent, `pyeto:324-364`; clamp to clear sky `365-385`); hourly required plus ratio hold (`756-851`) | 0.5 MJ/day/m2 (about 6 W/m2, `99-101`) | yes: pinned at 0 at night, no night rows (`weather_aggregate.py:259-267`, `217-220`; `continuous_update.py:236-241`). Ingest clamp for rate units only (`__init__.py:1400-1447`) |
| Precipitation | riemannsum if source is weather service, else delta (`419-433`) | `weatherdata.get(Precipitation, 0)` (`calculation.py:1209`); water steps | none (`continuous_update.py:88-93`) | yes for a cumulative gauge: "unchanged for days" (`continuous_update.py:236-241`). Single sample: delta 0.0, sum/riemannsum verbatim (EXEC-3); `last_entry` guard only for integral aggregates (`weather_aggregate.py:380-393`) |
| Current Precipitation | average (no special case; frontend default average, `const.ts:116-117`) | not read by any calculation; listed in `websockets.py:636-638`, units `helpers.py:260` | none | no statement |
| Evapotranspiration | average | Passthrough module only (`calculation.py:1213-1223`) | none | no statement |

User-facing description of the fields: `docs/configuration-sensor-groups.md:25-35` lists as required Dewpoint, Humidity, Total precipitation, Pressure, Temperature, Wind speed; as not required Evapotranspiration, Solar Radiation and "Current precipitation (unused)" (`:27`, `:52`); expected aggregation Average for all, Delta for total precipitation.

Steady versus dead, as the code stands:

- Aggregation, prune and `last_entry` carry no per-field age or staleness flag. A steady and a dead sensor both leave no rows in event mode; in poll mode a dead sensor with a numeric stale state keeps producing rows (`__init__.py:1891-1923`).
- Only the state strings `unavailable`/`unknown` and non-numeric states are filtered, at ingestion, leaving no trace except the missing field (section D).
- `State.last_reported` is read only for flow sensors: `flow_metering.py:155-196`, `irrigation.py:1179-1210`, `distributor.py:691-736`, `self_closing.py:391-397`. `last_changed`: `run_watch.py:751`, `self_closing.py:647`.
- `sensor_debounce` (`const.py:129-130`, default 5000 ms) only delays follow-up bookkeeping, the reading is appended at once (`continuous_update.py:22-27`, `339-347`, `479-508`).
- Weather-service rows carry the API's measurement time as `observed` (`const.py:754`; written by `OWMClient.py:148`, `OpenMeteoClient.py:180`, `MetOfficeClient.py:454`, `PirateWeatherClient.py:432`). The aggregation drops it (`weather_aggregate.py:206`); only the panel table reads it (`websockets.py:610`, `620`). Sensor rows carry no such field.
- Gap precedent in another domain: `FlowMeter` refuses to bridge a rate gap wider than `max_gap_s` ("sensor 'unavailable'", `flow_metering.py:125-129`, `206-218`).

---

## D. Sensor-unavailable handling

### D.1 At write time

- Poll: `build_sensor_values_for_mapping` (`__init__.py:1871-1930`). Missing entity: skipped silently (`1892`). `float(state.state)` (`1894`) raises for `unavailable`/`unknown`/text; caught, debug line "No / unknown value for sensor" (`1924-1928`); the field is simply absent from the returned dict.
- Event: `unavailable`/`unknown`/`None` ignored with a debug line (`continuous_update.py:359-365`), non-numeric ignored (`366-374`), `new_state is None` ignored (`357-358`). The baseline seed skips the same (`264-269`). `tests/test_continuous_update.py:565`, `1103`.
- Recovery to a value within the deadband writes no row (`continuous_update.py:391-392`).
- Appended rows are not filtered for emptiness (`__init__.py:1499-1504`, `1625-1629`); see B.4.

### D.2 At calculation time

- No read of a mapped sensor's HA state in `calculation.py`, `weather_aggregate.py` or `live_estimate.py`. Across `calculation.py`, `weather_aggregate.py`, `live_estimate.py`, `continuous_update.py` and `__init__.py`, `hass.states.get` appears only at `__init__.py:1891` (poll), `continuous_update.py:263` (baseline seed) and `live_estimate.py:386`, `433` (forecast weather entity). The event handler uses the event's `new_state` (`continuous_update.py:356`).
- The calculation sees the buffer and `last_entry` only. Outcomes by case are in B.3. Missing PyETO inputs log a WARNING per calculation and book zero ET (`calcmodules/pyeto/__init__.py:438-463`); the zone is still marked consumed (`calculation.py:619-625`).

### D.3 Fallback to the weather service per field

- None for a field mapped to a sensor or a static value. Commit `78f9ce2c` (2026-09-20, #149, an ancestor of `e9c79ec4`) added `strip_foreign_source_values` (`calculation.py:255-293`). It pops the service copy of every sensor- or static-mapped field before sensor values are laid on (`__init__.py:1484`, `1610`, only when the group has sensor or static fields). Tests: `tests/test_source_leak.py:45-87`, `111`.
- Fields with no source (legacy bare string, `calculation.py:284-287`) keep the service value (`tests/test_source_leak.py:74`, `79`). The event path never merges a service row.
- Other substitutions: standard-atmosphere pressure on the poll for a relative pressure with no reading (`__init__.py:1391-1398`); PyETO estimates solar radiation when absent or when a behaviour other than "do not estimate" is set (`calcmodules/pyeto/__init__.py:324-364`).
- Separate paths with an explicit fail-open rule: soil-moisture sensor "a dead sensor must never silently stop irrigation" (`irrigation.py:695-696`, `709-735`).
- No test feeds `unavailable`/`unknown` into `build_sensor_values_for_mapping` (grep of `tests/`; `tests/test_source_leak.py:111` simulates the effect with an empty sensor dict).

---

## E. Repair and notification infrastructure

### E.1 Issue registry

Only `repairs.py` uses `homeassistant.helpers.issue_registry` (imported inside the function, `repairs.py:77`; reason `59-71`). Single caller: `async_check_issues` from setup, `__init__.py:324-327`, "re-evaluated on every setup". No runtime or periodic caller. Fix flows: `async_create_fix_flow` (`repairs.py:392-400`).

| Issue id (`repairs.py:49-56`) | create | delete | fixable | translation key |
|---|---|---|---|---|
| `leftover_legacy_directory` | `99-110` | `83`, `98`, `116` | no | same as id |
| `leftover_legacy_directory_removable` | `99-110` | `84`, `98`, `112` | yes | same as id |
| `foreign_legacy_install` | `117-126` | `85`, `95` | no | same as id |
| `renamed_entity_ids` | `134-146` | `148` | yes | same as id |
| `legacy_dashboard_cards` | `152-161` | `163` | yes | same as id |

All WARNING severity, `learn_more_url=const.MIGRATION_GUIDE_URL`, placeholders `path`/`count`. HA rule noted in the code: an issue carries a `description` or a `fix_flow`, never both (`repairs.py:50-52`; `tests/test_i18n_completeness.py:249-261`). Tests touching repairs: `tests/test_legacy_cleanup.py`, `tests/test_lovelace_cards.py`, `tests/test_rename_safety_nets.py`.

### E.2 Where the `issues` translations live

`custom_components/irrigation_plus/translations/{de,en,es,fr,it,nl,no,sk}.json`, `"issues": {` at line 455 in each; the same five keys in all eight (`translations/en.json:456`, `460`, `464`, `479`, `490`). `SUPPORTED_LANGUAGES` = de, en, es, fr, it, nl, no, sk (`const.py:29`). Completeness is enforced by `tests/test_i18n_completeness.py`.

### E.3 Persistent notifications

| Use | Where | Id | Text keys |
|---|---|---|---|
| Flow calibration advisory | `irrigation.py:1376-1384` create, `1387-1391` dismiss | `irrigation_plus_flow_cal_<zone_id>` (`1318`) | `flow_calibration.title`, `.message_over`, `.message_under`, `.open_settings` (`irrigation.py:1357-1371`) in `frontend/localize/languages/*.json` (`frontend/localize/languages/en.json:2-7`) |
| Distributor halt / refusal | `distributor.py:206-216` (`_dist_notify`, `179-231`) | `irrigation_plus_distributor_<id>` | `panels.distributors.notify.halted`, `.reason.<reason>`, `.inlet_open` (`distributor.py:253-261`, `1309-1310`; `frontend/localize/languages/en.json:886-894`) |

The backend text lookup is `localize()` (`localize.py:15-66`): panel language file, fallback English, else the key; the same 8 languages (`const.py:28-29`).

### E.4 Existing surfaces that could show a stale sensor today

- Problem sensors: `SmartIrrigationZoneProblemSensor` (`binary_sensor.py:321-370`, created `70`) and `SmartIrrigationGlobalProblemSensor` (`439-500`, created `137`). Fed by the in-memory run-fault map (`irrigation.py:589-645`); reasons are run faults (`const.py:1145`, `1202-1228`), none about sensors. Bus event `irrigation_plus_zone_problem` (`const.py:1080`, `irrigation.py:605-619`; `docs/usage-events.md:20`).
- Outlook: `zone_faults`, `zone_skips`, `zone_estimates` (`skip_conditions.py:134-152`).
- Zone diagnostic sensors `last_calculated`, `last_weather_update`, `weather_data_points`, `drainage`, default-disabled (`sensor.py:1068-1090`).
- Live deficit sensor attributes `method`, `balance_form`, `forecast_tier`, `radiation_tier`, `unavailable_reason` (`sensor.py:714-819`; reasons `live_estimate.py:126-133`). A carried-forward field raises no reason; a field absent from window and carry-forward ends in `no_evapotranspiration_source` only if no other source applies (`live_estimate.py:1455`, `1477`). WARNING once per zone and reason when `live_estimate_enabled` (`1695-1703`).
- Raw rows with stamps: panel "Weather data" (`websockets.py:561-659`, `view-weather-data.ts`).
- `diagnostics.py:77-83` dumps mappings via `async_get_mappings` (buffer-free, `store.py:1884-1889`; includes `data_last_entry`).
- Logs: a hourly-repeated WARNING when the solar ingest clamp fires, written so "a sensor that needs clamping" stays visible (`__init__.py:1413-1446`); PyETO missing-field WARNINGs (above).
- Docs: nothing in `docs/` describes carried-forward weather values or unavailable weather sensors (grep over all `docs/*.md`). The only unavailable-sensor text is the soil-moisture fail-open rule (`docs/configuration-my-zones.md:229-230`).

---

## F. Tests (`tests/`)

`_prune_mapping_buffer`:
- `test_prune_delta_baseline.py`: `test_gauge_rise_straddling_a_prune_is_counted` (89, real store, per-field boundary), `test_delta_baseline_survives_a_later_row_of_another_field` (117), `test_substeps_agree_with_the_aggregate_across_the_baseline` (136), `test_poll_style_full_rows_are_unchanged` (156).
- `test_per_zone_consumption.py::test_prune_keeps_oldest_watermark_but_caps_at_retention` (129; asserts only `len(remaining) < 4`; the disabled zone sits 30 days back).
- `test_continuous_update.py::TestFlush` `test_flush_publishes_zone_bookkeeping_and_prunes_every_nth` (935, prune mocked), `test_row_cap_keeps_the_boundary_row` (963), `test_row_cap_leaves_a_buffer_under_the_cap_alone` (981).
- `test_store_buffers.py::TestGetMinEnabledWatermark` (516-575, mirrors the disabled-zone rule); `test_run_in_flight.py:397` and `test_coordinator_mixins.py:40` only mock or name it.
- In the buffer-related test files no scenario has a boundary row older than one day. Largest offsets: `days=1` (`test_weather_aggregate.py:259`), a window length of `days=8` (`test_summed_hourly_eto.py:225`) and a 30-day watermark of a disabled zone (`test_per_zone_consumption.py:135`); no `hours=` offset reaches 100 (grep of these files).

`aggregate_window`, boundary, hold (`test_weather_aggregate.py`):
- `TestSelectWindow::test_boundary_is_last_reading_at_or_before_watermark` (171), `TestAggregates::test_average_includes_boundary` (194), `test_average_weights_by_dwell_time_not_sample_count` (205), `test_delta_accumulates_increments_from_boundary` (223), `test_empty_returns_none` (256; a one-day-old boundary-only window still aggregates, 259-262).
- `TestContinuousUpdateRows::test_average_of_a_field_constant_for_part_of_the_window` (299, solar night), `test_riemannsum_uses_per_key_stamps_on_a_sparse_buffer` (329).
- `TestSelectWindowAcceptsBothTimestampForms` (35), `TestTheEntryPointsSurviveAnAwareNow` (107) for the clock work.
- Others: `test_aggregate_time_weighting_is_opt_in.py`, `test_cumulative_delta.py:55`, `181`, `test_water_balance_substeps.py`, `test_live_estimate.py`.

`last_entry` backfill and carry-forward:
- `test_weather_aggregate.py`: `test_last_entry_backfills_sensor_absent_from_window` (355), `..._does_not_override_sensor_present_in_window` (369), `..._none_values_are_ignored` (382), `..._never_backfills_an_integrating_aggregate` (396), `..._still_backfills_a_delta_rain_gauge` (419), `test_weather_service_precip_is_unaffected_by_the_guard` (440).
- `test_summed_hourly_eto.py`: `test_an_hour_with_no_readings_carries_the_last_value_forward` (160), `test_a_missing_required_field_falls_back` (189), `test_a_field_only_in_the_carry_forward_is_still_usable` (203), `test_an_absurdly_long_window_falls_back` (221).
- `test_live_estimate_from_buffer.py`: `test_a_slow_field_reaches_the_estimate_through_the_carry_forward` (351), `test_a_field_in_neither_the_window_nor_the_carry_forward_declines` (372).
- `test_store_buffers.py`: `test_carry_forward_refresh_schedules_no_write_either` (87), `test_carry_forward_rides_out_on_the_next_write` (108), `test_carry_forward_is_not_shared_between_sensor_groups` (123).
- `test_continuous_update.py`: `TestStateChanged::test_appends_sparse_row_and_updates_last_entry` (468), `TestClearWeatherData::test_clear_all_also_neutralises_carry_forwards` (990); `test_mapping_source_change.py::test_source_change_also_neutralises_the_carry_forward` (175).
- Solar hold: `test_solar_ratio_hold.py` (123, 212, 238, 256).

Unavailable / unknown and source leak:
- `test_continuous_update.py`: `test_non_numeric_states_are_ignored` (565, parametrised unknown/unavailable/None/"abc"), `test_unavailable_and_non_numeric_states_are_not_seeded` (1103).
- `test_source_leak.py`: `TestTheWeatherServicesCopyIsDropped` (45-87), `TestTheReadableSensorStillWins::test_an_unreadable_sensor_leaves_the_field_absent` (111).

Radiation calibration (PR 187): `test_live_estimate_measured_radiation.py::TestTheCommitRecordsTheCalibration` (518-684, incl. `test_a_stalled_watermark_is_not_recorded_as_one_window` 604), `TestTheTrailingCalibration` (687-845); `test_a_runaway_ratio_is_held_inside_its_bounds` (788) states "A dead sensor books almost no energy".

Writer clock frame: `test_weather_buffer_one_frame.py` (`TestEveryWriterStampsHAsClock` 349, `TestNoProcessClockOnTheBufferPaths` 491).

---

## G. Open questions not settled by the code

1. Do the deployed sensor integrations switch to `unavailable`/`unknown` when a device dies, or keep a numeric last state? That decides whether a dead sensor shows up as absence (poll) or as a stale numeric value (rewritten at each tick). Depends on the integration, not on this code.
2. Does the production HA version raise `state_reported` and bump `last_reported` the same way as the local HA 2024.12.5? The repo reads `last_reported` only for flow sensors.
3. Intent of per-field boundary retention beyond the 7-day cap: the docstring (`calculation.py:436-437`) and the loop (`467-481`) disagree. In this repository `git log -S` finds `BUFFER_RETENTION`, `merge_latest_per_field` and `last_entry` first in `552dc4ae` (2026-09-04, #120 rename), so earlier history is not available here.
4. Is it intended that `data_last_entry` is read when `continuousupdates` is off (`calculation.py:415`) though only the event path refreshes it? A value left from an earlier continuous period stays, unstamped, until a reset or a source change (`calculation.py:361-363`, `__init__.py:1783-1790`).
5. Never-consumed zones (`watermark is None`): aged boundary rows join the window with their real stamps and `_hour_multiplier` equals their span over 24 h (`weather_aggregate.py:310-318`). New zones are anchored at creation (`store.py:1727-1731`); legacy stores may still yield `None` (`store.py:1234-1240`). Reachability in practice not verified.
6. Whether a stamp-only poll row (all sensors unreadable) should advance zone `last_updated` and the data-point count (`__init__.py:1518-1522`, `1636-1648`). Reported as fact only.
7. The frontend was traced only for the mapping defaults, aggregate options and the weather-records table; other panel surfaces were not checked for staleness hints.
