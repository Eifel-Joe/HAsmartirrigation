# Valve Blueprints + Service-Mode Script Picker — Implementation Plan

> **For agentic workers:** execute task-by-task, TDD. Steps use `- [ ]`.

**Goal:** Replace the native MQTT watering mode with three auto-installed
self-closing script blueprints, and make the service-mode run/stop fields a
script dropdown.

**Architecture:** `service` watering mode stays the sole self-closing mode;
device specifics move into shipped script blueprints. Blueprints are bundled in
the package and copied to `config/blueprints/script/smart_irrigation/` on setup.

**Tech stack:** Python (HA custom integration, attr store), Lit/TS frontend,
pytest (local uv venv 3.12 + `_local_socket_unblock`), HA script blueprints.

**Spec:** `docs/specs/2026-07-01-valve-blueprints.md`.

**Local test runner (all backend tasks):**
`PYTHONPATH=<scratch> <uvenv312>/Scripts/python.exe -m pytest <targets> -p _local_socket_unblock -p no:cacheprovider -p no:sugar -o addopts="" --timeout=120`

---

### Task 1: Store migration v9→v10, drop mqtt fields

**Files:**
- Modify: `custom_components/smart_irrigation/store.py`
- Test: `tests/test_store_self_closing.py`, `tests/test_store_migration_*` (new asserts)

- [ ] **Step 1 — failing tests:** stored zone with `watering_mode: "mqtt"` +
  `mqtt_topic: "x"` migrates to `watering_mode: "classic"`; `mqtt_*` keys absent
  after load; constructing a `ZoneEntry` from a dict containing leftover
  `mqtt_*` keys does not raise; `STORAGE_VERSION == 10`.
- [ ] **Step 2 — run RED.**
- [ ] **Step 3 — implement:** `STORAGE_VERSION = 10`; remove `mqtt_topic/
  mqtt_open_field/mqtt_open_value/mqtt_stop_value` from `ZoneEntry`; add a
  known-field filter when building a `ZoneEntry` from stored data (drop unknown
  keys); in `_async_migrate_func` add `if old_version <= 9:` block that per-zone
  maps `watering_mode == "mqtt"` → `"classic"` and pops `mqtt_*` keys.
- [ ] **Step 4 — GREEN** (targeted) then full suite (regression vs baseline).
- [ ] **Step 5 — commit.**

### Task 2: Remove mqtt from const + self_closing

**Files:**
- Modify: `custom_components/smart_irrigation/const.py`,
  `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py` (delete the 4 mqtt tests)

- [ ] **Step 1:** delete the mqtt unit tests (`test_is_self_closing_includes_mqtt`,
  `test_mqtt_open_*`, `test_mqtt_run_*`, `test_mqtt_stop_*`) and the
  `_mqtt_zone()` helper.
- [ ] **Step 2 — run:** remaining self_closing tests still pass (they will, once
  code compiles).
- [ ] **Step 3 — implement:** remove `WATERING_MODE_MQTT` and `ZONE_MQTT_*` from
  `const.py`; in `self_closing.py` delete `_sc_mqtt_open/_sc_mqtt_stop/
  _sc_mqtt_publish`, the mqtt branch of `_sc_dispatch_open` (leave only
  `_sc_service_open`), the `WATERING_MODE_MQTT` arm of `_sc_is_self_closing`,
  and the mqtt branch of `async_stop_self_closing`. Remove the now-unused
  `import json` if nothing else needs it.
- [ ] **Step 4 — GREEN** targeted + full suite; grep confirms no `mqtt`/`MQTT`
  references remain in `self_closing.py`/`const.py`.
- [ ] **Step 5 — commit.**

### Task 3: Default `duration_field` = "duration"

**Files:**
- Modify: `store.py` (ZoneEntry default), `frontend/src/types.ts` (default)
- Test: `tests/test_store_self_closing.py`

- [ ] **Step 1 — failing test:** a fresh `ZoneEntry` has `duration_field ==
  "duration"`.
- [ ] **Step 2 — RED.**
- [ ] **Step 3 — implement:** set `ZoneEntry.duration_field` default to
  `"duration"`; set the TS `SmartIrrigationZone` default likewise where zones
  are constructed.
- [ ] **Step 4 — GREEN.**
- [ ] **Step 5 — commit.**

### Task 4: Three script blueprints

**Files:**
- Create: `custom_components/smart_irrigation/blueprints/script/tuya_z2m_valve.yaml`
- Create: `custom_components/smart_irrigation/blueprints/script/sonoff_z2m_valve.yaml`
- Create: `custom_components/smart_irrigation/blueprints/script/entity_valve.yaml`
- Test: `tests/test_blueprints.py` (new)

- [ ] **Step 1 — failing test:** for each of the 3 files: loads as YAML; has a
  top-level `blueprint:` with `domain: script` and a non-empty `input:`; has a
  `duration` field; `sequence` present. Tuya & SONOFF reference `mqtt.publish`;
  entity references `number.set_value` and a turn_on action.
- [ ] **Step 2 — RED** (files absent).
- [ ] **Step 3 — implement** the three YAMLs exactly as in the spec (Tuya:
  countdown+valve open, valve close; SONOFF: nested `cyclic_timed_irrigation`;
  entity: `number.set_value` countdown + `homeassistant.turn_on`/`turn_off`).
  All use `duration>0` open / else close via `choose`, and `{ … } | to_json`
  for dynamic payloads.
- [ ] **Step 4 — GREEN.**
- [ ] **Step 5 — commit.**

### Task 5: Auto-install (copy-on-setup)

**Files:**
- Create: `custom_components/smart_irrigation/blueprint_install.py`
- Modify: `custom_components/smart_irrigation/__init__.py` (call from `async_setup`)
- Test: `tests/test_blueprint_install.py` (new)

- [ ] **Step 1 — failing test:** `install_bundled_blueprints(src, dst)` copies a
  file missing in `dst`; does NOT overwrite an existing `dst` file whose content
  differs; creates `dst` if absent; a raised copy error is swallowed (returns,
  no exception). Use temp dirs; pure function (no hass needed).
- [ ] **Step 2 — RED.**
- [ ] **Step 3 — implement:** `blueprint_install.py` with a sync
  `install_bundled_blueprints(src_dir, dst_dir)` (copy-if-missing, mkdir,
  try/except per file, logging). In `__init__.py async_setup`, compute
  `src = <pkg>/blueprints/script`, `dst = hass.config.path("blueprints",
  "script", DOMAIN)`, and `await hass.async_add_executor_job(...)`. Non-fatal.
- [ ] **Step 4 — GREEN** targeted + full suite.
- [ ] **Step 5 — commit.**

### Task 6: Frontend — remove mqtt UI, add script picker

**Files:**
- Modify: `frontend/src/views/zones/view-zone-settings.ts`,
  `frontend/src/const.ts`, `frontend/src/types.ts`,
  `frontend/localize/languages/en.json`
- Build: `frontend/dist/*` (regenerated)

- [ ] **Step 1:** remove the `mqtt` `<option>`, the `watering_mode === "mqtt"`
  block, the `ZONE_MQTT_*` consts, the `mqtt_*` type fields, and the mqtt
  `en.json` keys (labels + help).
- [ ] **Step 2:** replace the `run_service` and `stop_service` `<input>`s with
  `<ha-entity-picker .hass=${this.hass} .includeDomains=${["script"]}
  allow-custom-entity .value=${zone.run_service || ""} @value-changed=…>`,
  storing the picked `script.<id>` string (mirror the `linked_entity` picker).
- [ ] **Step 3:** the `watering_mode !== "service"` fallback that renders
  `linked_entity` becomes simply `watering_mode !== "service"` (drop the extra
  `&& !== "mqtt"`).
- [ ] **Step 4 — build:** `npm run lint:fix && npm run build`; validate en.json;
  confirm no `mqtt` symbols remain in `dist/smart-irrigation.js`; confirm dist
  determinism (rebuild → stable).
- [ ] **Step 5 — commit** (`git add -f` the two dist bundles).

### Task 7: Docs + final review

**Files:**
- Modify: `README.md` (or `docs/` watering-modes section)

- [ ] **Step 1:** add a "Self-closing watering (service mode) + valve
  blueprints" section: what service mode is, the 3 shipped blueprints, how to
  instantiate + wire (watering mode = service, run_service = the script,
  duration_unit per device: Tuya = Minutes, SONOFF = Seconds), the crash-safety
  rationale, and the copy-if-missing auto-install note.
- [ ] **Step 2 — final gates:** full backend suite regression-free vs baseline;
  frontend build + dist freshness green; dispatch a code-review subagent over
  the whole diff.
- [ ] **Step 3 — commit + push.**

---

## Self-review

- Spec coverage: MQTT removal (T1/T2/T6), 3 blueprints (T4), auto-install (T5),
  script picker (T6), duration default (T3), docs (T7), migration (T1) — all
  mapped.
- No placeholders; each task has test → RED → impl → GREEN → commit.
- Type consistency: `duration` field name aligns blueprint ↔ `duration_field`
  default (T3/T4); `script.<id>` string flows picker → `_sc_split_service`.
