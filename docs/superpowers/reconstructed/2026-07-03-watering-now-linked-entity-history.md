# Initialise _linked_entity for zones without a linked entity

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-03  ·  **PR:** —  ·  **Branch(es):** fix/watering-now-linked-entity
**Commit(s):** 305bc897

## Problem / Context
The per-zone "watering now" binary sensor (`SmartIrrigationZoneWateringNowSensor`) reads `self._linked_entity` in `_resubscribe()`, which runs from `async_added_to_hass`. But `_update_from_zone` only assigned `_linked_entity` inside its change-guard, which is skipped when the value stays `None`. A service / self-closing zone has no linked entity, so the attribute was never set and the sensor raised `AttributeError` on add, failing to register.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Initialise `self._linked_entity = None` in `__init__`, alongside the existing `self._unsub_linked = None`, so the attribute always exists regardless of whether the zone ever assigns a real linked entity. This guarantees `_resubscribe()` can safely read it on add.

## Implementation
`custom_components/smart_irrigation/binary_sensor.py`: added `self._linked_entity = None` in the constructor (with an inline comment explaining that `_update_from_zone` only sets it inside its change-guard). `tests/test_binary_sensor.py`: added a regression test `test_watering_now_sensor_without_linked_entity_does_not_crash` that builds the sensor for a zone with no linked entity, asserts `_linked_entity is None`, and calls `_resubscribe()` to confirm it no longer raises.

## Evidence
- PR: —
- Commit(s): 305bc897 — fix(binary_sensor): initialise _linked_entity for zones without a linked entity
- Tests: tests/test_binary_sensor.py
- Memory: —

## Related
—
