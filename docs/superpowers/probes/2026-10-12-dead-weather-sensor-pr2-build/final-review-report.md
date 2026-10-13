# Final review (Opus) — feat/pause-silent-weather-sensor, 6a40e083..a9708bec

Transcribed by the controller from the reviewer's hand-back message (2026-10-12); the transcript file holds no
extractable copy. Content unchanged, layout lightly condensed.

Reviewed in four passes (diff, worktree code around it, tests, ledger). Nothing mutated (HEAD a9708bec, status clean).
One read-only probe in the session scratchpad (`probe_rain_notice.py`) calling the branch's real functions:

```
rain gauge: notice key = weather_sensor_stale_paused
rain gauge: gate blocks = None
calm night: blocked = {'Windspeed': ((2026-07-02 00:00, 2026-07-02 07:00),)}
calm night: share of the day's ET booked = 0.708
```

## Strengths
- Byte-identity holds: gate returns None for keep, hourly on, no watermark, no group, or no span left after the delta
  filter; with None `_aggregate` takes the old path, `calculate_module` leaves `share` None (`!= 0` true, `== 0`
  false, scaling skipped), explanation and both records skipped. Substeps need the hourly calculation, which turns the
  cut off, so a cut window never reaches `replay_water_balance`.
- Store compatibility: no version bump; load path coerces missing/unknown/unhashable to keep; an old panel omitting
  the key leaves the setting (`attr.evolve`); rollback safe (`git log -S"MappingEntry(**mapping"` finds no build that
  loaded mappings by kwargs).
- Failure isolation: new commit code runs inside calc-all's per-zone try/except; the watermark moves only on the final
  write; a raise loses no data.
- `_aggregate_blocked` matches spec §2 (boundary row held, counts as sample only when the window start is valid; F2;
  rain-rate trapezoids only valid part; fields without spans untouched).
- Clean texts: no own references; 8 languages with identical placeholders (script).

## Important (Should Fix)

1. **Notice and log announce a cut the calculation never makes** (`sensor_liveness.py:568-585`
   `_group_cuts`/`_stale_issue_key`, `:513`, vs. the gate's delta filter `calculation.py:440-446`). `_group_cuts` =
   pause AND not hourly; it ignores the rain-gauge exception. Probe: a pausing group whose only silent sensor is a delta
   rain counter gets `weather_sensor_stale_paused` ("these values are no longer used … water less or not at all") and
   the WARNING "no evapotranspiration is booked", while the gate blocks nothing. Common: docs `:66` says a YAML
   utility-meter rain counter looks silent on a dry day; new groups pause by default → false notice every dry day.
   Milder, same cause: only humidity or solar silent (PyETO daily form needs neither) → "no evapotranspiration is
   booked" is false. Fix: one shared "cuttable fields" helper (non-delta) for gate and `_group_cuts`; paused text + log
   only when an open outage has a cuttable field; test (pausing group, only delta gauge silent → `weather_sensor_stale`,
   log "still used"). Wording for non-required fields = human decision.

2. **Default `pause` turns a known false "silent" into a real ET cut on a required field** (docs `:43-49`, `:66`).
   The docs recommend a legacy YAML template `wind_at_2m` (no unique_id → no device → only its own `last_reported`).
   Calm night: anemometer at 0, template never writes; 21:00–07:00 blocks Windspeed 00:00–07:00 → share 0.708, ~29 % of
   the day's ET dropped every calm night. Rev. 3 accepted this sensor class only as a false notice; decision 9 names the
   price only for slow integrations. Fix (human decision): at minimum the `:66` paragraph says what Pause does to such
   sensors and advises Keep or a UI template helper attached to the station's device; beyond that a hint in the
   notice, or exempt device-less entities from the cut.

## Minor
1. Unreachable branches `weather_aggregate.py:647` (`if values else held[0]`) and `:650-651` (`elif not values`) —
   equivalent mutants; remove with a one-line comment.
2. Rounding `calculation.py:1916`: 2-minute block prints "… booked for 100 %"; shares just above 0 print "0 %".
   Suggest floor capped at 99 below 1, ceil min 1 above 0 (format plan-mandated; human decides).
3. Misleading comments: `calculation.py:421-422` ("cuts together with the live estimate"), `const.py:716-717`
   ("Chosen while the daily form … is the one that cuts"), `live_estimate.py:21` and `:913` ("converges on exactly what
   the commit will see") — commit a9708bec's message claims those were qualified.
4. Setting name: panel help (`en.json:470` + 7 languages) and docs `:62` say "the hourly calculation"; the setting is
   titled "Hourly evapotranspiration" (`en.json:363`).
5. Docs wording: `:59` "created from now on", `:60` "existed before" are relative to today; `:64` "With **Pause**, set
   such a sensor group to **Keep the last value**" reads like a contradiction.
6. Test pins (each mutant survives today): a) schema omission stays omitted (`MAPPING_VIEW_SCHEMA({}) == {}`; mutant
   `default="pause"` would flip every keep group on an old panel's save); b) gate test with an open outage; c) "valid
   time empty → no last_entry fill" (`test_weather_aggregate_blocked.py:126-130` fixture has T rows); d) two spans on
   one field; e) share-0 sentence; f) `test_changing_the_setting_rewrites_the_open_notice` should start on keep with
   an existing notice, then switch (also pins hook-after-write).
7. Unguarded re-sync hooks `__init__.py:1246-1250`, `:1844-1846` (setup wraps the same work in try/except); a raise
   would skip the `_config_updated` dispatch and return 500; nothing realistic raises today.

## Triage of the deferred minors (ledger)
- T1 valid_share no clip — can stay. T1 touching spans / `_merged` `<=` — should fix. T1 OverflowError — can stay.
  T1 comments — should fix "Chosen while…", grammar can stay. T1 typing — can stay.
- T2 "PAUSE" load path — can stay. T2 redundant migration test — can stay. T2 no write validation — can stay.
- T3 last_entry inert — should fix (6c). T3 unreachable branches — should fix (Minor 1). T3 multi-span — should fix
  (6d), rest can stay. T3 clock-skew asymmetry — can stay. T3 single-row Riemann — can stay.
- T4 open-outage gate test — should fix (6b). T4 offset test — can stay. T4 gate docstring — should fix. T4
  `watermark >= now` — can stay.
- T5 forecast-days test — can stay. T5 hourly test — can stay. T5 share near 0 / rain partial — can stay. T5 window
  twice — can stay. T5 et_term — can stay.
- T6 rounding — should fix, human decides. T6 share-0 sentence — should fix (6e). T6 order, Kc, Bucket space, Static
  sentence — can stay.
- T7 hooks unguarded — can stay. T7 hook order — should fix (6f). T7 config save w/o hourly key — can stay. T7
  @callback — can stay. T7 `_group_cuts` coupling — should fix with Important 1. T7 notice wrong for rain gauges —
  **must fix before upstream** (Important 1).
- T8 display `?? "pause"` — can stay. T8 schema omission — should fix (6a). T8 TS literals — can stay.
- T9 "no evapotranspiration" only required fields — should fix with Important 1 wording (human). T9 live_estimate
  exactness — should fix (Minor 3). T9 UI name — should fix (Minor 4). T9 `:64` — should fix (Minor 5). T9 "last
  report" — can stay. T9 gate docstring — should fix.

## Declined to judge
- Share by time, not sun-weighted; partial-day means — F3. Live estimate does not cut — Rev. 3 / part 3. Default pause
  costing slow integrations — decision 9 (only the device-less case raised). Up to 5 min between open/close and the
  block — spec §1. Rain booked in full — spec §3. Single-sample riemannsum/sum — spec §2. Sub-step spreading —
  unreachable. DST — not required, no new failure. Static zones sentence 1 — plan. "Bucket was" space — pre-existing.
  Rollback to PR-1 build loses pause — spec §4. 28 Lingering-timer errors — local env. Upstream CI ruff unpinned —
  outside branch. Panel `?selected` — consistent with existing selects.

## Recommendations
1. Fix Important 1 with a shared "cuttable fields" helper + delta-only test; human decides paused wording for
   non-required fields. 2. Put Important 2 to the human. 3. Batch cheap pins 6a–6f, dead branches, comment fixes; re-run
   mutations with added mutants (schema default, `_merged` `<=`, gate `now` → clock). 4. PR text: keep rollback note and
   live-estimate caveat.

## Assessment
**Ready to merge?** With fixes. Calculation, byte-identity for keep, store compatibility and failure isolation are
sound; but notice/log claim a cut for silent rain gauges (and overstate it for non-required fields), and the new
default turns the documented device-less false alarm into real ET loss on calm nights.
