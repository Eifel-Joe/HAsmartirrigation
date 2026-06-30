# Self-Closing Valve Mode — Design Spec

**Status:** Draft for review
**Date:** 2026-06-30
**Author:** Eifel-Joe (with Claude)
**Component:** `custom_components/smart_irrigation`

---

## 1. Problem & motivation

HASI actuates a zone valve by **opening it, sleeping the computed run duration
inside Home Assistant, then closing it** (`irrigation.py`: `turn_on` →
`_sleep_or_stopped` → `turn_off`, e.g. lines 300/480→544 and 875→895). The
"close" command therefore depends on Home Assistant staying alive for the whole
run.

If HA restarts or crashes mid-run, the `turn_off` never fires and the valve
**stays open → continuous irrigation / flooding** until HA recovers and someone
notices. On a single unattended productive instance this is a real safety gap.

Many valves can close themselves: they accept a **countdown / auto-off duration**
and shut independently of HA (e.g. Tuya dual-channel Zigbee water valves expose
`number.<valve>_countdown_l1` in minutes plus `valve.<valve>_valve_l1` /
`switch.<valve>_valve_l1`, and a `sensor.<valve>_valve_status_l1`). Today a user
who wants this must bypass HASI's actuation entirely and hand-build a script +
automation that pushes the duration to the valve. This feature brings that
capability **into HASI**, opt-in per zone, with the classic behaviour untouched.

## 2. Goals

- Per-zone, opt-in actuation that **delegates the close to self-closing
  hardware**, so an HA outage mid-run cannot cause continuous irrigation.
- Cover the realistic hardware "dialects" without HASI hard-coding vendors.
- Keep the model (bucket / live deficit) correct even if HA dies mid-run.
- Zero behavioural change for existing users (classic mode is the default and
  bit-identical to today).

## 3. Non-goals (explicit scope boundaries)

- **Pump recovery logic** (power-cycle, upstream-socket fallback, abort-on-fault)
  stays in the user's automations or behind the master hooks — HASI only fires
  `master_on` / `master_off`.
- Soil-moisture vetoes, cistern/rainwater accounting and notifications remain the
  user's automation layer.
- The master (pump) is **not** made crash-safe by HASI (a pump cannot self-close
  — see §7); this is documented, not solved here.

## 4. Concepts & data model

### 4.1 Per-zone watering mode (adapter)

A new per-zone setting `ZONE_WATERING_MODE` selects how the zone is actuated:

| Mode | Mechanism | Close on HA crash |
|------|-----------|-------------------|
| `classic` *(default)* | open `linked_entity` → sleep duration → close | ❌ stays open |
| `service` | call a configured service/script with the duration | ✅ valve self-closes |
| `duration_entity` | set a countdown `number`/`select` → open a `valve`/`switch` | ✅ |
| `mqtt` | publish a countdown payload → publish an open payload | ✅ |

`classic` continues to use the existing `ZONE_LINKED_ENTITY` (and `ZONE_FLOW_SENSOR`)
unchanged. The other three are "self-closing" adapters and share:

- `ZONE_DURATION_UNIT` — `seconds` (default) or `minutes`. HASI computes in
  seconds and converts on hand-off.
- `ZONE_STATUS_ENTITY` *(optional)* — an entity whose state confirms the valve
  actually opened (e.g. `sensor.<valve>_valve_status_l1` = `idle`/running), used
  for best-effort verification.

### 4.2 Adapter-specific config

**`service`** (most general):
- `run_service` — `domain.service` (e.g. `script.irrigation_beet`).
- `duration_field` — the data key the duration is passed under (e.g. `dauer`).
- `run_data` *(optional)* — extra static keyword data merged into the call;
  `zone_id` / `zone_name` are always added.
- `stop_service` *(optional)* — `domain.service` + optional `stop_data`, called on
  early stop.

> **Phasing note:** Phase 1 ships the literal `duration_field` + `run_data` form
> above (fully covers `script.irrigation_beet(dauer=<minutes>)`). Free-form Jinja
> templating of `run_data` values (injecting `{{ duration_minutes }}` etc.) is a
> Phase-2 refinement.

**`duration_entity`** (native two-entity):
- `duration_entity` — a `number` or `select` entity (the countdown).
- `open_entity` — a `valve` or `switch` entity. Open/close is dispatched by the
  entity's domain (`valve.open_valve`/`valve.close_valve`, or
  `switch.turn_on`/`switch.turn_off`).
- The countdown value is written with `number.set_value` / `select.select_option`
  using the duration in `duration_unit`, **before** opening.

**`mqtt`** (Zigbee2MQTT / raw):
- `topic` — e.g. `zigbee2mqtt/Wasser Beet/set`.
- `countdown_payload` — template, e.g. `{"countdown_l1": {{ duration_minutes }}}`.
- `open_payload` — template, e.g. `{"valve_l1": "on"}`.
- `stop_payload` *(optional)* — e.g. `{"valve_l1": "off"}`.
- `qos` (default 0), `retain` (default false). Published countdown first, then
  open.

A multi-channel device (e.g. Tuya l1/l2) is modelled as **two independent zones**,
each pointing at its own entities/payloads — no special multi-channel logic.

### 4.3 Active-run record (persisted)

Self-closing modes do **not** sleep the duration. HASI keeps a per-zone active-run
record, persisted in the store so it survives a restart — modelled on altmen's
`active_valve_runs` list (prior art, §14):

```
active_run = {
  zone_id,            # int
  entity_id,          # the actuated entity/service target (for stop/verify)
  started,            # ISO-8601 UTC timestamp
  planned_seconds,    # target run duration
  planned_mm,         # water the run is intended to deliver
  mode,               # service | duration_entity | mqtt
  credited,           # bool — bucket already credited optimistically (§5)
}
```

Stored as a list on the store config (e.g. `CONF_ACTIVE_VALVE_RUNS`), loaded on
`async_setup_entry` for reconciliation (§6). `started` is wall-clock **UTC** so a
reboot can compute true elapsed time including downtime.

### 4.4 Master (instance-level)

Optional instance-level config:
- `master_on_service` / `master_off_service` — `domain.service` (+ optional data),
  **or** `master_entity` (a switch/valve toggled on/off).
- `master_settle_seconds` — delay after `master_on` before the first zone fires
  (pressure build-up), default 10 s.

## 5. Actuation flow (self-closing modes)

1. HASI computes the run duration as today (from the deficit / live deficit), in
   seconds → `planned_seconds`, with the corresponding water amount `planned_mm`.
2. Convert to `duration_unit`. If `minutes` and `planned_seconds < 60`, round up
   to 1 minute and log a granularity warning (sub-minute precision is lost on
   minute-granular hardware).
3. Dispatch the adapter's **open action**. Open/close are domain-aware (mirroring
   altmen's `_valve_services`): a `valve.*` entity uses `valve.open_valve` /
   `valve.close_valve`, anything else uses `turn_on` / `turn_off`; the `service`
   and `mqtt` adapters use their configured calls / payloads.
4. **Confirm the open before crediting:** poll the optional `status_entity` (or
   the `open_entity` state) for up to ~8 s, accepting `on` / `open` / `opening`.
   If it never confirms, abort — do not credit, fire a `zone_problem` event
   (§5.1), do not persist an active run. (This closes the optimistic-over-credit
   risk in §12 — adopted from altmen.)
5. **Credit the bucket optimistically, now** (the valve owns the close, so assume
   completion): credit `planned_mm` via the existing run-credit math
   (`volume_l = throughput * seconds / 60 / multiplier`, clamped to the zone's
   `maximum_duration`), write a run-log entry tagged `self_closing` + `optimistic`,
   set `watering_now = on`, and persist the active-run record with `credited = true`.
6. Schedule a **lightweight cleanup timer** at `started + planned_seconds` that
   only flips `watering_now = off`, fires `irrigation_finished` (§5.1) and removes
   the active-run record. It does **not** close the valve — the hardware did.

### 5.1 Events

HASI fires the same events as altmen's direct valve control, for ecosystem
consistency so external automations (notifications, logging) work unchanged:
- `smart_irrigation_irrigation_started` — `{ sequencing, zones: [{zone_id, zone,
  seconds}] }`, when a self-closing cycle begins.
- `smart_irrigation_irrigation_finished` — `{ zones: [{zone_id, zone, seconds,
  volume_l, bucket}], problems: [...] }`, at cleanup / finalise.
- `smart_irrigation_zone_problem` — `{ zone_id, zone, entity_id, reason }`, when
  the open cannot be confirmed (§5 step 4).

If HA dies between steps 4 and 5: the valve still closes itself, and the bucket
is already correct, so the next cycle does **not** double-water. Only the
cosmetic `watering_now` stays briefly stale until restart reconciliation.

## 6. Stop, correction & restart reconciliation

**Manual stop** (`async_stop_zone` / stop button / stop-all):
- Dispatch the adapter's **stop action** (`stop_service` / close `open_entity` /
  `stop_payload` / classic `turn_off`). If a self-closing zone has no stop config,
  stop is **best-effort**: HASI cannot close the valve, logs a warning, but still
  corrects accounting.
- Compute `delivered = min(elapsed / planned_seconds, 1)` and **correct the
  bucket** by removing the un-delivered portion `(1 - delivered) * planned_mm`
  from the optimistic credit. Finalise the run-log as `stopped`.

**Restart reconciliation** (on `async_setup_entry`, modelled on altmen's
`async_resume_valve_runs`): load persisted active-run records; per record compute
`elapsed = utcnow() - started` (wall-clock, so downtime counts), then:
- `elapsed >= planned_seconds` → the self-closing hardware has already closed;
  finalise: clear `watering_now`, fire `irrigation_finished`, remove the record.
- `elapsed < planned_seconds` → the hardware countdown is still running; do **NOT**
  re-open (key divergence from altmen, whose software-timed valve would otherwise
  stay open). Just reschedule the cleanup timer for the remainder.
- The bucket is **not** re-credited on restart because `credited` is already true
  (optimistic credit at fire time); the flag prevents double-crediting.

## 7. Master flow

- A watering **cycle** begins when the first zone of a run fires. HASI calls
  `master_on`, waits `master_settle_seconds`, then dispatches the zones.
- Cycle end = `max(zone.start_ts + zone.planned_seconds)` across the cycle's
  zones. HASI schedules `master_off` at that time.
- Applies to classic zones too (master on before, off after).
- **Crash exposure (documented):** if HA dies after `master_on`, the master stays
  on. A pump is not self-closing, so this can dead-head / run dry. HASI cannot
  prevent this alone; the master device must carry its own safety (dry-run
  protection, a self-closing relay on the pump supply, or a max-on timer on the
  upstream socket). This is surfaced in the docs and the master config UI.

## 8. Backward compatibility

- `watering_mode` defaults to `classic`; all new attributes are additive with
  empty/neutral defaults.
- `STORAGE_VERSION` bumps `8 → 9`; the migration sets `watering_mode = classic`
  for every existing zone and leaves all other behaviour identical.
- A regression test pins that a classic zone's actuation is unchanged.

## 9. Affected code

- `const.py` — new `ZONE_WATERING_MODE`, adapter config keys, `ZONE_DURATION_UNIT`,
  `ZONE_STATUS_ENTITY`, master keys, defaults.
- `store.py` — `ZoneEntry` attributes + instance master config; `STORAGE_VERSION`
  8→9 + migration; persist the active-run record.
- `irrigation.py` — actuation dispatch by mode (new self-closing paths alongside
  the classic open/sleep/close), optimistic credit, stop + correction, restart
  reconciliation, master on/off sequencing.
- bucket/credit path (`calculation.py` / existing run-credit helpers) — apply the
  credit at fire time and the correction on early stop (reusing the existing
  post-run credit logic, not a new bucket formula).
- `sensor.py` — `watering_now` reflects the active-run record in self-closing
  modes.
- Frontend zone settings — `watering_mode` selector with conditional fields per
  adapter; instance master settings.
- Tests — see §11.

## 10. Adapter examples (the author's setup)

- **Beet (Tuya dual-valve), `duration_entity`:** `duration_entity =
  number.wasser_beet_countdown_l1` (`minutes`), `open_entity =
  valve.wasser_beet_valve_l1`, `status_entity =
  sensor.wasser_beet_valve_status_l1`. No script needed.
- **Beet, `mqtt` (alternative):** `topic = zigbee2mqtt/Wasser Beet/set`,
  `countdown_payload = {"countdown_l1": {{ duration_minutes }}}`, `open_payload =
  {"valve_l1": "on"}`, `stop_payload = {"valve_l1": "off"}`.
- **Beet, `service` (current approach):** `run_service = script.irrigation_beet`,
  `run_data = { "dauer": "{{ duration_minutes }}" }`.

## 11. Testing strategy

New `tests/test_self_closing_valve.py` (+ additions to `test_store.py` /
`test_init.py`):
- **Dispatch:** each adapter fires the correct service/entity/MQTT calls with the
  converted duration (mock `hass.services.async_call` / `mqtt.async_publish`).
- **Optimistic credit:** firing a self-closing run credits the bucket and writes
  an `optimistic` run-log entry immediately, without sleeping.
- **Stop correction:** stopping at 40 % elapsed leaves 40 % of `planned_mm`
  credited; the stop action is dispatched; no-stop-config path warns but still
  corrects.
- **Restart reconciliation:** a persisted active-run with past end is marked
  completed; a future end reschedules cleanup.
- **Granularity:** `minutes` unit rounds a 15 s run up to 1 min and warns.
- **Migration:** a v8 store migrates to v9 with `watering_mode = classic`.
- **Classic regression:** a classic zone's actuation path is unchanged.
- **Master:** `master_on` fires before the first zone with the settle delay;
  `master_off` fires after the last zone's planned end.

## 12. Risks & open points

- **Verification** is best-effort: in `service`/`mqtt` modes there may be no
  reliable "valve opened" signal; the optional `status_entity` mitigates this
  where available.
- **MQTT template safety:** payload templates are user-authored — validate they
  render to valid JSON before publishing; surface render errors instead of
  silently failing.
- **Master crash exposure** (§7) — accepted and documented, not solved.
- **Granularity loss** on minute-granular hardware for sub-minute runs.
- **Optimistic over-credit** is mitigated by the confirm-open step (§5 step 4):
  the credit happens only after the valve confirms open. Without a `status_entity`
  (and for `service`/`mqtt` adapters with no observable state) a silently-failed
  open is still indistinguishable from success — documented limitation, same as a
  classic run whose switch silently fails; configuring a `status_entity` removes it.

## 13. Phasing (each phase = an independent, shippable PR)

- **Phase 1 (MVP — delivers the crash-safety):** the `watering_mode` framework +
  the `service` adapter + optimistic credit + stop/correction + restart
  reconciliation + migration + config. Covers the author's existing script path.
- **Phase 2:** the `duration_entity` and `mqtt` adapters (additive).
- **Phase 3:** the master switch/valve.

Each phase gets its own implementation plan (`docs/plans/…`).

## 14. Prior art & alignment — altmen `direct_valve_control`

altmen/master (the canonical repo) already ships an adjacent, **global** feature
`direct_valve_control_enabled`, implemented in `valve_runner.py`:
- HASI opens the valve (domain-aware `_valve_services`), **software-times** the run
  (`asyncio.sleep`), then closes it; persists in-flight runs (`CONF_ACTIVE_VALVE_RUNS`:
  zone_id, entity_id, started, duration) and on reboot **resumes** by re-opening
  partial runs and crediting the full target duration (clamped to `maximum_duration`).
- Fires `irrigation_started` / `irrigation_finished` / `zone_problem` events; the
  legacy start event fires regardless, so an **external executor** (automation) can
  do the actuation when DVC is off.

This spec **borrows** altmen's persisted-run structure, wall-clock elapsed
calculation, crediting math, confirm-open check, and event surface. It **diverges**
on the close: altmen's reboot-resilience keeps the valve open while HA is down (a
hard crash that never recovers still floods), whereas this feature delegates the
close to **self-closing hardware** (a countdown), so the valve shuts regardless of
whether HA returns — and credits optimistically at start.

On **JustChr** (this branch) none of altmen's machinery exists, so it is implemented
natively. If this is ever targeted at **altmenorg**, it should **extend**
`direct_valve_control` (add the self-closing adapters + optimistic credit +
skip-re-open resume) rather than duplicate it — and the `service`/`mqtt` adapters
map cleanly onto altmen's existing "optional external executor + start event" path.
