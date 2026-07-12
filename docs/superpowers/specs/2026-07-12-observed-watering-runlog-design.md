# Observed-watering run-history entry — Design

**Date:** 2026-07-12
**Status:** Approved (design), pending spec review
**Type:** Feature (additive) — companion to the opt-in observed-watering feature

## Problem

Observed watering (`observed_watering_enabled`) credits a zone's bucket when its
valve runs outside Smart Irrigation, via `_credit_observed_watering`
(observed_watering.py): it updates `ZONE_BUCKET` + `ZONE_LAST_IRRIGATION` and
fires `config_updated` — but writes **no run-history entry**.

Consequences (confirmed on the user's production system 2026-07-11):
- The external watering is **invisible** in the zone's Bewässerungsverlauf (run
  history) — indistinguishable from "nothing happened".
- The credit is **transient**: it lives only in the bucket, so anything that
  later changes the bucket erases the evidence. Real case: a legacy dashboard
  script called `smart_irrigation.reset_bucket` 5 s after the valve closed, so
  the observed credit (+2.4 mm) was zeroed and the run left no trace.

## Goal

When observed watering credits a zone (an external run of its `linked_entity`
**or** `observed_entity`), also write **one run-history entry** — visible and
**persistent** (it survives later bucket changes), for **both** service/
self-closing and linked-entity zones.

## Design

All changes hang off the single shared crediting point,
`_credit_observed_watering`, which already runs for both zone types.

### 1. New run result token
- `RUN_RESULT_OBSERVED = "observed"` in `const.py` — a 5th result alongside
  `completed` / `partial` / `failed` / `skipped`. Distinct so the history row
  visibly marks an external run (not an SI-driven one).

### 2. Backend (`observed_watering.py::_credit_observed_watering`)
After the existing bucket credit + `last_irrigation` update, additionally:
```python
await self._record_run(
    zone_id,
    result=const.RUN_RESULT_OBSERVED,
    volume_l=volume_l,
    actual_s=round(seconds),
    trigger="observed",
    add_to_total=True,
)
```
- `volume_l` and `seconds` are already computed in the method.
- `add_to_total=True` → the estimated volume (run time × throughput) is added to
  the zone's `water_used_total`, so the usage sensor reflects **all** water
  delivered to the zone (SI + external) — per the design decision.
- `planned_s` is left unset/`None` (an external run was never "planned" by SI);
  `actual_s` carries the observed duration.
- Bucket + `last_irrigation` continue to be set by the existing update; the two
  `async_update_zone` writes are independent and non-conflicting (`_record_run`
  only touches `run_log` + `water_used_total`). The plan may merge them if
  cleaner, but correctness does not require it.
- No opt-in gate of its own — this is part of observed watering (already behind
  `observed_watering_enabled`); when the feature is off, nothing is credited or
  logged, so behaviour is unchanged.

### 3. Frontend
- Add `observed` to `panels.zones.history.results` in all 8 languages
  (EN "Observed", DE "Beobachtet"; translate es/fr/it/nl/no/sk in the register of
  the neighbouring result labels).
- The run-log row already renders `panels.zones.history.results.<result>` as a
  chip and shows the volume column, so an observed entry renders as:
  timestamp · **Observed** chip · volume (L) · detail (empty). Add a
  `.history-observed` chip style (a neutral/positive colour; if omitted it falls
  back to the base chip style — verify the row still renders cleanly).

### 4. Edge cases
- The estimate needs the zone's `size` + `throughput`; `_credit_observed_watering`
  already returns early (no credit) when either is missing — in that case there
  is likewise no run-log entry (nothing was credited). Unchanged.
- Run-log is bounded (`RUN_LOG_MAX_ENTRIES`); observed entries share that cap
  like any run — acceptable (external runs are discrete events, no dedup needed).

## Testing (TDD)
- Backend: `_credit_observed_watering` appends a `run_log` entry with
  `result == "observed"`, the estimated `volume_l`, and increments
  `water_used_total` by that volume. Existing observed-watering tests (bucket
  credit / cap / size+throughput guard / suppression) stay green.
- Frontend: a run-log row with `result: "observed"` renders the localized
  "Observed"/"Beobachtet" chip (if a render harness is available; else verified
  by build + live test, per the existing run-history convention).

## Overarching
- Additive; no new config, no STORAGE_VERSION bump. Off (feature disabled) =
  today's behaviour.
- **Upstream:** extends JustChr's own observed-watering feature → clean PR
  candidate (bundles naturally with the service-zone extension, or stands alone).
- **Process:** develop on `local/observed-runlog` (from `production` v2026.07.14);
  ship + release decision after the phase; design docs archived per the standing
  archive-branch rule.
