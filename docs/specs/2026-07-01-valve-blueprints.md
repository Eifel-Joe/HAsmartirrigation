# Valve Actuation Blueprints + Service-Mode Script Picker

**Date:** 2026-07-01
**Status:** Design — awaiting approval
**Supersedes:** the native MQTT watering mode from
`2026-06-30-self-closing-valve-mode.md` (that mode is removed here).

## Problem

The native MQTT watering mode exposed raw config fields (topic, JSON key,
open/close value). Two issues surfaced in real use:

1. **MQTT payloads are not standardized.** Zigbee2MQTT payloads depend on the
   device converter. The two valves on the reference system prove the range:
   - **Tuya dual-valve** (`Wasser Beet`): two *flat* publishes —
     `{"countdown_l1": N}` then `{"valve_l1": "on"}`; duration in **minutes**.
   - **SONOFF valve** (`Wasser hinten`): one *nested* publish —
     `{"cyclic_timed_irrigation": {"current_count": 0, "total_number": 1,
     "irrigation_duration": N, "irrigation_interval": 0}}`; duration in
     **seconds**.
   The flat-`{key: value}` field model could not even represent the SONOFF's
   nested structure. No finite field set generalizes this.
2. **ZHA users have no MQTT at all** — their valves are HA entities.

## Decision

Remove the native MQTT mode. Ship **self-closing script blueprints** that
encode each device's exact payload/actuation and only ask the user for the
topic/entity. Blueprints are the HA-native way to distribute reusable,
UI-instantiated scripts. The user instantiates a blueprint, then points a
zone's **service** watering mode at the generated script.

The `service` watering mode is the universal abstraction: the same mechanism
drives Z2M, ZHA, and anything else, because the device specifics live in the
script (blueprint), not in Smart Irrigation.

## Scope

In:
1. Remove the native MQTT watering mode (backend + frontend + tests + store).
2. Three self-closing script blueprints, bundled in the integration and
   auto-installed on setup.
3. Service-mode UI: pick the run/stop script from a dropdown (entity picker,
   `domain: script`) instead of free-text.
4. Default `duration_field` to `duration` so shipped blueprints work with
   minimal config.
5. README documentation section.

Out (non-goals): device auto-detection; covering every valve model; updating
an already-installed blueprint the user may have edited (copy-if-missing only).

## Design

### 1. Remove the native MQTT mode

- `const.py`: drop `WATERING_MODE_MQTT` and the `ZONE_MQTT_*` keys.
- `store.py`: drop the `mqtt_*` fields from `ZoneEntry`. Zone loading must
  tolerate a stored dict that still contains `mqtt_*` keys (filter unknown
  keys on construct). Bump `STORAGE_VERSION` to 10 with a migration that, for
  each zone, maps a stray `watering_mode == "mqtt"` to `"classic"` (safest —
  no actuation surprise) and drops any `mqtt_*` keys.
- `self_closing.py`: remove `_sc_mqtt_open/_sc_mqtt_stop/_sc_mqtt_publish`, the
  mqtt branch in `_sc_dispatch_open`, the `WATERING_MODE_MQTT` arm of
  `_sc_is_self_closing`, and the mqtt branch of `async_stop_self_closing`.
- Frontend: remove the `mqtt` `<option>`, the mqtt field block, the
  `ZONE_MQTT_*` consts (`const.ts`), the `mqtt_*` type fields (`types.ts`),
  and the mqtt `en.json` keys (label + help).
- Tests: remove the 4 mqtt unit tests and the mqtt store-field test.

`service` mode (run_service / duration_field / duration_unit / stop_service)
is unchanged and remains the sole self-closing mode.

### 2. Self-closing script blueprints

Bundled at `custom_components/smart_irrigation/blueprints/script/`:
`tuya_z2m_valve.yaml`, `sonoff_z2m_valve.yaml`, `entity_valve.yaml`.

Common contract for all three:
- `domain: script`, `mode: single`.
- A `duration` field, passed by Smart Irrigation, **already converted to the
  zone's configured unit** (`_sc_service_open` sends `{duration_field: value,
  zone_id, zone_name}`). The blueprint inserts the value verbatim — no
  conversion. The per-device unit is documented (Tuya → Minutes, SONOFF →
  Seconds) and set on the zone's `duration_unit`.
- `duration > 0` → **open**; `duration <= 0` (the stop call passes no
  `duration`) → **close**. One script therefore serves as both `run_service`
  and (optional) `stop_service`.

**Blueprint A — Tuya Zigbee2MQTT** (from `Wasser Beet`):
- Inputs: `mqtt_topic` (text); advanced with defaults: `countdown_key`
  (`countdown_l1`), `valve_key` (`valve_l1`), `open_value` (`on`),
  `close_value` (`off`).
- Open: publish `{countdown_key: duration}` then `{valve_key: open_value}`.
- Close: publish `{valve_key: close_value}`.
- Reference YAML:

```yaml
blueprint:
  name: "Smart Irrigation: Self-closing valve (Tuya Zigbee2MQTT)"
  domain: script
  input:
    mqtt_topic: { name: MQTT topic, selector: { text: {} } }
    countdown_key: { name: Countdown JSON key, default: countdown_l1, selector: { text: {} } }
    valve_key: { name: Valve on/off JSON key, default: valve_l1, selector: { text: {} } }
    open_value: { name: Open value, default: "on", selector: { text: {} } }
    close_value: { name: Close value, default: "off", selector: { text: {} } }
mode: single
fields:
  duration: { name: Duration, default: 0, selector: { number: { min: 0, max: 100000 } } }
sequence:
  - variables:
      topic: !input mqtt_topic
      ckey: !input countdown_key
      vkey: !input valve_key
      oval: !input open_value
      cval: !input close_value
      dur: "{{ duration | int(0) }}"
  - choose:
      - conditions: "{{ dur > 0 }}"
        sequence:
          - { action: mqtt.publish, data: { topic: "{{ topic }}", payload: "{{ {ckey: dur} | to_json }}" } }
          - { action: mqtt.publish, data: { topic: "{{ topic }}", payload: "{{ {vkey: oval} | to_json }}" } }
    default:
      - { action: mqtt.publish, data: { topic: "{{ topic }}", payload: "{{ {vkey: cval} | to_json }}" } }
```

**Blueprint B — SONOFF Zigbee2MQTT** (from `Wasser hinten`):
- Inputs: `mqtt_topic` (text).
- Open: publish `{"cyclic_timed_irrigation": {"current_count": 0,
  "total_number": 1, "irrigation_duration": duration, "irrigation_interval":
  0}}`.
- Close (best-effort): same payload with `irrigation_duration: 0`.
- Caveat: the SONOFF early-stop path is unverified; the valve self-closes on
  its own countdown regardless.

**Blueprint C — Entity-based (ZHA & others):**
- Inputs: `valve_switch` (entity, `domain: [switch, input_boolean]`);
  `countdown_number` (entity, `domain: number`, **required** — it is what
  makes the valve self-close). Without a hardware countdown entity a plain
  switch cannot self-close; the blueprint documents "use Classic mode instead".
- Open: `number.set_value` countdown = `duration`, then
  `homeassistant.turn_on` the valve.
- Close: `homeassistant.turn_off` the valve.
- Caveat: unverified on real ZHA hardware; `valve.*`-domain entities are out of
  scope (the entity picker targets switch/input_boolean).

### 3. Auto-install (copy-on-setup)

There is no first-class "integration ships blueprints" API. Use the
established copy-on-setup pattern:

- In `async_setup` (once, where services register), run an executor job that
  copies each bundled `blueprints/script/*.yaml` into
  `hass.config.path("blueprints", "script", DOMAIN)`
  (`config/blueprints/script/smart_irrigation/`).
- **Copy only if the destination file is missing** — never overwrite, so a
  user's edits are preserved. Create the destination directory if absent.
- Log which blueprints were installed/skipped. Failures are non-fatal
  (log + continue; the integration must still load).

Trade-off: an updated bundled blueprint will not replace a user's existing
copy. Acceptable for now; a version-aware update is future work.

### 4. Service-mode UI: script picker

In the zone editor's `service` block, replace the free-text `run_service` and
`stop_service` `<input>`s with `<ha-entity-picker … .includeDomains=${["script"]}>`
(the same component already used for `linked_entity`). The stored value stays
the `script.<id>` string; `_sc_split_service` already parses `script.<id>` into
`("script", "<id>")` and `hass.services.async_call("script", "<id>", data)`
invokes it. No backend change beyond the default in §5.

### 5. `duration_field` default

Default `ZONE_DURATION_FIELD` to `"duration"` (store + frontend). The shipped
blueprints use a `duration` field, so a zone using a blueprint script needs
only: watering mode = service, run_service = the script, duration_unit =
(Minutes for Tuya / Seconds for SONOFF).

## Config / data flow (per run)

1. Scheduler/manual → `async_run_self_closing(zone)`.
2. `_sc_service_open` calls `script.<x>` with `{duration: <value-in-unit>,
   zone_id, zone_name}`.
3. Blueprint script publishes / actuates; hardware owns the close.
4. Bucket credited optimistically at start; usage counted at run end
   (unchanged from the service mode).
5. Early stop → `stop_service` (same script, no `duration`) → close +
   bucket correction (unchanged).

## Testing strategy

- `test_blueprints.py`: each bundled YAML parses; has a `blueprint:` block with
  `domain: script` and at least one input; the mqtt blueprints reference
  `mqtt.publish`; the entity blueprint references `number.set_value`.
- `test_blueprint_install.py`: copies missing files to a temp dest; skips (does
  not overwrite) an existing file with different content; creates the dest dir;
  a copy error is swallowed and setup still succeeds.
- `test_store_migration`: a stored zone with `watering_mode: "mqtt"` migrates to
  `"classic"`; `mqtt_*` keys are dropped; loading a zone dict with leftover
  `mqtt_*` keys does not raise.
- Remove the mqtt unit/store tests.
- Frontend picker: no unit test (visual verification in the running UI).
- Full backend suite regression-free vs baseline; frontend build + dist
  freshness green.

## Migration / backward-compat

- `STORAGE_VERSION` 9 → 10. Migration: per zone, `watering_mode == "mqtt"` →
  `"classic"`; strip `mqtt_*` keys. `active_valve_runs` records with
  `mode == "mqtt"` are harmless (reconciliation is wall-clock based) and are
  left as-is.
- The reference system has no persisted `mqtt` zone (it was never fully
  configured), so the migration is defensive.

## Open questions

None blocking. Version-aware blueprint updates and `valve.*`-domain support are
explicitly deferred.
