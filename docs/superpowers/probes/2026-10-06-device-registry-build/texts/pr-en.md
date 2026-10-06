## Problem

Two device-registry calls are deprecated and go away in Home Assistant 2027.8.0:

1. **`via_device`** in the `device_info` of the zone and distributor devices (`entity.py`), which hangs each of those
   devices off the hub. HA 2026.9 reports at startup: "calls `device_registry.async_get_or_create` with a deprecated
   `via_device` parameter; use `via_device_id` instead … This will stop working in Home Assistant 2027.8.0".
2. **`device_registry.async_get_device(identifiers=…)`** when a zone (`async_remove_entity`) or a distributor (the
   delete branch of `async_upsert_distributor`) is deleted. HA 2026.9 reports: "deprecated because device identifiers
   and connections are no longer unique across config entries; use `async_get_device_by_identifier` …".

A plain swap doesn't work, because the integration is meant to run from HA 2025.5 on (`hacs.json`, the
`test-ha-floor` CI job):

| HA | `via_device_id` | `async_get_device_by_identifier` |
|---|---|---|
| 2025.5 – 2026.7 (floor; main CI job 2026.2.3) | doesn't exist: `async_get_or_create` has a fixed signature, an unknown parameter would be a `TypeError`, and every zone and distributor entity would be dropped | doesn't exist |
| 2026.8 | new (next to `via_device`) | new |
| 2026.9 | the only named parameter; `via_device` only through `**kwargs`, reported | replaces the reported `async_get_device` |

## Fix

- `entity.hub_link_for` asks the registry's **class** whether `async_get_or_create` takes a `via_device_id`
  parameter — detecting rather than comparing versions, as `migrate_domain.all_registry_devices` does. If it does, the
  parent link is `{"via_device_id": <the hub's registry id>}`, otherwise, as before, `{"via_device": (DOMAIN,
  <identifier>)}`. It asks the class because a `Mock()` says yes to any attribute on the instance, and the existing
  delete tests build the registry as a `Mock()`.
- `async_setup_entry` keeps the return value of the existing hub registration and records the answer once in
  `hass.data[DOMAIN]["hub_link"]` — before the platforms are set up, and afresh on every setup, since `hass.data`
  survives a reload. `zone_device_info` and `distributor_device_info` carry `**hub_link(hass)`; without a record the
  old form stays.
- `entity.find_device` uses `async_get_device_by_identifier(identifier, config_entry_id)` where the class has it,
  otherwise `async_get_device` as before. Both delete paths go through it, with the coordinator's config entry id. That
  id is read tolerantly (the old lookup doesn't need it, and test hosts built without `__init__` have none); a miss
  returns `None` and never falls back to the deprecated call.
- **Python 3.14:** Since 2026.6, HA's `device_registry.py` no longer has `from __future__ import annotations`. On
  Python 3.14, which HA has required since 2026.3, `inspect.signature` then evaluates the annotations; a name the
  registry imports only for type checking would raise `NameError` and stop the setup. So any failure to read the
  signature leaves the identifier form in place. Today this is only a precaution: in 2026.6 through 2026.9.4 every name
  in the signature is bound at runtime.
- Existing devices keep the same hub as their parent (the same id; HA rewrites nothing): no migration, and going back
  to an older version has no consequences. `hub_link` now shows up in the diagnostics.
- In passing: the comment above the distributor delete branch pointed at an `async_remove_zone` function that doesn't
  exist; it now names `async_remove_entity`.

**Alternative**, if you prefer: raise the floor to 2026.8 or later and drop the switches. Then these go: both switches
and `import inspect`; the tolerant entry id on both delete paths (it becomes a plain `self.entry.entry_id`); the
fallback in `hub_link` together with its two existing pins
(`test_sensor.py::TestSmartIrrigationZoneEntity::test_device_info`,
`test_distributor_entities.py::test_distributor_device_info_identifiers_and_via_device`); the old-shape tests; and the
three delete tests with a `Mock()` registry that bind `async_get_device` by name move along. Let me know and I'll
rework it that way.

## Testing

- New file `tests/test_device_registry_compat.py`, 22 tests. CI runs on 2026.2.3 and 2025.5.0 and doesn't know the new
  calls, so stand-in registries cover the three shapes (before 2026.8, 2026.8.0 itself, from 2026.9). Plus a setup
  test against the installed registry (the old path on real HA in both CI jobs), a hit, a miss and the old shape
  without an entry on both delete paths, the order before the platforms are set up, the overwrite after a reload, and
  the unreadable signature. Existing tests unchanged.
- Full suite locally (Python 3.12, HA 2024.12.5): unchanged apart from the new tests. (Locally the three new setup
  tests, like the existing coordinator tests, end with a "Lingering timer" at teardown — a quirk of this Windows
  environment.) black and ruff clean.
- 36 mutations of the changed lines, all killed by the new file.
- Live on a test instance with HA 2026.9.4: before, HA reported both deprecations (at startup, and when a zone and a
  distributor were deleted). After: none; all existing zone and distributor devices hang off the hub with the same id,
  no entity was dropped, `hub_link` is in the diagnostics with the hub's registry id, and a newly created zone and a new
  distributor hang off the hub and disappear together with their device when deleted — also after a reload.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
