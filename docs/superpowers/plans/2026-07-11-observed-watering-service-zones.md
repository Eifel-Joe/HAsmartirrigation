# Observed-watering for service zones (Phase 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let JustChr's opt-in "observed watering" credit **service / self-closing** zones (which have no `linked_entity`) via a new optional per-zone `observed_entity`, and stop the self-closing runner from double-crediting SI's own runs.

**Architecture:** Additive `ZoneEntry.observed_entity` (default None). The observer (`ObservedWateringMixin.async_setup_observed_watering`) tracks `linked_entity` **or** (else) `observed_entity` per zone. The self-closing runner calls the existing `_note_si_valve` so SI's own service run isn't observed. Frontend adds an entity picker in the service-mode block, shown only when `observed_watering_enabled` is on. All gated by the existing flag (default off).

**Tech Stack:** Python (attrs / HA coordinator mixins), Lit/TypeScript, pytest + vitest. Spec: `docs/superpowers/specs/2026-07-11-observed-watering-service-zones-design.md`.

**Dev branch:** `local/observed-watering-ext` (already checked out, from `production` v2026.07.13). Phase 2 (distributor members) is a separate later cycle.

**Test env (do NOT rebuild):** Python 3.12 env is built. From repo root, prefix Bash with `export PATH="/mingw64/bin:/usr/bin:/bin:$PATH"` and run tests as `./.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock --tb=short -q`. Harmless `ProactorEventLoop`/`_ssock` teardown lines print after tests — ignore. Frontend: `custom_components/smart_irrigation/frontend`, `npm run lint` / `npm run build` (PATH needs `/c/Program Files/nodejs`).

---

## File Structure

**Backend**
- `custom_components/smart_irrigation/const.py` — `ZONE_OBSERVED_ENTITY = "observed_entity"`.
- `custom_components/smart_irrigation/store.py` — `ZoneEntry.observed_entity` attr + `async_load` hydration.
- `custom_components/smart_irrigation/observed_watering.py` — entity_map: `linked_entity` else `observed_entity`.
- `custom_components/smart_irrigation/self_closing.py` — `_note_si_valve` in `async_run_self_closing`.

**Frontend**
- `frontend/src/const.ts` — `ZONE_OBSERVED_ENTITY`.
- `frontend/src/types.ts` — `observed_entity?: string | null` on the zone type(s).
- `frontend/src/views/zones/view-zone-settings.ts` — picker in the service block, gated on `observed_watering_enabled`.
- `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json` — `observed_entity` label + help.

**Tests**
- `tests/test_observed_watering.py` — new: entity_map + suppression.
- `tests/test_self_closing.py` — extend: run marks `_si_driven_until`.

---

## Task 1: `observed_entity` zone field (backend)

**Files:** Modify `const.py`, `store.py`; Test: `tests/test_observed_watering.py` (new).

- [ ] **Step 1: Failing test** — create `tests/test_observed_watering.py`:
```python
"""Observed watering extended to service/self-closing zones (Phase 1)."""

import attr

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.store import ZoneEntry


def test_zone_observed_entity_defaults_none():
    field = attr.fields_dict(ZoneEntry)["observed_entity"]
    assert field.default is None
    assert const.ZONE_OBSERVED_ENTITY == "observed_entity"
```

- [ ] **Step 2: Run — expect FAIL**
`./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock --tb=short -q`
Expected: `KeyError: 'observed_entity'`.

- [ ] **Step 3: const.py** — after `ZONE_CONFIRM_ENTITY = "confirm_entity"` (~line 568):
```python
# Observed-watering (opt-in): the physical valve/switch to watch for EXTERNAL
# runs of a service/self-closing zone (which has no linked_entity). Distinct from
# confirm_entity (run confirmation). Only consulted when observed_watering_enabled.
ZONE_OBSERVED_ENTITY = "observed_entity"
```

- [ ] **Step 4: store.py** — add the import `ZONE_OBSERVED_ENTITY` to the const import block (alphabetical, near `ZONE_LINKED_ENTITY`). In `ZoneEntry`, after `confirm_entity = attr.ib(type=str, default=None)` (~line 222):
```python
    observed_entity = attr.ib(type=str, default=None)
```
In `async_load`, after `confirm_entity=zone.get("confirm_entity", None),` (~line 777):
```python
                        observed_entity=zone.get(ZONE_OBSERVED_ENTITY, None),
```
(No STORAGE_VERSION bump — `.get` default handles absence, like `confirm_entity`. `async_create_zone`/`async_update_zone` filter by `attr.fields_dict(ZoneEntry)`, so the field flows through CRUD automatically; the zone websocket POST uses ALLOW_EXTRA, so no schema change — verify by reading the zone POST handler and only touch it if it has an explicit field allow-list.)

- [ ] **Step 5: Run — expect PASS**
`./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock --tb=short -q` → 1 passed.
Guard: `./.venv/Scripts/python.exe -m pytest tests/test_store.py tests/test_store_self_closing.py -p _local_socket_unblock --tb=short -q` → no new failures.

- [ ] **Step 6: Commit**
```
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py tests/test_observed_watering.py
git commit -m "$(printf 'feat(store): add optional observed_entity zone field\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 2: Observer entity_map + self-closing suppression (backend)

**Files:** Modify `observed_watering.py`, `self_closing.py`; Test: `tests/test_observed_watering.py`, `tests/test_self_closing.py`.

- [ ] **Step 1: Failing tests** — append to `tests/test_observed_watering.py`:
```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import SmartIrrigationCoordinator


def _obs_coord(zones, enabled=True):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    coord.hass = Mock()  # async_track_state_change_event(self.hass, ...) returns a Mock
    coord.store = Mock()
    coord.store.config = SimpleNamespace(observed_watering_enabled=enabled)
    coord.store.async_get_zones = AsyncMock(return_value=zones)
    coord._observed_entities = frozenset()
    coord._observed_unsub = None
    coord._observed_on_since = {}
    coord._observed_zone_by_entity = {}
    return coord


async def test_setup_maps_observed_entity_for_service_zone():
    coord = _obs_coord(
        [{const.ZONE_ID: 1, const.ZONE_OBSERVED_ENTITY: "switch.beet"}]
    )
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {"switch.beet": 1}


async def test_setup_prefers_linked_entity_over_observed():
    coord = _obs_coord(
        [{const.ZONE_ID: 1, const.ZONE_LINKED_ENTITY: "switch.lawn",
          const.ZONE_OBSERVED_ENTITY: "switch.other"}]
    )
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {"switch.lawn": 1}


async def test_setup_maps_nothing_when_feature_off():
    coord = _obs_coord(
        [{const.ZONE_ID: 1, const.ZONE_OBSERVED_ENTITY: "switch.beet"}], enabled=False
    )
    await coord.async_setup_observed_watering()
    assert coord._observed_zone_by_entity == {}
```
Append to `tests/test_self_closing.py` (reuses its `_coord`/`_zone`):
```python
async def test_self_closing_run_marks_si_driven():
    c = _coord()
    c._si_driven_until = {}
    c.hass.loop.time = Mock(return_value=1000.0)
    c._confirm_valve_running = AsyncMock(return_value=True)
    c._timed_volume_l = Mock(return_value=20.0)
    c._credited_depth_native = Mock(return_value=4.0)
    await c.async_run_self_closing(_zone(), trigger="schedule")
    # zone id 2 marked SI-driven for the run window so the observer skips it
    assert 2 in c._si_driven_until
    assert c._si_driven_until[2] > 1000.0
```
(Add `from unittest.mock import Mock` to test_self_closing.py imports if not present — it already imports `AsyncMock, Mock`.)

- [ ] **Step 2: Run — expect FAIL**
`./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py tests/test_self_closing.py::test_self_closing_run_marks_si_driven -p _local_socket_unblock --tb=short -q`
Expected: the 3 observer setup tests fail (observed_entity not mapped) and the self-closing test fails (`2 not in _si_driven_until`).

- [ ] **Step 3: Extend the observer** — in `observed_watering.py::async_setup_observed_watering`, replace the entity loop (~lines 52-55):
```python
            for zone in await self.store.async_get_zones():
                # linked_entity for classic zones; else the opt-in observed_entity
                # for service/self-closing zones (no linked valve of their own).
                entity = zone.get(const.ZONE_LINKED_ENTITY) or zone.get(
                    const.ZONE_OBSERVED_ENTITY
                )
                if entity:
                    entity_map[entity] = int(zone.get(const.ZONE_ID))
```

- [ ] **Step 4: Suppress SI's own service run** — in `self_closing.py::async_run_self_closing`, immediately after the `if planned_seconds <= 0:` early-return block (~line 140-141) and before the confirm/dispatch, add:
```python
        # Observed-watering (opt-in) may watch this zone's observed_entity, which
        # our own run_service opens. Mark the run window as SI-driven so the
        # observer does not double-credit it (the run already credits the bucket).
        self._note_si_valve(int(zone.get(const.ZONE_ID)), planned_seconds)
```
Verify `zone.get(const.ZONE_ID)` is the right accessor here (read the surrounding lines) and that `_note_si_valve` exists on the coordinator (it does — irrigation.py:46).

- [ ] **Step 5: Run — expect PASS**
`./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py tests/test_self_closing.py -p _local_socket_unblock --tb=short -q` → all pass.

- [ ] **Step 6: Regression**
`./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py -p _local_socket_unblock --tb=short -q` → existing observed-watering tests still green (entity_map change is additive: `linked or observed` == `linked` when no observed_entity).

- [ ] **Step 7: Commit**
```
git add custom_components/smart_irrigation/observed_watering.py custom_components/smart_irrigation/self_closing.py tests/test_observed_watering.py tests/test_self_closing.py
git commit -m "$(printf 'feat(observed): watch service zones via observed_entity + suppress own runs\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 3: Frontend field + i18n (8 languages)

**Files:** Modify `frontend/src/const.ts`, `frontend/src/types.ts`, `frontend/src/views/zones/view-zone-settings.ts`, `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json`.

- [ ] **Step 1: const + type**
`const.ts` after `export const ZONE_CONFIRM_ENTITY = "confirm_entity";` (~line 148):
```typescript
export const ZONE_OBSERVED_ENTITY = "observed_entity";
```
`types.ts`: add `observed_entity?: string | null;` next to each `confirm_entity?: string | null;` (~lines 296 and 407).

- [ ] **Step 2: i18n label + help (8 languages)**
In each `localize/languages/<lang>.json`, add two keys to `panels.zones.labels` next to `confirm_entity`/`confirm_entity_help`:
- `observed_entity`: en "Observed valve/switch (optional)", de "Beobachtetes Ventil/Schalter (optional)"
- `observed_entity_help`: en "If Observed watering is on, external runs of this valve/switch (a manual tap, an automation) credit this zone's water storage. Leave empty to not observe this zone.", de "Wenn 'Beobachtete Bewässerung' an ist, schreiben externe Läufe dieses Ventils/Schalters (manuell, Automatisierung) dem Wasserspeicher dieser Zone gut. Leer lassen, um diese Zone nicht zu beobachten."
Translate es/fr/it/nl/no/sk faithfully in the register of the neighbouring `confirm_entity` strings in that same file. Keep valid JSON (verify each with `node -e "JSON.parse(require('fs').readFileSync('localize/languages/<l>.json','utf8'))"`).

- [ ] **Step 3: Render the picker** — in `view-zone-settings.ts`, inside the `zone.watering_mode === "service"` block, immediately after the `confirm_entity` `<ha-settings-row>` (closes ~line 1201), add a config-gated row mirroring confirm_entity:
```typescript
                            ${this.config?.observed_watering_enabled
                              ? html`
                                  <ha-settings-row>
                                    <span slot="heading"
                                      >${localize(
                                        "panels.zones.labels.observed_entity",
                                        this.hass.language,
                                      )}</span
                                    >
                                    <span slot="description"
                                      >${localize(
                                        "panels.zones.labels.observed_entity_help",
                                        this.hass.language,
                                      )}</span
                                    >
                                    <ha-entity-picker
                                      .hass="${this.hass}"
                                      .value="${zone.observed_entity || ""}"
                                      .includeDomains="${[
                                        "valve",
                                        "switch",
                                        "input_boolean",
                                      ]}"
                                      allow-custom-entity
                                      @value-changed="${(e: CustomEvent) =>
                                        this.handleEditZone(index, {
                                          ...zone,
                                          [ZONE_OBSERVED_ENTITY]:
                                            e.detail.value || null,
                                        })}"
                                    ></ha-entity-picker>
                                  </ha-settings-row>
                                `
                              : ""}
```
Import `ZONE_OBSERVED_ENTITY` from `../../const` alongside `ZONE_CONFIRM_ENTITY`. Verify the exact indentation/placement by reading lines 1200-1205 first.

- [ ] **Step 4: Lint**
In `frontend/`: `npm run lint` → clean (run `npm install` first only if `node_modules` is missing). Do NOT `npm run build` (dist rebuilt in Task 4).

- [ ] **Step 5: Commit** (dist rebuilt in Task 4)
```
git add custom_components/smart_irrigation/frontend/src custom_components/smart_irrigation/frontend/localize
git commit -m "$(printf 'feat(frontend): observed_entity picker for service zones (8 langs)\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

> **Frontend test note (no silent gap):** the zone-settings service-mode rows (confirm_entity, stop_service) have no per-field vitest coverage; this row follows that convention and is verified by lint + build + the live test. The backend behavior is fully covered by Task 1/2 tests.

---

## Task 4: Regression, review, build

- [ ] **Step 1: Full backend suite** — `./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q --tb=line`. Compare to the pre-change baseline (3 failed / 60 errors pre-existing); expect that plus the new observed tests passing, no new failures.
- [ ] **Step 2: black + ruff** — `uvx black --check custom_components/smart_irrigation/` and `uvx ruff check custom_components/smart_irrigation/` → clean (run `uvx black custom_components/smart_irrigation/` to fix if needed).
- [ ] **Step 3: Frontend build** — in `frontend/`: `npm test` then `npm run build` (regenerate dist).
- [ ] **Step 4: REGEL-8 sister-path check** — confirm: only `async_run_self_closing` needed the `_note_si_valve` marker (the linked-entity runner paths already have it; the distributor cycle is Phase 2 / excluded by `active_cycle`); the entity_map `linked or observed` change doesn't affect classic zones. Document/verify.
- [ ] **Step 5: Code review** — dispatch `superpowers:code-reviewer` over `production..HEAD` (feature commits). Focus: no double-credit of SI runs; entity_map correctness (linked xor observed); field gated on flag + service mode; feature-off byte-identical. Address findings.
- [ ] **Step 6: Commit dist**
```
git add -f custom_components/smart_irrigation/frontend/dist
git commit -m "$(printf 'build(frontend): rebuild dist with observed_entity picker\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 5: Delivery (gated on user)

- [ ] **Step 1: Decide release shape with the user** — Phase-1 alone as `v2026.07.14` (optionally bundling the help-page `target="_blank"` fix from ToDo), or hold until Phase 2. Per REGEL 5, show release notes and await approval before `gh release create`.
- [ ] **Step 2: If releasing** — cherry-pick the feature commits onto `production` (exclude `docs/superpowers`), bump `const.py`/`package.json`/`manifest.json`, rebuild dist, commit, push, create release via `gh api ... /releases` (the `gh release create` wrapper mis-reports a workflow-scope error — use the raw API POST as in v2026.07.13). User tests on HA-Test.
- [ ] **Step 3: Prepare upstream PR branch** — `feature/observed-watering-service-zones` from `upstream/master`, cherry-pick feature commits (no branding/version/docs), rebuild dist, push to origin. Do NOT open the PR (user decides). This enhances JustChr's own feature.
- [ ] **Step 4: Archive design docs** — ensure the spec + this plan are on `archive/observed-watering-design-history` before the dev branch is cleaned up.
- [ ] **Step 5: Update ToDo.md + memory** — mark Phase 1 shipped; note Phase 2 (distributor members) as the next cycle.

---

## Self-Review

**Spec coverage:** field (Task 1) ✓; observer entity_map extension (Task 2) ✓; SI-own-run suppression (Task 2) ✓; frontend gated field + 8-lang i18n (Task 3) ✓; opt-in default-off byte-identical (gating verified Task 2 step 6 / Task 4) ✓; Phase 2 explicitly deferred ✓.

**Placeholders:** es/fr/it/nl/no/sk translations in Task 3 are content-to-write in the neighbouring register (en/de given verbatim) — not logic gaps.

**Type consistency:** `observed_entity` (snake_case) identical across const.py / store.py / observed_watering.py / const.ts / types.ts / view-zone-settings.ts; `ZONE_OBSERVED_ENTITY == "observed_entity"`; `_note_si_valve(zone_id, planned_seconds)` matches the existing signature (irrigation.py:46).
