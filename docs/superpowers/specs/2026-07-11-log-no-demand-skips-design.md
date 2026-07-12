# Log "no demand" skips in the run history — Design

**Date:** 2026-07-11
**Status:** Approved (design), pending spec review
**Type:** Feature (opt-in, additive)

## Problem

When a scheduled irrigation run evaluates a zone and finds no water demand
(computed duration 0 / bucket already at or above its threshold), the zone is
silently dropped from the candidate list and the scheduler returns without
leaving any trace. See `irrigation.py` — the candidate filter drops
no-demand zones, then `if not zones_to_irrigate: return` only emits a
`_LOGGER.debug` line.

As a result, the zone's **Bewässerungsverlauf** (run history card) shows
nothing for that day, and the user cannot distinguish "HASI evaluated the zone
and decided no water was needed" from "HASI never looked / something is broken."

By contrast, HASI already records a `skipped` run-history entry for the *active*
skip decisions:

- **Weather / schedule conditions** (rain forecast, freeze, days-between, rain
  sensor): `scheduler.py` records a skipped run with the reason ids for all
  targeted zones before returning.
- **Rain delay / pause**: `_record_skipped_run(zone_ids, SKIP_REASON_PAUSED)`.
- **Per-zone soil-moisture wet-veto**:
  `_record_run(result=SKIPPED, detail=SKIP_REASON_SOIL_MOISTURE)`.

Only the "no demand" case leaves no record. The same gap exists for distributor
**member** zones: a non-due member is skip-pulsed to advance the ring but leaves
no history entry.

## Goal

When (and only when) the user opts in, a scheduled run that does not water a
zone/member **specifically because it has no water demand** leaves exactly one
`skipped` run-history entry per zone with a new reason **`no_demand`** —
de-duplicated to at most one per zone per calendar day.

Default-off means existing installs behave byte-for-byte as today.

## Non-goals

- No change to *when* watering happens — this is logging only.
- No change to the forward-looking dashboard outlook (which already explains why
  the *next* run will/won't water). This feature adds the missing *historical*
  record.
- Cumulative flow-volume metering is unrelated and untouched.

## Design

### 1. Config toggle

- New constants in `const.py`:
  - `CONF_LOG_NO_DEMAND = "log_no_demand"`
  - `CONF_DEFAULT_LOG_NO_DEMAND = False`
- New boolean field on `Config` (`store.py`), added with a storage migration so
  existing configs load with the default (`False`).
- CRUD pass-through in the websocket/config update path, matching the existing
  boolean-field pattern (e.g. `automatic_duration`, `distributors_enabled`).
- Rendered as a toggle in **Setup → general settings** (NOT the Experimental
  tab — this is a benign transparency preference, not risky behavior).
- Toggle label + description localized in all 8 languages.

### 2. Reason token

- New constant `SKIP_REASON_NO_DEMAND = "no_demand"` in `const.py`.
- The frontend run-log row already localizes a `skipped` entry's `detail` via
  `panels.zones.outlook.checks.<reason>`
  (`view-zone-settings.ts`). Add a new key `no_demand` to the
  `panels.zones.outlook.checks` block in all 8 languages (e.g. EN "No water
  demand", DE "Kein Bedarf"). No collision — the block currently has
  `precipitation, days_between, rain_sensor, freeze, paused, soil_moisture`.
- The result chip reuses the existing `panels.zones.history.results.skipped`
  label — no new result value.

### 3. Normal zones (`irrigation.py`)

Principle: for each scheduled run that gets **past the pause / rain-delay
gate**, every targeted, automatic-eligible, non-member zone that is NOT watered
**only because it has no demand** gets one `no_demand` entry.

- "No demand" = classic gate: `duration <= 0` OR `bucket >= bucket_threshold`.
  Under the experimental live-estimate gate, "no demand" instead means the zone
  was dropped by `_apply_live_durations` (no live deficit) — i.e. the same set
  that today causes the silent early-returns.
- **Mutual exclusion (no double entries):** zones skipped for pause, rain delay,
  or soil-moisture keep their existing reason and are NOT additionally logged as
  `no_demand`. Because the pause/rain-delay path logs `paused` for *all*
  targeted zones and returns before watering, `no_demand` is only recorded on
  the non-paused path; soil-vetoed zones were "due" and are excluded from the
  no-demand set by definition.
- **De-duplication:** skip appending a `no_demand` entry for a zone if that
  zone's most recent run-log entry is already `no_demand` on the same calendar
  day (guards against multiple schedules/day producing repeats).
- Gated entirely behind `config.log_no_demand`. When off, the code path is a
  no-op and behavior is byte-identical to today.

### 4. Distributor member zones (`distributor.py`)

Analogous: when a cycle runs, a member that is not watered **only because it has
no demand** (not-due, and neither paused nor soil-vetoed) gets one `no_demand`
entry, with the same dedup rule. The mechanical skip-pulse that advances the
ring is unchanged — this only adds the history entry. Also gated behind
`config.log_no_demand`.

### 5. Edge cases

- **Nothing due at all** (today's `if not zones_to_irrigate: return`): each
  targeted eligible no-demand zone still gets its entry before returning.
- **Disabled zones**: never logged (they are not automatic-eligible).
- **Manual runs**: bypass the scheduler entirely; no `no_demand` logging (manual
  runs are explicit user intent, not a demand evaluation).
- **50-entry cap**: `no_demand` entries share the existing `RUN_LOG_MAX_ENTRIES`
  cap. This is the reason the feature is opt-in: a user who wants only real-run
  history leaves it off. Dedup keeps it to ~1/zone/day when on.

## Testing (TDD)

Backend (`tests/`):
- No-demand zone with toggle ON → one `no_demand` run-log entry.
- Same zone with toggle OFF → no entry (byte-identical to today).
- Paused run + no-demand zone → only `paused`, no duplicate `no_demand`.
- Soil-veto zone (due but wet) → only `soil_moisture`, never `no_demand`.
- Second scheduled run same day → dedup, still one `no_demand` entry.
- "Nothing due" early-return path → entries still written for eligible zones.
- Distributor member, not due, toggle ON → one `no_demand` entry; OFF → none.
- Migration: pre-migration config loads with `log_no_demand == False`.

Frontend (`vitest`):
- A `skipped` / `no_demand` run-log row renders with the localized label.
- Setup toggle reflects and updates `config.log_no_demand`.

## Upstream / release framing

- Additive, opt-in, no distributor special-casing → clean feature PR candidate
  for JustChr upstream.
- **Process (per user, 2026-07-11):**
  1. Develop on the `gardena` dev branch (established flow), TDD + code review.
  2. **Merge into `production` first** and cut a new production release on the
     Eifel-Joe fork.
  3. **Prepare** a clean PR branch `feature/log-no-demand-skips` extracted from
     `upstream/master` — but do **NOT** open the PR to JustChr yet (user will
     decide later).
