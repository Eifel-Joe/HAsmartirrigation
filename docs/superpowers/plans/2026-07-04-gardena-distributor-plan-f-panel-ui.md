# Gardena Distributor — Plan F: Panel UI (frontend) — HANDOFF

> **For the fresh session picking this up:** the entire Python backend (Plans A–E) is DONE, tested and reviewed on branch `feature/gardena-distributor`. This plan is the remaining **frontend** work: a Lit/TypeScript panel branch to configure & operate distributors. It is **build/lint-verifiable locally** (`npm run build` runs green here) but must be **click-tested on the running test-HA (192.168.10.196)** — that is the real verification. This doc is a structured task breakdown + exact mirror-targets, not verbatim TDD code (the frontend is iteration-verified, not pytest-RED/GREEN).

**Goal:** A distributor configuration + commissioning UI in the panel that blends into the existing look (spec §8 hard requirement), talks to the Plan-E config API + Plan-D services, and ships strings in all 8 languages.

**Branch / build:**
- Branch `feature/gardena-distributor` (from `production` v2026.07.10). Clean, fully-tested point.
- Frontend dir: `custom_components/smart_irrigation/frontend/`. Toolchain verified: **node v24 / npm 11**, `npm run build` (= `eslint src/**/*.ts && rollup -c`) builds `dist/` green. `npm run test` = vitest. Rebuild + commit `dist/` at the end (the integration ships the built bundles; cache-bust is by file mtime, panel.py).

---

## The contract this UI consumes (already built)

**Config CRUD (Plan E):**
- **Read distributors:** `hass.callWS({ type: "smart_irrigation/distributors" })` → list of distributor dicts.
- **Create/update/delete:** HTTP `POST /api/smart_irrigation/distributors` with the distributor body; `{ id, remove: true }` deletes; an `id` present (incl. 0) updates; else creates. Mirror `saveZone`/`deleteZone` in `frontend/src/data/websockets.ts`. A stale/missing id returns a 400 `{success:false,message}` (handled gracefully).
- **Zone→outlet mapping:** POST the zone (existing `saveZone` to `/api/smart_irrigation/zones`) with `distributor_id` + `outlet_number` — the zone POST schema now accepts them.

**Operation services (Plan D) — call via `hass.callService(DOMAIN, name, data)`:**
- `distributor_test_run` `{distributor_id}` — commissioning sweep (30 s/outlet), needs synced, exempt from the confirm gate.
- `distributor_set_outlet` `{distributor_id, outlet}` — re-sync (user read the physical window).
- `distributor_resync_home` `{distributor_id}` — re-sync to outlet 1.
- `distributor_run_now` `{distributor_id}` — one full manual cycle (needs synced + commissioning_confirmed; rejects if a cycle is active).

**Distributor object fields** (from `DistributorEntry`, `store.py`): `id, name, watering_mode` (classic|service), `inlet_entity, run_service, stop_service, duration_field, duration_unit, run_data, stop_data, confirm_entity, flow_sensor, pause_seconds` (default 300, floor 10), `skip_pulse_seconds` (default 30, floor 10), `current_outlet, position_state` (synced|uncertain), `notify_target, use_master` (bool), `commissioning_confirmed` (bool), `schedules, active_cycle`.

---

## Frontend structure & exact mirror-targets

| New file | Mirror of | Purpose |
|---|---|---|
| `src/data/websockets.ts` (extend) | `getZones`/`saveZone`/`deleteZone` | `getDistributors` (WS), `saveDistributor`/`deleteDistributor` (HTTP POST) |
| `src/components/si-distributor-form.ts` | `src/components/si-zone-form.ts` (controlled component, emits `*-changed` events, uses `<si-field>`) | the distributor config fields |
| `src/views/setup/view-distributor-settings.ts` | `src/views/zones/view-zone-settings.ts` (~430 lines: collapsible cards, add-dialog, delete-confirm, 500ms debounced auto-save) | distributor list + CRUD + commissioning controls |
| `src/views/zones/view-zone-settings.ts` (edit) | — | add a "belongs to distributor X, outlet N" selector to the zone edit form (POSTs `distributor_id`/`outlet_number`) |
| `src/views/setup/view-setup.ts` (edit) | existing tab router | add a "Distributors" tab/section routing to the new view |
| `src/types.ts` / `src/const.ts` (extend) | `SmartIrrigationZone` type etc. | `SmartIrrigationDistributor` TS type |
| `localize/languages/*.json` (all 8) | existing key structure | `panels.distributors.*` strings |

**Reusable building blocks (don't reinvent — spec §8):** `<si-field>` (label/unit/help wrapper, `si-field.ts`), `<ha-card>` (card), `<ha-dialog>` (confirm/popup), `<ha-entity-picker>` (inlet/sensor selection), `<ha-textfield>`/`<ha-select>`/`<ha-switch>`, MDI icons from `@mdi/js`, HA CSS vars (`--primary-color`, `--secondary-text-color`, `--divider-color`, …), `showToast`/`showErrorToast` (`helpers.ts`), the `zone-state-badge` pattern for a position/state badge. i18n via `localize("panels.distributors.x", hass.language)` (`localize/localize.ts`); load-blocking + cache-bust already handled by the panel.

---

## Task breakdown (build-verify each with `npm run build`)

1. **TS types + websocket helpers.** `SmartIrrigationDistributor` type; `getDistributors`/`saveDistributor`/`deleteDistributor` in `data/websockets.ts`. Build green.
2. **`si-distributor-form.ts`** — controlled form for the §4.1 fields. Group: identity (name), inlet actuation (watering_mode select → classic shows `inlet_entity` picker; service shows `run_service`/`stop_service`/`duration_field`/`duration_unit`/`run_data`), shared sensors (`confirm_entity`/`flow_sensor` pickers), timing (`pause_seconds`/`skip_pulse_seconds` with the failure-mode hint text + floor 10), `use_master`, `notify_target`. Build green.
3. **`view-distributor-settings.ts`** — list distributors as cards (mirror zone-settings): add-dialog, edit (debounced auto-save via `saveDistributor`), delete-confirm. Per-card commissioning block: **position + state badge**; **"Test run" button** (`distributor_test_run`); **re-sync** control (read window → `distributor_set_outlet`, + "to 1" → `distributor_resync_home`); **commissioning-confirmed `<ha-switch>`** with a **confirmation `<ha-dialog>` popup** — the switch is the arm gate; setting it POSTs `commissioning_confirmed: true`; note it can only be set when synced and drops to off on any uncertain (the backend already de-arms; the UI reflects it from the polled state); a **"Run now" button** (`distributor_run_now`). Build green.
4. **Zone form: distributor+outlet selector.** In the zone edit form add a distributor `<ha-select>` (from `getDistributors`) + an outlet number field; on change POST the zone with `distributor_id`/`outlet_number`. Enforce contiguous 1..n / n∈2..6 in the UI (spec §4.3); when a zone is assigned to a distributor, hide/disable its own valve + schedule fields. Build green.
5. **Wire into the panel.** Add the "Distributors" tab in `view-setup.ts` + route in `smart-irrigation.ts`. Build green.
6. **UI hints (spec):** pressure/flow warning (≥1 bar / 20 l/h; below-floor pause/skip warning); Wahl-Taste-undetectable → re-sync note; changing outlets forces re-sync + re-confirm; parallel-mode concurrent-draw warning; **sequential/rotating + master-off-after → pump is per-outlet cycled** hint (spec §8).
7. **i18n:** add `panels.distributors.*` keys to `en.json` first, then all 7 others (de/es/fr/it/nl/no/sk). All new strings in all 8 (memory rule).
8. **Build + commit `dist/`.** `npm run build`; commit the source + rebuilt `dist/*.js`.

---

## Verification (on the user's test-HA — the real gate)

Install the beta on 192.168.10.196, then walk the commissioning flow: create a distributor → map zones to outlets → set device to outlet 1 + re-sync → **Test-run**, watch each zone water in order + the device advance → adjust pause/skip if needed → set the commissioning switch (popup) → **Run now** for a full observed cycle. Confirm the switch drops to off + a notify fires if a safety-halt/uncertain occurs.

## After Plan F → Beta

Bump to **PEP440 `bN`** (e.g. `v2026.07.11b1`, NEVER `-betaN`), rebuild `dist`, release as a **pre-release** for HACS install on 192.168.10.196. Long live-test. **Plan G** (automatic schedule dispatch: schedule-target discriminator + `_perform_schedule_action` branch → `async_run_distributor_cycle` with `concurrent` from the sequencing mode + finish-anchor `distributor_cycle_estimate`; promote the `"watering"`/`"pausing"`/`"restart_mid_advance"` literals to constants) = Beta 2.
