# Distributor device + entities — Design

**Date:** 2026-07-05
**Feature:** Expose each Gardena distributor as a Home Assistant *device* (analogous to the existing per-zone devices) with entities that surface its outlet→zone mapping, position, commissioning/active state, and a test-run action.

## Goal

Give every configured distributor a first-class HA device so a user sees, without opening the Smart Irrigation panel:
- which zone hangs on each used outlet,
- which outlet the ring is currently on,
- whether the distributor is commissioned (armed) and whether a cycle is running,
- and can trigger the commissioning test-run from a button.

## Context (verified from source, 2026-07-05)

- Platforms forwarded in `__init__.py` `async_setup_entry`: `[sensor, number, binary_sensor, button, datetime]`.
- Per-zone **device** built by `entity.py:zone_device_info()` → identifiers `{(DOMAIN, f"{cid}_zone_{zone_id}")}`, `via_device (DOMAIN, cid)` (the hub device). Hub device created in `__init__.py` with identifiers `{(DOMAIN, coordinator.id)}`.
- Entities are **not** `CoordinatorEntity`. They read directly from the store (`store.get_zone(id)` returns an `attr.asdict` dict) and refresh on the dispatcher signal `DOMAIN + "_config_updated"` (fired with a `zone_id`).
- Dynamic per-zone entities are created by dispatcher: `setup_SmartIrrigation_entities()` replays each zone via `DOMAIN + "_register_entity"`; each platform's `async_setup_entry` subscribes and calls `async_add_devices(...)`. Entities tracked in `hass.data[DOMAIN][<bucket>]` keyed by id.
- `_attr_has_entity_name = True` + `_attr_translation_key` → HA composes "<device name> <entity name>"; translations under `entity.<platform>.<key>` in `translations/<lang>.json`. HA supports `_attr_translation_placeholders` for `{placeholder}` substitution in the translated name.
- Distributor data: `store.get_distributor(id)` / `async_get_distributors()` → dicts with `id, name, current_outlet, position_state, commissioning_confirmed, active_cycle, use_master, …`. Member zones carry `distributor_id` + `outlet_number`; outlet assignments are gapless `1..n`.
- Test-run already exists: `coordinator.async_run_distributor_test(distributor)` (requires `position_state == synced`; exempt from the commissioning gate). Service `distributor_test_run` is registered.
- **Gap:** no distributor entity exists yet, and no dispatcher signal carries a *distributor* (only zones). Dynamic **per-outlet** entities (variable count per parent) have no precedent — zones have a fixed entity set.

## Device

One HA device per distributor, parented to the hub:

```python
# entity.py
def distributor_device_info(hass, distributor_id, distributor_name) -> dict:
    cid = coordinator_id(hass)
    return {
        "identifiers": {(const.DOMAIN, f"{cid}_distributor_{distributor_id}")},
        "name": distributor_name,
        "model": "Gardena water distributor",
        "manufacturer": const.MANUFACTURER,
        "via_device": (const.DOMAIN, cid),
    }
```

## Entities (all attach to the distributor device)

`unique_id` scheme mirrors zones: `f"{DOMAIN}_distributor_{distributor_id}_{suffix}"`.

| Entity | Platform | State | Key attributes | translation_key |
|---|---|---|---|---|
| **Zone on outlet N** (one per *used* outlet, dynamic) | `sensor` | assigned zone's `name` (str) | `zone_id`, `outlet_number` | `outlet_zone` + `translation_placeholders={"outlet": str(n)}` |
| **Current outlet** | `sensor` | `current_outlet` (int) | `position_state`, `phase` (from `active_cycle`, else `idle`), `zone_id`/zone name at current outlet | `current_outlet` |
| **Commissioned** | `binary_sensor` | `commissioning_confirmed` (on/off) | — | `commissioned` |
| **Watering now** | `binary_sensor`, device_class `running` | `bool(active_cycle)` — a cycle is in progress | `phase` (watering / pausing), `outlet` | `watering_now` |
| **Test run** | `button` | — (press action) | — | `test_run` |

Notes / decisions:
- **Watering now** is True whenever a cycle is active (`active_cycle` non-empty), including the inter-outlet pause; the `phase` attribute (`watering`/`pausing`) distinguishes flow from pause. This mirrors the "distributor is currently working" intent; a pure inlet-open indicator is available via the `phase` attribute.
- **Current outlet** exposes `position_state` as an attribute so the blocking `uncertain` state is visible without a dedicated entity.
- **Test run** calls `coordinator.async_run_distributor_test(distributor)`. It stays available always; if `position_state != synced` the underlying call no-ops with a log (matching the service). (No per-state disabling — HA buttons don't model that cleanly.)
- **Commissioned** carries no `device_class` (it is a config/armed state, not a HA-standard binary class).

## Wiring (mirror the zone pattern)

Distributor entities live in the **existing** platform files — `sensor.py`, `binary_sensor.py`, `button.py` — because HA groups by entity type, not by feature. No new platform is added to the forward list.

**New dispatcher signals:**
- `DOMAIN + "_distributor_register_entity"` — carries a distributor dict. Fired for each distributor in `setup_SmartIrrigation_entities()` (replay on setup, alongside the zone replay) and when a distributor is created (`async_upsert_distributor` create path).
- `DOMAIN + "_distributor_updated"` — carries a `distributor_id`. Fired whenever a distributor's persisted state changes: `_dist_persist_cycle` (outlet advance / phase), `_dist_clear_cycle`, `_dist_mark_uncertain`, `async_update_distributor`. Distributor entities subscribe and re-read the store on a matching id.

**Member-assignment coupling:** the per-outlet zone sensors depend on *zone* data (a zone's `outlet_number`). When a member zone changes (`async_update_zone` touching `distributor_id`/`outlet_number`/`name`), fire `DOMAIN + "_distributor_updated"` for the affected distributor id(s) so the outlet sensors refresh and reconcile.

## Dynamic reconciliation (the real work)

The set of "Zone on outlet N" sensors must track the distributor's *used* outlets (gapless `1..n`, n = member count).

- On `_distributor_register_entity`: compute used outlets from member zones; create the current-outlet sensor, both binary_sensors, the button (static, once), and one outlet-zone sensor per used outlet. Track created entities in `hass.data[DOMAIN]["distributor_entities"][distributor_id]`.
- On `_distributor_updated` (member change): **reconcile** — add outlet-zone sensors for newly-used outlets; remove sensors for outlets no longer used via `entity_registry.async_remove(entity_id)`, and drop them from the tracker.
- On distributor **deletion**: the `async_upsert_distributor` delete path fires a dedicated `DOMAIN + "_distributor_removed"` signal carrying the `distributor_id`. Its handler removes **all** entities for that distributor's device from the entity registry, drops the tracker bucket, and removes the now-empty device from the device registry.

The reconcile is a pure set-diff over outlet numbers; the entity add uses `async_add_devices`, the remove uses the entity registry — both are established HA APIs.

## i18n

New entity translation keys in **all 8 languages** (`translations/*.json`, keep CRLF-canonical via the Node merge script), under `entity.sensor` / `entity.binary_sensor` / `entity.button`:
- `sensor.outlet_zone` = "Zone on outlet {outlet}" (+ localized), `sensor.current_outlet` = "Current outlet"
- `binary_sensor.commissioned` = "Commissioned", `binary_sensor.watering_now` = "Watering now"
- `button.test_run` = "Test run"

## Testing

- **Unit (pure logic, no hass):** state derivation for each entity from a distributor/zone dict (current outlet, commissioned, watering-now bool + phase attr, outlet-zone name resolution); `distributor_device_info` shape/identifiers; the reconcile set-diff (used-outlets set → entities to add/remove) including the shrink case (zone unassigned → sensor removed) and the grow case.
- **Signal plumbing:** assert `_distributor_updated` is fired on `_dist_persist_cycle` / `async_update_distributor` / member `async_update_zone` (spy the dispatcher).
- **HA wiring** (device grouping, add/remove against a live registry) is verified in the live/click test on 192.168.10.196 — it is not unit-testable without a full hass harness; the reconcile logic that drives it *is* unit-tested.

## Out of scope (YAGNI)

- No per-outlet *button* or *switch* (only the whole-distributor test-run button).
- No configurable device name beyond the distributor's own name.
- No historical/statistics entities.

## Release

Bundle with the H7 rolling-notes master fix into a single pre-release **b8** on the fork (`Eifel-Joe/HAsmartirrigation`, target `feature/gardena-distributor`), for the test system 192.168.10.196. Frontend dist rebuild only if any TS changes (this feature is backend/entity-only — likely no panel change). Version bump ×3, `black --check`, full pytest, `gh release --prerelease`.
