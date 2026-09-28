# Data-flow inventory: the five persisted timestamp fields

Read-only inventory. Nothing in the repository was modified.

- Worktree: `D:\Entwicklung\HASI\issue22-work\wt`, branch `fix/weather-buffer-aware-writers`, HEAD `1876aa03`.
  `git status --short` = only the untracked `docs/superpowers/`, so every line number below is the file as it is on disk and as it is at HEAD.
- Scope: `custom_components/irrigation_plus/`, excluding `weathermodules/` and `tests/`. `frontend/src` was only glanced at for consumers (rows marked informational).
- Method: grep for the five constants, the literal key names, attr access (`.last_consumed_at` etc.) and dict-key access (`["last_calculated"]`); grep for every parser/coercion helper call; then each function was read and every `now` / `watermark` parameter was followed to its callers. Complete helper census in Appendix 1.
- HA reference for Section E: the test venv `D:\Entwicklung\HASI\HAsmartirrigation\.venv` = Home Assistant 2024.12.5 (`homeassistant/const.py:26-28`). The production HA version is NOT VERIFIED.
- Probes: small in-memory Python snippets (`python -B`, no repository file written, no test suite). Outputs are in Appendix 2 and are cited as P1..P4. A scripted spot-check of 191 cited `file:line` references against the source found 0 mismatches (the throwaway checker lives in the session scratchpad, outside the repository).
- Design context (terminology only, not evidence for any code claim): the untracked `docs/superpowers/specs/2026-09-28-weather-buffer-aware-writers-design.md`, cited below as "the design doc".
- Anything marked NOT VERIFIED could not be established from the code on disk.

Row counts: Section A = 32 rows (+2 frontend informational rows, +9 derived-compare rows); Section B = 16 origin rows (+5 funnel rows, +4 write-block rows); Section C = 24 bare-`now` rows (+5 `dt_util.now()`-compared rows, +3 offset-only rows, +2 adjacent rows).

## 0. Vocabulary and what each helper really does

Frames used below:

- "bare now" = a bare `datetime.now()`: naive, PROCESS time zone.
- "HA-local naive" = `dt_util.now().replace(tzinfo=None)`, or `coerce_stamp(x, STAMP_FROM_CLIENT)`, or `_parse_stored_as_ha_local(x)`.
- "raw stored value" = what a zone dict / buffer row holds: an ISO `str` after `async_load` (Section E), a naive `datetime` object after an in-process write, `None` if never set.

| helper | file:line | naive in | aware in | str in | notes |
|---|---|---|---|---|---|
| `helpers.parse_datetime` / `helpers.as_datetime` / `calculation._as_datetime` (alias `from .helpers import as_datetime as _as_datetime`, calculation.py:29) | helpers.py:960-984, 987-997 | unchanged | unchanged | `datetime.fromisoformat(val)` (helpers.py:982) | NO frame conversion at all. A malformed string raises ValueError (uncaught). A non-str/non-datetime logs WARNING and returns None (helpers.py:983-984). `as_datetime(None)` is None. |
| `helpers.coerce_stamp(value, provenance)` | helpers.py:1018-1059 | unchanged for BOTH provenances (:1055-1056) | STORE: `parsed.astimezone(_process_timezone()).replace(tzinfo=None)` (:1057-1058); CLIENT: `dt_util.as_local(parsed).replace(tzinfo=None)` (:1059) | via `as_datetime` inside `try ... except (ValueError, TypeError): return None` (:1049-1052) | unknown provenance raises ValueError (:1045-1046); None -> None; non-datetime -> None (:1053-1054). Output is always naive. |
| `weather_aggregate._parse` | weather_aggregate.py:102-122 | = `coerce_stamp(value, STAMP_FROM_STORE)` (:122) | | | |
| `live_estimate._parse_stored_as_ha_local` | live_estimate.py:192-227 | unchanged (:226, i.e. taken as HA-local) | `dt_util.as_local(value).replace(tzinfo=None)` (:225) | `fromisoformat`, ValueError -> None (:218-222) | other types -> None (:227) |
| `sensor._to_aware_datetime` | sensor.py:603-621 | `.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)` (:619-620), i.e. taken as HA's zone | unchanged (:621) | `fromisoformat`, ValueError -> None (:612-616) | non-datetime -> None (:617-618) |
| `sensor._format_timestamp` | sensor.py:306-326 | `.strftime("%Y-%m-%d %H:%M:%S")` | same, prints the digits of the value's own offset | `fromisoformat(...).strftime(...)` (:318), `except (ValueError, TypeError): return val` (:319-320) | no zone handling |
| `websockets._safe_parse_datetime` | websockets.py:63-80 | unchanged | `astimezone(datetime.UTC).replace(tzinfo=None)` (:67-68) | `dateutil isoparse`, aware -> naive UTC (:72-75) | anything else or failure -> `datetime.datetime.min` (:78-80) |

Try/except labels used in the Section A table:

- **TE-CALC**: nothing inside the reading function. Reached via `_async_calculate_all`: `try` calculation.py:452, `except Exception:  # noqa: BLE001` calculation.py:460 -> `_LOGGER.exception("Error calculating zone %s; skipping it and continuing with the remaining zones", ...)` (calculation.py:464-468, ERROR + traceback), then `continue`; the zone's watermark is not advanced. Reached via `async_update_zone_config` -> `self.async_calculate_zone(zone_id, forecastdata, run_start=run_start)` (`__init__.py:2109`, no try there): callers auto_calc.py:72-74 (none), services.py:97 (none), run_state.py:250 (`except Exception:` run_state.py:253 -> `_LOGGER.warning(..., exc_info=True)` run_state.py:254-260, zone stays deferred), websockets.py:384 (`except SmartIrrigationError` :385 only, so a TypeError propagates); scheduler.py:1827 / :1969 / :2351 -> `async_commit_pre_run_calculation` (auto_calc.py:46-74, none): whether the scheduler frames above catch it is NOT VERIFIED.
- **TE-LIVE1**: inside `_intraday_for_zone`'s `try` (live_estimate.py:1256) / `except Exception as e:  # noqa: BLE001 — estimate must never raise` (live_estimate.py:1546) -> `_LOGGER.debug("intraday estimate failed for a zone: %s", e, exc_info=True)` (:1555) and `result["unavailable_reason"] = REASON_FAILED` (:1556). Swallowed, DEBUG level.
- **TE-LIVE2**: inside `_carry_estimate_to`'s `try` (live_estimate.py:1730) / `except Exception as e:  # noqa: BLE001 — a projection must never raise` (:1849) -> `_LOGGER.debug("next run: could not carry a zone's estimate forward: %s", e)` (:1850). Swallowed, DEBUG, no traceback.
- **TE-ING**: no try around the stamp comparison in `_sensor_state_changed` (continuous_update.py:349-459; its only try, :365-373, guards `float(new_state.state)`) or in `_continuous_seed_baseline` (:230-295; its only try, :265-268, guards `float(state.state)`). The event path is dispatched by HA `helpers/event.py:354-360`: `except Exception:` -> `_LOGGER.exception("Error while dispatching event for %s to %s", ...)` (ERROR; verified in the .venv HA 2024.12.5 only). The reading is not appended.

## Section A. READ sites of the five fields (32 rows)

Columns: ID | file:line | function | field | how parsed | compared with / passed to (other operand and its origin) | try/except that would catch TypeError.

| ID | file:line | function | field | how parsed | compared with / passed to | try/except |
|---|---|---|---|---|---|---|
| A-01 | store.py:1157 | `SmartIrrigationStorage.async_load` | zones[].last_calculated | raw: `zone.get(ZONE_LAST_CALCULATED, None)` into `ZoneEntry.last_calculated` (store.py:253; `attr.ib` with no converter or validator) | not compared; value stays what JSON delivered (ISO str or None) | no (nothing compared) |
| A-02 | store.py:1161-1164 | `async_load` | zones[].last_consumed_at (and reads last_calculated as its default) | raw: `zone.get(ZONE_LAST_CONSUMED, zone.get(ZONE_LAST_CALCULATED, None))`. dict.get semantics: last_calculated is used only when the KEY is absent; a present key holding None stays None | not compared; this is where every watermark reader (A-07, A-09, A-11..A-14, A-20) gets its value | no |
| A-03 | store.py:1165 | `async_load` | zones[].last_updated | raw | not compared | no |
| A-04 | store.py:1289 | `async_load` | mappings[].data_last_updated | raw: `mapping.get(MAPPING_DATA_LAST_UPDATED, None)` | not compared | no |
| A-05 | store.py:1282-1284 | `async_load` | mappings[].data[].retrieved | untouched: `buffers[int(mapping[MAPPING_ID])] = _as_buffer(mapping.get(MAPPING_DATA))`; `_as_buffer` (store.py:865-879) returns the loaded list itself, rows keep RETRIEVED_AT as ISO str (confirmed by the comment at store.py:1980-1984) | not compared | no |
| A-06 | store.py:1652 | `async_create_zone` | zones[].last_consumed_at | raw attr read `new_zone.last_consumed_at is None` | only an `is None` test | no |
| A-07 | store.py:1921 | `get_enabled_zone_watermarks` | zones[].last_consumed_at | `as_datetime(zone.last_consumed_at)`: attr read on the frozen `ZoneEntry` from `self.zones.values()` (not via asdict); parse only, no frame conversion | appended to `watermarks`; None sets `any_unconsumed` (:1922-1925). Consumers: (a) store.py:1939 `min(watermarks)` in `get_min_enabled_watermark`, other operands = the other enabled zones' watermarks on the same mapping (naive vs aware mix raises); (b) calculation.py:388 -> :392 `max(cap_cutoff, min(watermarks))`, `cap_cutoff` = `now - BUFFER_RETENTION` (:387), `now` from the `_prune_mapping_buffer` parameter (callers calculation.py:474, :555, continuous_update.py:544, each a bare now: :432, :432 or :498, :521) or the bare default :379; (c) continuous_update.py:277-279 (`watermark_cache`) and :441 -> `merge_or_append_mapping_reading(min_watermark=...)` -> store.py:1990 `newest_at > min_watermark` | no try in store.py:1889-1939. For (b): none in `_prune_mapping_buffer`, its callers are calculation.py:474 (OUTSIDE the try at :452-460), :555 (only with prune=True; calc-all passes prune=False, :457) and continuous_update.py:544 (none). For (c): TE-ING |
| A-08 | store.py:1985 | `merge_or_append_mapping_reading` | mappings[].data[].retrieved | `as_datetime(newest.get(RETRIEVED_AT))`; parse only; None -> no merge, plain append (:1997-1998) | `newest_at >= coalesce_before` (:1989): `coalesce_before` = `timestamp - CONTINUOUS_COALESCE_WINDOW`, `timestamp` = bare now at continuous_update.py:252-253 (seed) or :378 / :440 (event); `newest_at > min_watermark` (:1990): see A-07 (c) | none in store.py:1941-1999. Callers: continuous_update.py:280 (`_continuous_seed_baseline`, no try around the call; invoked at :197 from `async_setup_continuous_updates`, whose callers `__init__.py:787` / `:810` have no try) and :437 (`_sensor_state_changed`, TE-ING) |
| A-09 | calculation.py:331 | `_aggregate_for_zone` | zones[].last_consumed_at | `_as_datetime` (parse only) | -> `select_window(readings, watermark)` :332 and `aggregate_window(readings, watermark, ..., now=now)` :333-357. Other operands: row stamps (`_parse` = coerce STORE), `now` (coerced STORE at weather_aggregate.py:368; origin bare now calculation.py:432 -> :456, or :498). Inside `aggregate_window` the SAME watermark is used un-coerced at weather_aggregate.py:382, :414 (`now - watermark`), :415 (`end <= start`); see D.5 | none in `_aggregate_for_zone` (:317-358) or `async_calculate_zone`; TE-CALC |
| A-10 | calculation.py:398 | `_prune_mapping_buffer` | mappings[].data[].retrieved | `_as_datetime(r.get(RETRIEVED_AT)) if isinstance(r, dict) else None` (parse only) | `rt is None or rt > cutoff` (:400) with `cutoff` = `cap_cutoff` (`now - 7 d`, :387) or `max(cap_cutoff, min(watermarks))` (:392), see A-07; `merge_latest_per_field(boundaries, rt, r, keep_row=True)` (:403) -> `timestamp >= prev[0]` (weather_aggregate.py:140) compares row stamps with each other; `sorted(boundaries.values(), key=lambda p: p[0])` (:407) likewise | none in calculation.py:360-419. Callers: :474 (outside the try :452-460), :555 (`async_calculate_zone`, prune=True path), continuous_update.py:544 (none, runs in a task); so NOT caught by :460 |
| A-11 | calculation.py:808 | `_hourly_et_for_zone` | zones[].last_consumed_at | `_as_datetime` | -> `hourly_eto_priced(readings, <wm>, mappings_config, now=now, ...)` (:806-816) -> `build_hourly_rows` (et_estimate.py:171) -> `_effective_series` (weather_aggregate.py:941) -> un-coerced at :729 / :731. `now` from `calculate_module(now=)` :960 <- :534 <- `async_calculate_zone` (bare now :432 / :498), default bare :934 | none in :721-831; TE-CALC |
| A-12 | calculation.py:865 | `_substeps_for_zone` | zones[].last_consumed_at | `_as_datetime` | -> `build_substeps(readings, <wm>, mappings_config, now=now, hourly_et=, applied=)` :863-870 -> `_effective_series` weather_aggregate.py:1136. `now` from :1060. `applied` = `pending_bucket_events(zone)` (:1058), HA-local naive | none; TE-CALC |
| A-13 | calculation.py:975 | `calculate_module` | zones[].last_consumed_at | `_as_datetime` | -> `weather_day(<wm>, now)` :974-976 (weather_aggregate.py:237-260: returns `(window_start + 12 h).date()`; no comparison, no coercion) | no comparison; downstream TE-CALC |
| A-14 | calculation.py:1116 | `calculate_module` (lumped arm) | zones[].last_consumed_at | `_as_datetime`; None -> `now - timedelta(hours=elapsed_hours)` (:1117-1118) | `(stamp - window_start).total_seconds()` (:1123) for each `(stamp, mm)` of `applied`; `stamp` = HA-local naive (calculation.py:64-65 `dt_util.as_local(...).replace(tzinfo=None)`), `window_start` = raw stored frame. Raises TypeError if the watermark is aware; measures across two frames if process zone differs from HA's | none; TE-CALC |
| A-15 | weather_aggregate.py:176 | `select_window` | mappings[].data[].retrieved | coerce_stamp STORE via `_parse` (:122) | `rdt <= watermark` (:177; watermark = coerce STORE of the parameter, :167); `rdt >= boundary_dt` (:178); `merge_latest_per_field(fields, rdt, r, keep_row=False)` (:180) | none needed: both sides come out of coerce_stamp, no naive/aware mix can arise here |
| A-16 | weather_aggregate.py:206 | `_group_by_sensor` | mappings[].data[].retrieved | coerce_stamp STORE via `_parse` | `(stamp, val)` tuples; stamps later subtracted/compared in `_aggregate` (:586), `_time_weighted_mean` (:283-307), `_clamped_samples` (:623, against start/end from `_window_bounds`), `_precip_increments` (:691), `_hold_integral_table` (:639-650), `_ratio_hold_solar` (:804-807) | none |
| A-17 | weather_aggregate.py:229 | `_window_bounds` | mappings[].data[].retrieved | coerce_stamp STORE via `_parse` | `start = watermark` (:230, parameter used as received) or `min(stamps)`; `end = max([now, *stamps])` (:231, `now` used as received); `end <= start` (:232) | none in function. P1: aware watermark -> TypeError :232; aware now -> TypeError :231 |
| A-18 | weather_aggregate.py:321 | `_hour_multiplier` | mappings[].data[].retrieved | coerce_stamp STORE via `_parse`; only when watermark is None | `max(times) - min(times)` (:324). With a watermark the row stamps are not read and `now - watermark` (:319) uses both as received | none. P1/P2: aware or ISO-string watermark -> TypeError :319 |
| A-19 | live_estimate.py:246 | `_window_anchor` | zones[].last_calculated | `_parse_stored_as_ha_local` | None -> return None (:247-248); the anchor's consumers are AC-01..AC-09 and D.5 (M3-M5), D.6 (M7), D.7 (M9) | none in `_window_anchor`; callers :1288 (TE-LIVE1), :1741 (TE-LIVE2) |
| A-20 | live_estimate.py:249-250 | `_window_anchor` | zones[].last_consumed_at | `_parse_stored_as_ha_local` | `max(last_calc, last_consumed) if last_consumed else last_calc` (:250); both operands from the same parser, both naive | as A-19 |
| A-21 | auto_calc.py:135 | `_any_zone_ledger_older_than` | zones[].last_calculated | `_parse_stored_as_ha_local` (import auto_calc.py:24) | `last is None or last < cutoff` (:136); `cutoff` = `dt_util.now().replace(tzinfo=None) - timedelta(hours=const.AUTO_CALC_MAX_LEDGER_AGE_HOURS)` (:96-98), passed at :112 | none; caller `async_guard_ledger_staleness` (:76-120) has none and is scheduled as an unawaited task (`__init__.py:2162`); what HA does with such a task exception is NOT VERIFIED |
| A-22 | sensor.py:68 (+:282, :292) | `async_add_sensor_entity` -> `SmartIrrigationZoneEntity.__init__` | zones[].last_updated | raw `config[const.ZONE_LAST_UPDATED]` (zone dict from `store.async_get_zones()`, `__init__.py:896` -> dispatch :900; or `entry` from `async_create_zone`, `__init__.py:2150-2152`), then `_format_timestamp` | none | `_format_timestamp` swallows `(ValueError, TypeError)` (sensor.py:319-320, 324-325) but there is no comparison to protect |
| A-23 | sensor.py:69 (+:283, :293) | same | zones[].last_calculated | as A-22 | none | as A-22 |
| A-24 | sensor.py:343 (+:355) | `async_update_sensor_entity` | zones[].last_updated | raw `zone["last_updated"]` from `store.get_zone(id)` (attr.asdict copy, sensor.py:336), then `_format_timestamp` (no zone conversion, prints the digits of the value's own offset) | none | as A-22 |
| A-25 | sensor.py:344 (+:356-358) | same | zones[].last_calculated | as A-24 | none | as A-22 |
| A-26 | sensor.py:427-438, output :448-449 | `extra_state_attributes` | zones[].last_updated, last_calculated | lazy re-format of the cached formatted strings | none | as A-22 |
| A-27 | sensor.py:1103-1105 (spec tuples :1062-1063) | `SmartIrrigationZoneDiagnosticSensor._update_from_zone` | zones[].last_calculated, last_updated | sensor helper `_to_aware_datetime` (sensor.py:603-621) | becomes `native_value` (:1122) of a `SensorDeviceClass.TIMESTAMP` sensor (:1112); not compared inside the integration | `except ValueError` (sensor.py:615-616) -> None, silent; TypeError not caught; nothing is compared |
| A-28 | websockets.py:489-493 | `websocket_get_zones` | zones[].last_calculated, last_consumed_at, last_updated | none: raw pass-through of `store.async_get_zones()`; HA JSON-encodes the datetimes | none | no |
| A-29 | websockets.py:521-526 | `websocket_get_mappings` | mappings[].data_last_updated | none: raw (buffer-free `async_get_mappings`, store.py:1802-1807) | none | no |
| A-30 | websockets.py:566-570 | `websocket_get_weather_records` | mappings[].data[].retrieved | other: `_safe_parse_datetime` (websockets.py:63-80) | sort key only; all keys are naive so TypeError is impossible, but the keys mix naive-UTC (from aware rows) with naive-as-is (legacy rows) | `try` :542 / `except Exception as e:` :622 -> `_LOGGER.error(...)` :623-625 and `records = []` :626 (ERROR, returns an empty list) |
| A-31 | websockets.py:577-589 | same | mappings[].data[].retrieved | other: `_to_iso` (:580-585): datetime -> `.isoformat()`, str as is | display only (`retrieval_time` :607) | same try as A-30 |
| A-32 | diagnostics.py:79, :81 | `async_get_config_entry_diagnostics` | mappings[].data_last_updated; zones[] three stamps | none: raw dump of `async_get_mappings()` / `async_get_zones()` | none | no |

Frontend rows (informational, from reading the TypeScript only, not executed):

| ID | file:line | consumer | field | how parsed | note |
|---|---|---|---|---|---|
| A-F1 | frontend/src/types.ts:333-334; views/zones/view-zones.ts:879, :1103, :1129-1130 | zone status and "last checked" text | last_calculated (last_updated is only declared) | `formatDateTime` -> `new Date(value)` (common/datetime.ts:12-14, 30-36) | an ISO string without offset is read as BROWSER-local, one with an offset is an absolute instant; `last_consumed_at` is not rendered |
| A-F2 | frontend/src/views/weather/view-weather-data.ts:273-279, :382 | weather-record table | data[].retrieved as `retrieval_time` | `isValidDate` + `formatMonthDayTime` -> `new Date` | try/catch -> "-" (:274-278) |

### Derived-compare rows (9): where the parsed anchor is compared once it leaves `_window_anchor`

`anchor` is HA-local naive (A-19, A-20). Other operand = `now_local` unless stated; `now_local` is `inputs.get("now") or dt_util.now().replace(tzinfo=None)` (live_estimate.py:1293 / :1731) and `inputs["now"]` is `coerce_stamp(dt_util.now(), STAMP_FROM_CLIENT)` built at live_estimate.py:275 (`now = dt_util.now()` at :264); both HA-local naive. All inside TE-LIVE1 or TE-LIVE2 unless stated.

| ID | file:line | function | what is compared |
|---|---|---|---|
| AC-01 | live_estimate.py:731-734 | `_buffer_hourly_et` | `watermark, base = anchor, {}`; `carry.anchor == anchor and anchor <= carry.boundary` (:732); `carry.boundary <= now` (:733) then `watermark = carry.boundary`. `carry.boundary` = `current_hour` (:762, :771-772), built from `now` |
| AC-02 | live_estimate.py:768-770 | `_buffer_hourly_et` | `hour < current_hour` (:768); `current_hour > watermark` (:770) |
| AC-03 | live_estimate.py:839, :843, :847, :851 | `_commit_forecast` | `max(anchor + timedelta(hours=24), now)` (:839); `commit_at.replace(tzinfo=site_tz)` (:843, HA's zone) compared with forecast `FORECAST_DAY_START` values (:847); `(commit_at.date() - now.date()).days` (:851) |
| AC-04 | live_estimate.py:982 | `_composed_day_et` | `window_end=anchor + timedelta(hours=24)` -> `_projected_extremes` (:910 `forecast_remainder`, :915 `diurnal_remainder`) -> day_projection.py:192-196 (`remainder_hours`), :243, :249, :254 (`forecast_remainder`), :375 |
| AC-05 | live_estimate.py:992 | `_composed_day_et` | `weather_day(anchor, now)` (date only) |
| AC-06 | live_estimate.py:1200 | `_rows_since` | `rdt + timedelta(hours=1) > last_calc_local` with `rdt = fromisoformat(r["time"])` of the weather client's hourly rows (`inputs["rows"]`, from `client.get_hourly_data`, :288-290); the frame of those row times is NOT VERIFIED (weathermodules ignored) |
| AC-07 | live_estimate.py:1412-1421 | `_intraday_for_zone` | `(local.date() - anchor.date()).days`, `anchor.hour` |
| AC-08 | live_estimate.py:1439 | `_intraday_for_zone` | `elapsed_hours = max(0.0, (now_local - anchor).total_seconds() / 3600.0)` |
| AC-09 | live_estimate.py:1510-1512 | `_intraday_for_zone` | `(stamp - anchor)` for `(stamp, mm)` in `pending_bucket_events(zone)` (stamp HA-local naive, calculation.py:64-65); the daily twin is A-14 with a raw window start |

Not read: `zones[].last_updated` is not read by live_estimate.py, auto_calc.py, calculation.py or weather_aggregate.py (its only mention in live_estimate.py:193 is a docstring). `mappings[].data_last_updated` is read by nothing that parses it (A-04, A-29, A-32 only).

## Section B. WRITE sites of the five fields (16 origin rows)

Columns: file:line | function | field | value written | origin of that value | same variable also used for non-persisting computation (file:line).

| ID | file:line | function | field | value written | origin | non-persisting uses of the same variable |
|---|---|---|---|---|---|---|
| B-01 | calculation.py:300 | `_async_clear_all_weatherdata` (:258-315) | zones[].last_consumed_at | `now`, through `store.async_update_zone(zone_id, {...})` (:297-308) | bare `datetime.now()` at calculation.py:267. The method has no `now` parameter (`*args`); callers services.py:245 (`handle_clear_weatherdata`) and, through it, `__init__.py:2131` | none (only :267 and :300) |
| B-02 | calculation.py:547 | `async_calculate_zone` (:480-561) | zones[].last_calculated | `calc_data[ZONE_LAST_CALCULATED] = now`, stored by `async_update_zone` :553 | parameter `now`: (a) `_async_calculate_all` passes `now=now` (:456) where `now = datetime.now()` at :432, one clock read shared by every zone; (b) default `if now is None: now = datetime.now()` at :498 when called without it: `__init__.py:2109` (zone POST with calculate, auto_calc.py:72, services.py:97, run_state.py:250). `async_calculate_zone` has exactly two callers (calculation.py:453, `__init__.py:2109`) and no caller of `_async_calculate_all` supplies a `now` (auto_calc.py:69, :120, button.py:293, services.py:83, `__init__.py:2114`; the timer registration `__init__.py:1301` passes HA's tick time, which `*args` swallows) | :526 `_aggregate_for_zone(zone, now=now)` -> :333-357 `aggregate_window(now=)` -> weather_aggregate.py:368 (coerce STORE), :414 (`now - watermark`), :415 (window bounds); :534 `calculate_module(..., now=now)` -> :960 (`_hourly_et_for_zone` -> :810 `hourly_eto_priced(now=)`), :975 (`weather_day`), :979 (`now.date() + timedelta(days=1)`), :1060 (`_substeps_for_zone` -> :867), :1118 (`now - timedelta(hours=elapsed_hours)`); :545 `_record_window_amplitude(now=now)` -> :597 (`now.date().isoformat()`); :555 `_prune_mapping_buffer(..., now=now)` -> :387 (`now - BUFFER_RETENTION`). In the calc-all path the same `now` is also used at :474 after the loop |
| B-03 | calculation.py:548 | `async_calculate_zone` | zones[].last_updated | `calc_data[ZONE_LAST_UPDATED] = now` | same object as B-02 | same list as B-02 |
| B-04 | calculation.py:550 | `async_calculate_zone` | zones[].last_consumed_at | `calc_data[ZONE_LAST_CONSUMED] = now` | same object as B-02 | same list as B-02 |
| B-05 | __init__.py:1506 | `_async_update_zone` (:1455-1544) | mappings[].data[].retrieved | `weatherdata[const.RETRIEVED_AT] = dt_datetime.now()`; the dict is appended by reference to the buffer (`append_mapping_reading` :1510 -> store.py:1884) | inline bare `dt_datetime.now()` (alias `from datetime import datetime as dt_datetime`, `__init__.py:11`); its own clock read, separate from :1516 | the dict is logged at :1511-1515; earlier it went through `_apply_pressure_type` (:1502) and `merge_weatherdata_and_sensor_values` (calculation.py:239-256, mutates in place); whether `client.get_data` returns a fresh dict each call is NOT VERIFIED (weathermodules) |
| B-06 | __init__.py:1518 | `_async_update_zone` | mappings[].data_last_updated | `updated_at`, via `store.async_update_mapping` (:1517-1519) | bare `dt_datetime.now()` at :1516 | none (`updated_at` appears only at :1516, :1518, :1525) |
| B-07 | __init__.py:1525 | `_async_update_zone` | zones[].last_updated | `updated_at` in `changes_to_zone` (:1524-1527), `async_update_zone` :1528 | same object as B-06 | none |
| B-08 | __init__.py:1632 | `_async_update_all` (:1546-1669) | mappings[].data[].retrieved | `weatherdata[const.RETRIEVED_AT] = dt_datetime.now()`, appended by reference :1635 | inline bare now; own clock read | logged :1636-1640 |
| B-09 | __init__.py:1644 | `_async_update_all` | zones[].last_updated | `const.ZONE_LAST_UPDATED: dt_datetime.now()` inside `changes_to_zone` (:1643-1646); the same dict, hence the same datetime object, is written to every zone of the mapping (:1647-1649) | inline bare now; a second separate read after B-08's :1632. This path never writes `data_last_updated` (compare B-06 and B-15) | none |
| B-10 | __init__.py:1804 | `async_update_mapping_config` (:1740-1829) | zones[].last_consumed_at | `now`, once per zone of the mapping (:1800-1811) | bare `dt_datetime.now()` at :1799, taken after `async_update_mapping` (:1797) has wiped the buffer (:1792-1796) | none (:1799, :1804 only) |
| B-11 | __init__.py:2023 | `_book_asserted_bucket` (:1967-2026) | zones[].last_consumed_at | `const.ZONE_LAST_CONSUMED: dt_datetime.now()` in the payload of `async_update_zone` :2014-2026 | inline bare now; reached from `async_update_zone_config` generic branch (:2135-2136, incl. `_async_set_all_buckets` :2316-2327 and irrigation.py:753), and services.py:229 | none (also writes `ZONE_PENDING_BUCKET_EVENTS: []`) |
| B-12 | store.py:1653 | `async_create_zone` | zones[].last_consumed_at | `attr.evolve(new_zone, last_consumed_at=datetime.datetime.now())` when it is None (:1652) | inline bare now (`import datetime`, store.py:3); reached from `__init__.py:2150` | none |
| B-13 | continuous_update.py:282 | `_continuous_seed_baseline` (:230-295) | mappings[].data[].retrieved | `{key: value, const.RETRIEVED_AT: timestamp}` into `merge_or_append_mapping_reading` :280-285 | bare now `timestamp = datetime.now()` at :252, one read reused for every field and mapping of the seed. When a merge happens the row keeps its FIRST RETRIEVED_AT (store.py:1993-1994 copies fields only), so `timestamp` is stored only for a fresh row | :253 `coalesce_before = timestamp - CONTINUOUS_COALESCE_WINDOW`, passed :283 -> compared at store.py:1989 |
| B-14 | continuous_update.py:439 | `_sensor_state_changed` | mappings[].data[].retrieved | `{key: value, const.RETRIEVED_AT: timestamp}` :437-442 | bare now `timestamp = datetime.now()` at :378 (the comment :375-377 states the naive-local convention) | :440 `coalesce_before=timestamp - CONTINUOUS_COALESCE_WINDOW`; :449-455 debug log |
| B-15 | continuous_update.py:523 | `_async_continuous_update_for_mapping` (:508-554) | mappings[].data_last_updated | `now`, via `store.async_update_mapping` :522-524 | bare now `now = datetime.now()` at :521 | :532 (persisted, B-16); :544 `_prune_mapping_buffer(mapping_id, now=now)` -> calculation.py:387 `now - BUFFER_RETENTION` compared with stored stamps (A-10) |
| B-16 | continuous_update.py:532 | `_async_continuous_update_for_mapping` | zones[].last_updated | `const.ZONE_LAST_UPDATED: now` in `changes_to_zone` :531-534, per zone :535-537 | same object as B-15 | same as B-15 |

Funnels (values pass through unchanged, no conversion; not origins):

| ID | file:line | what |
|---|---|---|
| B-F1 | store.py:1700-1702 | `async_update_zone`: filters keys to `attr.fields_dict`, then `attr.evolve(old, **filtered_changes)`; keeps whatever object it is handed (datetime or str) |
| B-F2 | store.py:2110 | `async_update_mapping`: `attr.evolve(old, **changes)` |
| B-F3 | store.py:1884, :1997-1998 | `append_mapping_reading` / `merge_or_append_mapping_reading` put the reading dict by reference into `self.buffers[mapping_id]` |
| B-F4 | store.py:2014, :2064, :2091 | `set_mapping_buffer` / `async_create_mapping` / `async_update_mapping(MAPPING_DATA)` replace the buffer with rows that keep their stamps. Callers: calculation.py:280 (`[]`), :419 (`kept`, original rows), continuous_update.py:583 (subset), `__init__.py:1794` (`[]`), `__init__.py:1826` (view-sanitized data) |
| B-F5 | store.py:1549-1557, :1569 | `_data_to_save` (`attr.asdict`) and `_data_to_save_full` put datetimes and the live buffer rows into the payload |

Write-blocks (client and service payloads cannot write the five fields):

| ID | file:line | what |
|---|---|---|
| B-W1 | websockets.py:312-317 accept, :366-382 drop | zone POST schema accepts `last_calculated` / `last_updated` as `None, str, datetime`, then `data.pop(_server_owned, None)` (:382) removes `ZONE_LAST_CONSUMED`, `ZONE_LAST_CALCULATED`, `ZONE_LAST_UPDATED` before `async_update_zone_config` (:384) |
| B-W2 | websockets.py:244-245 accept, :257-267 drop | mapping POST accepts `data` and `data_last_updated` as `object`, then filters them into `sanitized` |
| B-W3 | const.py:440-446; services.py:178-183, :212-216, :222 | `set_zone` service only takes `new_bucket/multiplier/duration/state/throughput` values, then `async_update_zone(zone_id, zone_data)` |
| B-W4 | migrate_domain.py:497-500 (docstring), :547 (`shutil.copyfile(src, dst)`) | `async_import_legacy_store` copies the pre-domain-move storage file as RAW bytes, so stored stamps arrive byte-identical (naive strings stay naive) |

## Section C. Every bare "now" outside weathermodules (24 rows)

Bare-call census: `grep -rn "\.now("` over the component minus weathermodules and frontend; comments and docstrings excluded (they are at auto_calc.py:94, calculation.py:52, :789, :1194, const.py:734, helpers.py:1008, :1023, live_estimate.py:196-197, sensor.py:606, weather_aggregate.py:112, :344). Aliases in use: `datetime.now()` (calculation.py, continuous_update.py, helpers.py, services.py, watering_calendar.py: `from datetime import datetime`), `datetime.datetime.now()` (store.py, weather_aggregate.py: `import datetime`), `dt_datetime.now()` (`__init__.py`). No other spelling exists.

| ID | file:line | function | classification | downstream uses (file:line) |
|---|---|---|---|---|
| C-01 | calculation.py:267 | `_async_clear_all_weatherdata` | PERSISTED | :300 -> `async_update_zone` (:297-308) -> zones[].last_consumed_at. No other use |
| C-02 | calculation.py:379 | `_prune_mapping_buffer` (default, only when `now is None`) | INTERNAL-COMPARE | :387 `cap_cutoff = now - BUFFER_RETENTION` -> :390 / :392 `cutoff` -> :400 `rt > cutoff`; :412-418 debug log (DISPLAY-OR-LOG). Not reachable from in-repo callers: calculation.py:474, :555 and continuous_update.py:544 all pass `now=` |
| C-03 | calculation.py:432 | `_async_calculate_all` | PERSISTED, INTERNAL-COMPARE, INTERNAL-SOLAR | :456 -> `async_calculate_zone` -> B-02/B-03/B-04 (:547/:548/:550); :474 `_prune_mapping_buffer` (:387); through `async_calculate_zone`: :526 -> weather_aggregate.py:368 / :414 / :415; :534 -> :810 `hourly_eto_priced` (hour rows and solar geometry: weather_aggregate.py:994-1011, :1018), :975 `weather_day`, :979, :1060 -> :867 `build_substeps`, :1118; :545 -> :597 |
| C-04 | calculation.py:498 | `async_calculate_zone` (default) | PERSISTED, INTERNAL-COMPARE, INTERNAL-SOLAR | same downstream list as C-03 (:526, :534, :545, :547-550, :555). Reachable via `__init__.py:2109` |
| C-05 | calculation.py:934 | `calculate_module` (default) | INTERNAL-COMPARE, INTERNAL-SOLAR | :960, :975, :979, :1060, :1118. Not reachable in-repo: the only caller passes `now=now` (:534). Nothing persisted inside `calculate_module` |
| C-06 | continuous_update.py:252 | `_continuous_seed_baseline` | PERSISTED, INTERNAL-COMPARE | :282 (RETRIEVED_AT of fresh rows); :253 `coalesce_before` -> :283 -> store.py:1989 |
| C-07 | continuous_update.py:378 | `_sensor_state_changed` | PERSISTED, INTERNAL-COMPARE, DISPLAY-OR-LOG | :439 (RETRIEVED_AT); :440 `coalesce_before` -> store.py:1989; :449-455 debug log |
| C-08 | continuous_update.py:521 | `_async_continuous_update_for_mapping` | PERSISTED, INTERNAL-COMPARE | :523 (data_last_updated), :532 (zone last_updated); :544 `_prune_mapping_buffer(now=)` -> calculation.py:387 |
| C-09 | helpers.py:1015 | `_process_timezone` | TTL/OTHER (process-zone probe) | used only by `coerce_stamp` STORE aware branch (helpers.py:1058); returns a FIXED-offset tzinfo (see F-04, P3) |
| C-10 | services.py:273 | `handle_generate_watering_calendar` | DISPLAY-OR-LOG | event payload `generated_at` (:268-275) |
| C-11 | services.py:289 | same (error branch) | DISPLAY-OR-LOG | event payload `generated_at` (:284-291) |
| C-12 | store.py:1653 | `async_create_zone` | PERSISTED | zones[].last_consumed_at (B-12) |
| C-13 | watering_calendar.py:79 | `async_generate_watering_calendar` | DISPLAY-OR-LOG | `"generated_at"` in the calendar dict (:72-80) |
| C-14 | watering_calendar.py:93 | same (error branch) | DISPLAY-OR-LOG | `"generated_at"` (:87-94) |
| C-15 | weather_aggregate.py:370 | `aggregate_window` (default) | INTERNAL-COMPARE | :414 `_hour_multiplier(window, watermark, now)` (:319), :415 `_window_bounds` (:231-232). NOT passed through `coerce_stamp` (the conditional expression coerces only the non-None branch). Reachable: `live_estimate.py:638` (from :1339, :1373, :1428) passes no `now` |
| C-16 | weather_aggregate.py:938 | `build_hourly_rows` (default) | INTERNAL-COMPARE, INTERNAL-SOLAR | :941 `_effective_series` -> :731 `_window_bounds`; hour rows :994-1011, :1018 (`tz.utcoffset(hour_start)`). Not reachable in-repo: `hourly_eto_priced` (et_estimate.py:171-182) always forwards `now`, and both of its callers pass one |
| C-17 | weather_aggregate.py:1133 | `build_substeps` (default; the "third default") | INTERNAL-COMPARE, INTERNAL-SOLAR | :1136 `_effective_series`; cuts and hours :1161-1215. Not reachable in-repo: calculation.py:867 and live_estimate.py:1109 pass `now=` |
| C-18 | __init__.py:1429 | `_clamp_solar_reading` (default when `now=None`) | INTERNAL-SOLAR, TTL/OTHER, DISPLAY-OR-LOG | :1431-1438 `clamp_solar_to_clear_sky(value, now, lat, lon, elev, offset_h)` (helpers.py:814-852 uses `when.hour`, `when.timetuple().tm_yday`); :1441-1442 `now - last >= SOLAR_CLAMP_WARN_INTERVAL` (`_solar_clamp_warned_at`, TTL); :1450 `now.isoformat(...)` in the warning. Callers pass no `now`: continuous_update.py:227, `__init__.py:1927`. Persists nothing |
| C-19 | __init__.py:1506 | `_async_update_zone` | PERSISTED | RETRIEVED_AT (B-05) |
| C-20 | __init__.py:1516 | `_async_update_zone` | PERSISTED | :1518 data_last_updated, :1525 last_updated (B-06, B-07) |
| C-21 | __init__.py:1632 | `_async_update_all` | PERSISTED | RETRIEVED_AT (B-08) |
| C-22 | __init__.py:1644 | `_async_update_all` | PERSISTED | zones[].last_updated (B-09) |
| C-23 | __init__.py:1799 | `async_update_mapping_config` | PERSISTED | :1804 last_consumed_at (B-10) |
| C-24 | __init__.py:2023 | `_book_asserted_bucket` | PERSISTED | last_consumed_at (B-11) |

### C.2 `dt_util.now()` sites compared with one of the five fields or with a value derived from them (5 rows)

| ID | file:line | compared with |
|---|---|---|
| DT-1 | auto_calc.py:96 | `cutoff = dt_util.now().replace(tzinfo=None) - timedelta(hours=...)` (:96-98) compared at :136 (`last < cutoff`) with `_parse_stored_as_ha_local(zone.get(ZONE_LAST_CALCULATED))` (:135) |
| DT-2 | live_estimate.py:264 | `now = dt_util.now()` -> `coerce_stamp(now, STAMP_FROM_CLIENT)` at :275 = `inputs["now"]`; every use of `now_local` below compares it with `anchor` (A-19/A-20) or with buffer row stamps: AC-01..AC-09, D.5 (M3-M5), D.6 (M7), D.7 (M9); also :1732 `until_local <= now_local`, :1790 `(until_local - now_local)` |
| DT-3 | live_estimate.py:1293 | fallback `dt_util.now().replace(tzinfo=None)` when `inputs["now"]` is falsy; same uses as DT-2 |
| DT-4 | live_estimate.py:1731 | same fallback in `_carry_estimate_to`; same uses as DT-2 |
| DT-5 | irrigation.py:2861 | writes `pending_bucket_events[].ts` = `dt_util.now().isoformat()` (out-of-scope AWARE field); `pending_bucket_events()` (calculation.py:47-72) flattens it to HA-local naive (:64-65) and it is then subtracted from the raw watermark (calculation.py:1123, A-14), from `anchor` (live_estimate.py:1510-1512, AC-09) and compared with window start/end inside `build_substeps` (weather_aggregate.py:1160-1163, :705-706, :1173) |

Offset-only `dt_util.now()` uses (no stamp comparison, a float offset travels instead): calculation.py:803 (`tz_offset_h`, applied to bare-now stamps, see F-10), live_estimate.py:1297 (fallback offset), `__init__.py:1430` (offset paired with the bare now of C-18, see F-10). Other `dt_util.now()` sites are unrelated to the five fields: irrigation.py:208, :223, :325, :462, :600, :664, :2897, :2938, :2975, :3071, observed_watering.py:528, scheduler.py:1489, skip_conditions.py:372, websockets.py:1102 (forecast label). `dt_util.utcnow()` at calculation.py:1198 is compared with forecast rows, not with stamps.

Adjacent bare clocks that are not `datetime.now()` (listed for completeness): calcmodules/pyeto/__init__.py:242 and :305 `datetime.date.today()` as the default for `day` (process-local date); every in-repo PyETO caller passes `day` (calculation.py:974-976, live_estimate.py:1014, watering_calendar.py:286-288), so the default is not reached from them. The Static and Passthrough `calculate()` calls (calculation.py:985, :988, watering_calendar.py:139) take no day at all.

## Section D. Entry points of weather_aggregate.py

Census of `coerce_stamp` call sites (complete): weather_aggregate.py:122 (`_parse`, STORE), :167 (STORE), :368 (STORE), :936 (STORE), :1131 (STORE); live_estimate.py:275, :464, :507, :545 (all CLIENT). Not used in calculation.py, store.py, sensor.py, auto_calc.py, continuous_update.py, `__init__.py`, websockets.py. `_parse` call sites: weather_aggregate.py:176, :206, :229, :321.

Terminology in the origin column: RAW = raw stored value, read with `as_datetime` only (parse, no frame conversion). CONVERTED = already converted by `_parse_stored_as_ha_local` / `coerce_stamp CLIENT` into HA-local naive. BARE = bare `datetime.now()`.

### D.1 `select_window(readings, watermark)` (weather_aggregate.py:144-187)

(1) Inside: `watermark` -> `coerce_stamp(watermark, STAMP_FROM_STORE)` at :167, which REBINDS THE LOCAL NAME ONLY (None short-circuits at :162-163; an unparseable value becomes None and the whole buffer becomes the window, :168-169). Row stamps -> `_parse` (STORE) at :176. Later lines using the original parameter: none inside this function (:177 uses the coerced local). The coerced value is not returned, so no caller sees it (see D.5-D.7).
(2) Callers:
- calculation.py:332 `select_window(readings, watermark)`; `watermark = _as_datetime(zone.get(const.ZONE_LAST_CONSUMED))` (:331): RAW. No `now`.
- weather_aggregate.py:374 (`aggregate_window`): its own `watermark` parameter, as received (D.5).
- weather_aggregate.py:724 (`_effective_series`): its own `watermark` parameter, as received (D.2).

### D.2 `_effective_series(readings, watermark, now)` (weather_aggregate.py:718-734)

(1) No `coerce_stamp` call in the body. `watermark` is handed to `select_window` (:724, coerced only inside) and then the ORIGINAL is used at :729 (`{**boundary, const.RETRIEVED_AT: watermark}`) and :731 (`_window_bounds(effective, watermark, now)`). `now` is used as received at :731; its callers coerce it first.
(2) Callers (only two):
- weather_aggregate.py:941 (`build_hourly_rows`): `watermark` = its parameter as received (D.6); `now` = the coerced local of :935-939.
- weather_aggregate.py:1136 (`build_substeps`): `watermark` = its parameter as received (D.7); `now` = the coerced local of :1130-1134.
Probe P1: `_effective_series(rows, aware_wm, naive_now)` -> TypeError at :232; `_effective_series(rows, naive_wm, aware_now)` -> TypeError at :231.

### D.3 `_window_bounds(effective, watermark, now)` (weather_aggregate.py:217-234)

(1) No `coerce_stamp` call on the parameters. Row stamps -> `_parse` (STORE) at :229. Original `watermark` at :230 (`start`), original `now` at :231 (`end = max([now, *stamps])`), and the comparison `end <= start` at :232.
(2) Callers:
- weather_aggregate.py:415 (`aggregate_window`): `watermark` = the UN-COERCED parameter; `now` = coerced local (:367-371).
- weather_aggregate.py:731 (`_effective_series`): `watermark` = the UN-COERCED parameter; `now` = as received from D.2's callers (coerced).
Probe P1: aware watermark -> TypeError :232; aware `now` -> TypeError :231.

### D.4 `_hour_multiplier(window, watermark, now)` (weather_aggregate.py:311-325)

(1) No `coerce_stamp` call on the parameters. `_parse` (STORE) only for row stamps at :321 (used only when the watermark is None). Original `watermark` and `now` at :319 (`now - watermark`).
(2) Caller: weather_aggregate.py:414 (`aggregate_window`): `watermark` = UN-COERCED parameter, `now` = coerced local.
Probe P1: aware watermark -> TypeError :319. Probe P2: an ISO-string watermark -> TypeError :319 too (`select_window` accepts the string, `_hour_multiplier` does not).

### D.5 `aggregate_window(readings, watermark, mappings_config, *, now=None, last_entry=None, time_weighted=False)` (weather_aggregate.py:328-424)

(1) `now`: `coerce_stamp(now, STAMP_FROM_STORE)` at :368 when not None; when None the default is a bare `datetime.datetime.now()` at :370 (the default branch is NOT passed through coerce_stamp). `watermark`: NEVER coerced in this function. It goes to `select_window` (:374, coerced only inside) and the ORIGINAL parameter is used at :382 (RETRIEVED_AT of the synthetic boundary row; that row is later re-read by `_parse` at :206), :414 (`_hour_multiplier`, TypeError source at :319) and :415 (`_window_bounds`, TypeError source at :232).
(2) Callers:
- calculation.py:333-357 (`_aggregate_for_zone`): `watermark` = `_as_datetime(zone.get(const.ZONE_LAST_CONSUMED))` (:331), RAW. `now=now`: parameter of `_aggregate_for_zone` <- calculation.py:526 <- `async_calculate_zone`'s `now`: BARE at calculation.py:432 (passed at :456) or BARE default at :498 (`__init__.py:2109` path).
- live_estimate.py:596-617 (`_aggregate_live_window(zone, anchor, *, now=None)`): `watermark` = `anchor` = `_window_anchor(zone)` (:1288 / :1741), CONVERTED by `_parse_stored_as_ha_local` (:246-250). Three routes for `now`:
  - :1322 (`_intraday_for_zone`) `now=now_local`: CONVERTED, HA-local naive, built at :1293 as `inputs.get("now") or dt_util.now().replace(tzinfo=None)`; `inputs["now"]` = `coerce_stamp(dt_util.now(), STAMP_FROM_CLIENT)` at :275.
  - :1764 (`_carry_estimate_to`) `now=now_local`: CONVERTED, same expression at :1731.
  - :638 (`_observed_precip_since_mm`, called from :1339, :1373, :1428): no `now` -> None -> BARE default at weather_aggregate.py:370. This is the one live-estimate call that lands on the default.

### D.6 `build_hourly_rows(readings, watermark, mappings_config, *, now=None, last_entry=None, latitude=None, longitude=None, elevation=0.0, tz_offset_h=0.0, tz=None)` (weather_aggregate.py:869-1044)

(1) `now`: `coerce_stamp(now, STAMP_FROM_STORE)` at :936, BARE default at :938 (default not coerced). `watermark`: NEVER coerced; the only use is :941 (`_effective_series`), where the original is used at :729 / :731. A line-by-line search of :869-1044 finds `watermark` on no other line (only the parameter at :871).
(2) Only caller: et_estimate.py:171-182 (`hourly_eto_priced`), which forwards its own `watermark` and `now` verbatim (:172-175). Callers of `hourly_eto_priced`:
- calculation.py:806-816 (`_hourly_et_for_zone`): `watermark` = `_as_datetime(zone.get(const.ZONE_LAST_CONSUMED))` (:808), RAW; `now=now` (:810) <- `calculate_module(now=)` :960 <- calculation.py:534 <- `async_calculate_zone`'s `now` (BARE :432 / :498), or the BARE default of `calculate_module` :934.
- live_estimate.py:743-750 (`_buffer_hourly_et`): `watermark` = local of :731-734 = `anchor` (CONVERTED) or `carry.boundary` (= `current_hour`, :762 / :771-772, derived from `now`, i.e. already HA-local); `now=now` (:747) = `now_local` from :1312 (CONVERTED).

### D.7 `build_substeps(readings, watermark, mappings_config, *, now=None, hourly_et=None, applied=None)` (weather_aggregate.py:1081-1239) — this is the function holding the third default (`datetime.datetime.now()` at :1133)

(1) `now`: `coerce_stamp(now, STAMP_FROM_STORE)` at :1131, BARE default at :1133 (default not coerced). `watermark`: NEVER coerced; only use :1136 (`_effective_series`, then :729 / :731 with the original). `applied` is not coerced either: after the None/zero filter (:1160) its stamps go into `_substep_boundaries(start, end, ...)` (:1161-1163; `start < t < end` at :705-706) and `bisect.bisect_left(cuts, t)` (:1173).
(2) Callers:
- calculation.py:863-870 (`_substeps_for_zone`): `watermark` = `_as_datetime(zone.get(const.ZONE_LAST_CONSUMED))` (:865), RAW; `now=now` (:867) <- `_substeps_for_zone(..., now=now)` <- calculation.py:1060 <- `calculate_module`'s `now` (BARE, see D.6); `applied=applied` <- `pending_bucket_events(zone)` (:1058), CONVERTED (HA-local naive, :64-65).
- live_estimate.py:1105-1112 (`_buffer_water_steps`): `watermark` = `anchor` (CONVERTED, passed from :1468-1472); `now=now` (:1109) = `now_local` (:1471, CONVERTED); `applied=applied` <- `pending_bucket_events(zone)` (:1478), CONVERTED.

### D.8 Additional entry point, not requested: `weather_day(window_start, window_end)` (weather_aggregate.py:237-260)

No coercion; returns a date only (`(window_start + 12 h).date()` or `window_end.date()`). Callers: calculation.py:974-976 (`_as_datetime(zone.get(ZONE_LAST_CONSUMED))` RAW, `now` BARE) and live_estimate.py:992 (`anchor` CONVERTED, `now` CONVERTED).

### D.9 Caller matrix

"Second STORE coercion" = the value is already in the internal (HA-local naive) frame and then enters a `coerce_stamp(..., STAMP_FROM_STORE)` call. Today that is harmless because a naive value passes through untouched (helpers.py:1055-1056); it becomes a second conversion the moment the STORE branch starts lifting naive values.

| ID | caller | watermark expression and origin | now expression and origin | second STORE coercion of an already-converted value? |
|---|---|---|---|---|
| M1 | calculation.py:332 -> `select_window` | `_as_datetime(zone.get(ZONE_LAST_CONSUMED))` :331, RAW | none | no |
| M2 | calculation.py:333 -> `aggregate_window` | same RAW value | `now`: BARE :432 (-> :456) or :498 | no; but the watermark is also used un-coerced at weather_aggregate.py:382, :414, :415 |
| M3 | live_estimate.py:1322 via :596 -> `aggregate_window` | `anchor`, CONVERTED (:246-250) | `now_local` :1293, CONVERTED (:275) | YES for both: `select_window` :167 (watermark), :368 (now), and `_parse` :206 of the boundary row that :382 stamps with the anchor |
| M4 | live_estimate.py:1764 via :596 -> `aggregate_window` | `anchor` (:1741), CONVERTED | `now_local` :1731, CONVERTED | YES, as M3 |
| M5 | live_estimate.py:638 via :596 (from :1339, :1373, :1428) -> `aggregate_window` | `anchor`, CONVERTED | None -> BARE default weather_aggregate.py:370 (never coerced) | watermark YES; `now` is in the process frame while the anchor is HA-local |
| M6 | calculation.py:806-816 -> `hourly_eto_priced` -> `build_hourly_rows` | `_as_datetime(...)` :808, RAW | `now` :810 <- :960 <- :534 <- BARE :432 / :498 (or :934) | no |
| M7 | live_estimate.py:743 -> `hourly_eto_priced` -> `build_hourly_rows` | `anchor` or `carry.boundary` (:731-734), CONVERTED | `now_local` :1312, CONVERTED | YES: :167 via `_effective_series` :724, :936 |
| M8 | calculation.py:863 -> `build_substeps` | `_as_datetime(...)` :865, RAW | `now` :867 <- :1060 <- BARE | no |
| M9 | live_estimate.py:1105 -> `build_substeps` | `anchor`, CONVERTED | `now_local` :1471, CONVERTED | YES: :167, :1131 |
| M10 | calculation.py:974-976 -> `weather_day` | `_as_datetime(...)` :975, RAW | `now` BARE | n/a (no coercion in `weather_day`) |
| M11 | live_estimate.py:992 -> `weather_day` | `anchor`, CONVERTED | `now` (= `now_local`, from :1045 / :1053 / :1774-1783) | n/a |

## Section E. The store's load and save path

- Conversion on load: NONE. `async_load` (store.py:905-1339) reads `data = await self._store.async_load()` (:907) and hydrates zones with plain `zone.get(...)` at store.py:1157, :1161-1164, :1165 and mappings at :1289. No parser is called in the load path (store.py uses `as_datetime` only at :1921 and :1985, both at read time, and `datetime.datetime.now()` only at :1653). The only converter-shaped code near the fields is the type annotation `attr.ib(type=datetime, ...)` (store.py:253-256, :353), where `datetime` is the MODULE (`import datetime`, store.py:3) and no converter or validator is attached.
- Buffer rows: left as strings. `_as_buffer(mapping.get(MAPPING_DATA))` (store.py:1282-1284, definition :865-879) returns the loaded list untouched; RETRIEVED_AT stays the ISO string JSON gave (the comment at store.py:1980-1984 says so for the buffer, and wrongly implies the zone watermarks ARE converted, see F-08).
- Consequence for readers: the same field is a `str` after a restart and a `datetime` after the next in-process write (calculation.py:547-550, `__init__.py` writers). Every reader therefore has to accept both, which is why `as_datetime` exists.
- Migration: `STORAGE_VERSION = 14` (store.py:198), `class MigratableStore(Store)` (store.py:603) with `_async_migrate_func(self, old_version, data)` (store.py:606-862), instantiated at store.py:903 (`MigratableStore(hass, STORAGE_VERSION, STORAGE_KEY)`). It handles v3, <=4, <=6, <=8, <=9, <=10, <=11, <=12, <=13 (store.py:619-766) and then normalises/strips the `config` block (:768-860). None of the migrations touches any of the five fields. HA calls it only when the stored version or minor version differs (`homeassistant/helpers/storage.py:391-419` in the .venv). The project convention is "hydrate additive fields with `.get` defaults, STORAGE_VERSION stays put" (store.py:473, :1078, :1096, :1126, :1221).
- Domain-move import: `migrate_domain.async_import_legacy_store` (migrate_domain.py:492-575; the copy is `shutil.copyfile(src, dst)` at :547) copies the old storage file as raw bytes, then `MigratableStore` handles the version; stamps arrive verbatim.
- Save path: `async_schedule_save` -> `self._store.async_delay_save(self._data_to_save_scheduled, SAVE_DELAY)` (store.py:1473-1476; `SAVE_DELAY = 30`, store.py:208), `async_save` -> `self._store.async_save(self._data_to_save_full())` (:1478-1480). Payload builders: `_data_to_save` (store.py:1534-1557: `attr.asdict` of config, zones, modules, mappings, distributors; datetimes stay `datetime` objects) and `_data_to_save_full` (:1560-1571: adds `mapping[MAPPING_DATA] = self.buffers.get(...)`, :1569). There is no `isoformat` and no custom encoder anywhere in store.py (`MigratableStore` is built without `encoder=`, :903).
- Serialisation is therefore HA's default (verified in the .venv HA 2024.12.5, production version NOT VERIFIED): `Store._write_data` -> `json_helper.save_json(path, data, self._private, encoder=self._encoder, atomic_writes=...)` (homeassistant/helpers/storage.py:556-562) -> with `encoder=None` the orjson branch `_orjson_bytes_default_encoder` = `orjson.dumps(data, option=OPT_INDENT_2 | OPT_NON_STR_KEYS, default=json_encoder_default)` (homeassistant/helpers/json.py:186-192, :195-218). orjson writes datetimes itself: probe P4 shows a naive value as `2026-09-28T12:00:00.000005` (no offset), a naive value with microsecond 0 as `2026-09-28T10:00:00` (fraction omitted, the case the docstring at helpers.py:960-978 is about), an aware `Europe/Berlin` value as `2026-09-28T12:00:00.000005+02:00`. `json_encoder_default` (json.py:70-87) `isoformat()` is only the fallback for non-native types.

## Section F. Anything surprising (ordered by importance)

F-01. `aggregate_window` and `_effective_series` hand the UN-COERCED watermark to the code that compares it. `select_window` coerces its own local (weather_aggregate.py:167) and returns none of it; the original goes on at :382 (boundary row stamp), :414 -> `_hour_multiplier` :319 (`now - watermark`), :415 -> `_window_bounds` :230/:232, and at :729/:731 for `build_hourly_rows` and `build_substeps`. `_window_bounds` and `_hour_multiplier` do not coerce `watermark` or `now` at all (:229-232, :319). Measured (P1/P2): an aware watermark raises at :319 (via `aggregate_window`) and at :232 (via `_effective_series`, `build_hourly_rows`, `build_substeps`); an aware `now` handed to `_window_bounds` raises at :231; an ISO-STRING watermark raises at :319. So the uniformity the design doc relies on (design doc :96-99: "`weather_aggregate.py:167` coerces the watermark and `:122` coerces the row stamps ... the translation is uniform by construction") holds for the comparisons inside `select_window` only. The three coerce sites for `now` (:368, :936, :1131) are correct for `now`, but the default branch of each conditional (:370, :938, :1133) is not coerced.

F-02. Under the target semantics (naive STORE input lifted from the process zone into HA-local), the live-estimate path would convert twice. It feeds values that are ALREADY HA-local naive (`anchor` from `_parse_stored_as_ha_local`, live_estimate.py:246-250; `now_local` from `coerce_stamp(..., CLIENT)`, :275) into `select_window` :167, `aggregate_window` :368, `build_hourly_rows` :936, `build_substeps` :1131, and, through the boundary row stamped at :382 / :729, into `_parse` :206 (matrix rows M3, M4, M7, M9; also `carry.boundary` at live_estimate.py:734). Harmless today only because a naive input is returned untouched (helpers.py:1055-1056). `live_estimate.py:638` (M5) is the opposite case: it lands on the never-coerced BARE default at weather_aggregate.py:370 while its watermark is HA-local, i.e. the process clock is compared with an HA-local anchor.

F-03. Raw `as_datetime` readers compare a stored value with bare-now operands and do no frame work: calculation.py:331, :398, :808, :865, :975, :1116 and store.py:1921, :1985. With one aware stored value (or a MIXED store: old naive rows/zones next to new aware ones, which is exactly the state right after an upgrade) these raise TypeError at store.py:1939 (`min(watermarks)`), :1989, :1990; calculation.py:392, :400, :403 (via weather_aggregate.py:140), :407, :1123; and inside weather_aggregate.py per F-01. Where they are caught: only the calc-all loop (calculation.py:460, ERROR log, zone skipped, watermark not advanced) and the live estimate (DEBUG only, TE-LIVE1/2, feature silently unavailable); the ingestion path is caught by HA's dispatcher (ERROR, reading lost, TE-ING); `_prune_mapping_buffer` from calculation.py:474 and continuous_update.py:544, `async_guard_ledger_staleness`, and the zone-POST calculate path (websockets.py:385 catches `SmartIrrigationError` only) are not caught in this code. `as_datetime` also raises ValueError on a malformed string (helpers.py:982) where `coerce_stamp` returns None (helpers.py:1049-1052): swapping the parser changes that behaviour at every one of those sites.

F-04. The STORE branch of `coerce_stamp` is not the frame the design names, and it is subtly wrong for old stamps. The design doc (:50-62, decision R3-1) and the task brief name one internal frame, naive HA-local. (a) An aware STORE input is converted to the PROCESS zone (helpers.py:1057-1058), not to HA-local (that is the CLIENT branch, :1059); a naive input is returned untouched for both provenances (:1055-1056). (b) `_process_timezone()` returns `datetime.now().astimezone().tzinfo` (helpers.py:1015), a FIXED-offset `datetime.timezone` frozen at the moment of the call (P3: `timezone(timedelta(seconds=7200), ...)`), so every aware stamp is shifted by TODAY's offset, not the offset of the stamp's own date: P3 converts `2026-01-15T12:00Z` to 14:00 where `astimezone()` with no argument gives 13:00. That is a one-hour error for stamps on the far side of a DST change, and the buffer keeps seven days (calculation.py:44).

F-05. Scope mismatch between "persisting writers" and what the code does. The design doc (:158-166) lists 16 "persisting writers": `__init__.py` 1429, 1506, 1516, 1632, 1644, 1799, 2023; calculation.py 267, 379, 432, 498, 934; continuous_update.py 252, 378, 521; store.py 1653. Three of the sixteen persist nothing: `__init__.py:1429` persists nothing (solar clamp: INTERNAL-SOLAR, TTL, log; C-18); `calculation.py:379` and `:934` are compare-only defaults that no in-repo caller reaches (C-02, C-05). Conversely, for the persisting writers the variable is shared with compare uses: `continuous_update.py:521` (persisted :523/:532 and compared through :544), `continuous_update.py:252` / `:378` (persisted, and `coalesce_before` compared with stored stamps at store.py:1989), `calculation.py:432` / `:498` (persisted at :547-550, and compared throughout B-02's list). Moving those to an aware clock changes the compare operand at the same time. Also `_async_update_all` never writes `data_last_updated` (compare `_async_update_zone` :1518 and continuous_update.py:523) and each of its two persisting statements takes its own clock read (:1632 for RETRIEVED_AT, :1644 for last_updated), while `_async_update_zone` also takes two (:1506, :1516) but shares the second one between the mapping and the zone.

F-06. One stored naive stamp is read in four frames. The same `last_calculated` / `last_updated` string is: taken as HA-local by `_parse_stored_as_ha_local` (live_estimate.py:226 for naive, :225 `dt_util.as_local` for aware; auto_calc.py:135 compares the result with the HA-local cutoff built at auto_calc.py:96-98), taken as HA's zone by `_to_aware_datetime` (sensor.py:620, `dt_util.DEFAULT_TIME_ZONE`), left frameless by `as_datetime` and then compared with bare-now (calculation.py:331 etc.), taken as process-local by `coerce_stamp` STORE (weather_aggregate.py:122, :167), and kept frameless by `_safe_parse_datetime` (websockets.py:73-76) and by the browser (`new Date`, A-F1). These agree only when the process zone equals HA's zone.

F-07. Daily and live twins disagree about the frame of pending credits: calculation.py:1116-1123 subtracts HA-local `stamp` from the RAW watermark, live_estimate.py:1510-1512 subtracts it from the HA-local anchor; `build_substeps` compares `applied` (HA-local, never coerced, weather_aggregate.py:1160-1173) with window bounds built from process-local stamps.

F-08. Misleading comment: store.py:1980-1984 says `async_load` "never converts buffer rows the way it does zone watermarks". `async_load` converts neither (store.py:1157-1165, :1282-1289, Section E). The in-memory type of every stamp flips between `str` and `datetime` around each restart.

F-09. The client sees mixed shapes: `websocket_get_zones` and `websocket_get_weather_records` send naive ISO strings without an offset (A-28, A-31); the browser reads those as its own local time and an aware string as an absolute instant (A-F1, A-F2). `_safe_parse_datetime` (websockets.py:63-80) maps aware values to naive UTC and leaves naive ones as they are, so a buffer holding both shapes is sorted on two different scales (A-30; no exception). The live estimate publishes derived values the same way: `as_of` is `now_local.isoformat()` (live_estimate.py:1342, :1359, :1430; HA-local naive, no offset), or a weather client's row time (:1375), and reaches the entity attributes at sensor.py:788; `projected_to` is `until_local.isoformat()` (:1718).

F-10. HA's zone is applied to process-local stamps in three places, each with its own float offset: calculation.py:786 (`tz = dt_util.DEFAULT_TIME_ZONE`), :803-804 (`dt_util.now().utcoffset()`) -> `SiteGeometry` -> weather_aggregate.py:1018 (`tz.utcoffset(hour_start)` where `hour_start` derives from buffer stamps), :759-763 (`row.get("tz_offset_h", ...)`), et_estimate.py:140; `__init__.py:1430` (HA offset) with the bare now of C-18; live_estimate.py:842-843 (`commit_at.replace(tzinfo=site_tz)`, consistent there because the anchor is HA-local). The offset does not travel as `tzinfo` (comment calculation.py:796-800), so an aware stamp leaves these untouched.

F-11. `pending_bucket_events()` flattens aware `ts` values to HA-local naive with `dt_util.as_local(...).replace(tzinfo=None)` (calculation.py:64-65). This is the one place today where an aware stamp is converted to HA-local naive; it is done independently of, and in a different frame from, the watermark it is later subtracted from (F-07).

F-12. Possible sixth place a stamp can hide (NOT VERIFIED): `aggregate_window` skips a `retrieved` key inside `last_entry` (`if key == const.RETRIEVED_AT: continue`, weather_aggregate.py:393) and `calculation.py:290` / `__init__.py:1795` null every `data_last_entry` key, which suggests an older release stored the stamp inside `mappings[].data_last_entry`. The current writers never do (store.py:2019-2051 only sets sensor fields). Whether any deployed store still holds one was not checked.

F-13. Comments and docstrings that assert the naive convention and will be false after the change (checklist): calculation.py:47-55 and :778 and :787-802 and :1193-1197; auto_calc.py:93-95; continuous_update.py:375-377; `__init__.py:2017-2022`; live_estimate.py:192-215, :1188-1190, :1406-1411, :1435-1436; sensor.py:603-608; weather_aggregate.py:103-121, :164-166, :254-255, :356-366, :924-934, :1119-1129; const.py:734; store.py:1980-1984; helpers.py:1018-1044; websockets.py:66, :73.

F-14. Domain-migration import copies raw bytes (migrate_domain.py:497-500), so a pre-change store keeps naive strings forever unless a zone is recalculated or a buffer row is rewritten; nothing in the load path rewrites them (Section E).

## Appendix 1. Complete call-site census of the parsing helpers (whole component minus weathermodules)

- `as_datetime` / `_as_datetime`: calculation.py:61 (pending-event `ts`, out-of-scope field), :331, :398, :808, :865, :975, :1116; store.py:1921, :1985; helpers.py:1050 (inside `coerce_stamp`).
- `coerce_stamp`: see Section D preface.
- `_parse_stored_as_ha_local`: live_estimate.py:246, :249; auto_calc.py:135.
- `_window_anchor`: live_estimate.py:1288, :1741.
- `_to_aware_datetime`: sensor.py:825 (`last_irrigation`, out-of-scope), :890 (`next_run_utc`, out-of-scope), :1105 (A-27).
- `_safe_parse_datetime`: websockets.py:568.
- `get_enabled_zone_watermarks`: calculation.py:388, store.py:1938; `get_min_enabled_watermark`: continuous_update.py:277, :441.
- Other `fromisoformat` / `dt_util.parse_datetime` sites (all on other fields): datetime.py:86, irrigation.py:200, :441, live_estimate.py:457 (forecast rows), :1197, opensprinkler.py:308, run_state.py:114, run_watch.py:327, :335, run_window.py:423, scheduler.py:1552, :2260, :2270, self_closing.py:337, :912, skip_conditions.py:345.

## Appendix 2. Probes run (in-memory, `python -B`, nothing written, no test suite)

Interpreter: `D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe`, run with cwd = the worktree.

P1 (`weather_aggregate` with naive/aware inputs; rows naive, `now` naive 2026-09-28 12:00):
```
OK   select_window(aware wm)
FAIL aggregate_window(aware wm, naive now)   TypeError can't subtract offset-naive and offset-aware datetimes @ weather_aggregate.py:319 _hour_multiplier
OK   aggregate_window(naive wm, aware now)
OK   aggregate_window(naive wm, naive now)
FAIL _hour_multiplier(aware wm)              TypeError ... @ weather_aggregate.py:319
FAIL _window_bounds(aware wm)                TypeError can't compare ... @ weather_aggregate.py:232
FAIL _window_bounds(naive wm, aware now)     TypeError can't compare ... @ weather_aggregate.py:231
FAIL _effective_series(aware wm)             TypeError ... @ weather_aggregate.py:232 _window_bounds
FAIL _effective_series(naive wm, aware now)  TypeError ... @ weather_aggregate.py:231 _window_bounds
FAIL build_substeps(aware wm)                TypeError ... @ weather_aggregate.py:232 _window_bounds
OK   build_substeps(naive wm) sanity
```
P1b (`build_hourly_rows` with rows that carry the four required fields under their const keys `Temperature`, `Humidity`, `Windspeed`, `Solar Radiation`; the first attempt with wrong keys is not counted):
```
OK   build_hourly_rows(naive wm, naive now)   -> list of 6 rows
FAIL build_hourly_rows(aware wm, naive now)   TypeError can't compare offset-naive and offset-aware datetimes @ weather_aggregate.py:232 _window_bounds
OK   build_hourly_rows(naive wm, aware now)   -> list of 8 rows (the aware `now` is coerced at :936)
FAIL build_hourly_rows(aware wm, aware now)   TypeError ... @ weather_aggregate.py:232 _window_bounds
```
So an aware `now` is survivable at the three coerced entry points, an aware watermark is not.
P2: `aggregate_window(rows, "2026-09-28T06:00:00", {}, now=naive)` -> TypeError at weather_aggregate.py:319; `select_window(rows, "2026-09-28T06:00:00")` -> OK. `as_datetime("...T06:00:00")` gives tzinfo None, `as_datetime("...T06:00:00+00:00")` gives UTC, and `min([naive, aware])` raises TypeError.
P3: `helpers._process_timezone()`-equivalent `datetime.now().astimezone().tzinfo` = `datetime.timezone(datetime.timedelta(seconds=7200), ...)` (fixed offset). `2026-01-15T12:00Z` -> via that tzinfo 14:00, via `astimezone()` with no argument 13:00.
P4 (HA 2024.12.5 `homeassistant.helpers.json.json_bytes`): `{"a": naive 10:00:00, "b": naive 10:00:00.123456, "c": aware UTC}` -> `"2026-09-28T10:00:00"`, `"2026-09-28T10:00:00.123456"`, `"2026-09-28T10:00:00+00:00"`; `Europe/Berlin` aware 12:00:00.000005 -> `"2026-09-28T12:00:00.000005+02:00"`.

## Appendix 3. NOT VERIFIED (collected)

- Production HA version behaviour of `Store`/JSON (only the test venv HA 2024.12.5 was inspected).
- What HA does with an exception escaping a `hass.async_create_task` coroutine (A-21, `__init__.py:2162`, continuous_update.py:508-554).
- Whether the scheduler frames above `async_commit_pre_run_calculation` (scheduler.py:1827, :1969, :2351) catch a TypeError.
- The frame of the weather clients' hourly `row["time"]` used in `_rows_since` (AC-06) and whether `client.get_data` returns a fresh dict per call (B-05); weathermodules were out of scope.
- Any deployed store holding a `retrieved` key inside `data_last_entry` (F-12).
- Frontend behaviour beyond reading the TypeScript.
