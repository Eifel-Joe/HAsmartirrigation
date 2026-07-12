# b9 batch: version-from-backend + test-run gate + member manual-run

> Execution: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Three shippable improvements bundled into beta b9: (1) the panel shows the integration version fetched from the backend at runtime (never drifts from the built bundle), (2) the distributor test-run button only works before commissioning, (3) distributor member zones get a "Jetzt bewässern (X Min)" custom-duration manual run, mutually exclusive per distributor with a hint text.

**Tech Stack:** HA custom integration (Python), Lit/TS panel (`npm run build`), pytest.

**Test env:**
```
S="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad"
PYTHONPATH="$S" "$S/uvenv312/Scripts/python.exe" -m pytest <path> -p _local_socket_unblock -q
```

**Verified recon (2026-07-05):**
- `websockets.py:340-373` `websocket_get_config` sends the config dict; registered `DOMAIN + "/config"` at 960-966. Extensible payload.
- `frontend/src/data/websockets.ts:18-23` `fetchConfig`; `frontend/src/types.ts:56-136` `SmartIrrigationConfig`; panel version at `frontend/src/smart-irrigation.ts:116` `<div class="version">${VERSION}</div>`; `VERSION` from `const.ts:2` `\`v${pkg.version}\`` (build-time; also used for cache-busting).
- `irrigation.py:1492-1550` `async_run_zone`; member branch 1521-1526 routes to `_dispatch_distributor_cycles([zone_id])` using the STORED duration.
- `distributor.py` `_dispatch_distributor_cycles(zone_ids=None)` → `async_run_distributor_cycle(..., only_zone_ids=list(target))`; per-outlet `window = float(zone.get(ZONE_DURATION) or 0) if water else skip`.
- `distributor.py:656-666` `handle_distributor_run_now` raises `SmartIrrigationError` if `active_cycle` set (single-flight guard to mirror).
- `frontend/src/views/zones/view-zones.ts`: `_canActuate` (237-241) `!!(linked_entity || (watering_mode==="service" && run_service))`; custom-duration control `_renderRunZoneControl` (~1100-1166) → `_runZoneFor` (~319-337) → `runZone` ws (`data/websockets.ts:250-255`). Member fields `distributor_id`/`outlet_number` in `types.ts:293-297`. Distributor object (with `active_cycle`, `position_state`) available via `fetchDistributors` (`websockets.py:385-389`), type `types.ts:374-405`.

## Design decisions (locked)
- **Version:** display `config.version` from the backend; fall back to build-time `VERSION` if absent. Keep `VERSION` for cache-busting (`?v=`).
- **Member manual-run = single outlet:** the target member waters for the **custom** duration; the ring still advances (skip-pulsing intervening outlets to reach it). Reuse `only_zone_ids=[zone_id]` + a new `duration_override`.
- **Mutual exclusion:** while a distributor has a non-empty `active_cycle`, NO member of it may start a manual run — backend rejects (`SmartIrrigationError`), panel disables the control for all its members + shows a hint.
- **Custom-duration control shows for members regardless of the calculated duration** (it's a user-input minutes run, decoupled from the daily calc).

---

### Task V-BE: version in the config payload (backend)

**Files:** `custom_components/smart_irrigation/websockets.py`. Test: `tests/test_websockets*.py` (or a new focused test).

- [ ] **Step 1 — test:** call/inspect `websocket_get_config` (or the config-building) and assert the result contains `version == const.VERSION`. If the existing test harness for websockets is heavy, a minimal unit test that constructs the payload dict and asserts `version` is present is acceptable; mirror any existing websocket test.
- [ ] **Step 2 — FAIL.**
- [ ] **Step 3 — implement:** in `websocket_get_config`, after building `config` (and the precipitation conversion), add `config["version"] = const.VERSION` before `connection.send_result(msg["id"], config)`. (Use a copy if `config` is the live store dict to avoid mutating persisted state — `config = dict(config)` first.)
- [ ] **Step 4 — PASS + no regressions.**
- [ ] **Step 5 — commit** `feat(panel): expose integration version in the config payload`

### Task M-BE: member custom-duration run + mutual-exclusion guard (backend)

**Files:** `custom_components/smart_irrigation/irrigation.py` (`async_run_zone`), `custom_components/smart_irrigation/distributor.py` (`_dispatch_distributor_cycles`, `async_run_distributor_cycle`). Test: `tests/test_distributor_dispatch.py`.

- [ ] **Step 1 — tests** (append to `tests/test_distributor_dispatch.py`):
```python
async def test_dispatch_passes_duration_override():
    c = _host()
    c._rain_delay_active = Mock(return_value=False)
    seen = {}
    async def _run(dist, *, concurrent=False, only_zone_ids=None, duration_override=None):
        seen["dur"] = duration_override
        seen["only"] = only_zone_ids
        return True
    c.async_run_distributor_cycle = AsyncMock(side_effect=_run)
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    c._dist_members = AsyncMock(return_value=[{"id": 7, "distributor_id": 0}])
    c._dist_needs_water = Mock(return_value=True)
    await c._dispatch_distributor_cycles([7], duration_override=120.0)
    assert seen["dur"] == 120.0 and seen["only"] == [7]


async def test_cycle_duration_override_sets_target_window():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    for m in ("_dist_persist_cycle","_dist_open_inlet","_dist_close_inlet","_dist_credit_zone","_dist_clear_cycle"):
        setattr(c, m, AsyncMock())
    c._dist_advance = AsyncMock(side_effect=lambda did, cur, n: (cur % n) + 1)
    windows = []
    async def _sleep(s): windows.append(s)
    c._dist_sleep = AsyncMock(side_effect=_sleep)
    c._dist_needs_water = Mock(return_value=True)
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    members = [{"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 30,
                "bucket": -1, "bucket_threshold": 0, "state": "automatic"}]
    c.store.async_get_zones = AsyncMock(return_value=members)
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1),
                                        only_zone_ids=[7], duration_override=200.0)
    # the target outlet watered for the override (200), not its stored 30
    assert 200.0 in windows
```
- [ ] **Step 2 — FAIL** (`duration_override` not a param).
- [ ] **Step 3 — implement:**
  - `async_run_distributor_cycle(self, distributor, *, concurrent=False, test_run=False, only_zone_ids=None, duration_override=None)`. In the outlet loop where `window` is computed for a watered outlet, when `not test_run and duration_override is not None and water`: `window = float(duration_override)`. (Only the targeted member is `water=True` because `only_zone_ids` filtered `to_water`; others skip-pulse unchanged.) Place the override right after the existing `window = ... if water else skip` line.
  - `_dispatch_distributor_cycles(self, zone_ids=None, duration_override=None)`: pass `duration_override=duration_override` into the `async_run_distributor_cycle(...)` call (alongside `concurrent`, `only_zone_ids`).
  - `irrigation.py` `async_run_zone` member branch (1521-1526): compute `seconds` (already done at the top of async_run_zone), add the active-cycle guard and pass the override:
    ```python
    if zone.get(const.ZONE_DISTRIBUTOR_ID) is not None:
        dist = self.store.get_distributor(zone.get(const.ZONE_DISTRIBUTOR_ID))
        if dist and dist.get("active_cycle"):
            _LOGGER.info("run_zone: distributor %s busy, ignoring member run", dist.get("id"))
            return
        await self._dispatch_distributor_cycles([zone_id], duration_override=float(seconds))
        return
    ```
    (Confirm `seconds` is the resolved custom duration in seconds and is in scope here — it is computed near the top of `async_run_zone`.)
- [ ] **Step 4 — PASS + run `tests/test_distributor.py tests/test_distributor_dispatch.py -q`** no regressions (the H5 `only_zone_ids` tests + G-series still pass).
- [ ] **Step 5 — commit** `feat(distributor): member run_zone honours custom duration + single-flight guard`

### Task FE: frontend — version display + member custom-run control + hint + i18n

**Files:** `frontend/src/types.ts`, `frontend/src/smart-irrigation.ts`, `frontend/src/views/zones/view-zones.ts`, `frontend/src/localize/languages/*.json` (or wherever panel strings live — 8 languages). Build: `npm run build`.

- [ ] **Step 1 — version display:** add `version?: string;` to `SmartIrrigationConfig` (`types.ts`); in `smart-irrigation.ts:116` render `${this.config?.version ?? VERSION}` (keep the `VERSION` import for the fallback + cache-busting).
- [ ] **Step 2 — member run control:** in `view-zones.ts`:
  - `_canActuate(zone)`: also return true when `zone.distributor_id != null` (so the custom-duration control renders for members).
  - The custom-duration control (`_renderRunZoneControl`) should render for members regardless of `zone.duration`. Gate it: if the zone is a member AND its distributor has a non-empty `active_cycle` (look the distributor up in the panel's fetched distributors by `zone.distributor_id`), render the control **disabled** + a **hint** ("Verteiler arbeitet gerade — bitte warten, bis er in Grundstellung ist."). Otherwise enabled. `_runZoneFor` already calls `runZone(zone_id, minutes)` — unchanged; the backend routes members correctly.
  - The panel must have the distributors list available in `view-zones.ts` (it fetches `fetchDistributors` elsewhere; if not present in this view, add a fetch/prop). Verify how other member-aware logic in this view accesses distributor data and reuse it.
- [ ] **Step 3 — i18n:** add the hint string key (e.g. `panels.zones.distributor_busy`) in ALL 8 language files, CRLF-canonical (Node script). German: "Verteiler arbeitet gerade — Start erst möglich, wenn er wieder in Grundstellung ist."
- [ ] **Step 4 — build:** `cd custom_components/smart_irrigation/frontend && npm run build` → EXIT 0 (lint + rollup). Run `npm test` (vitest) if present → green.
- [ ] **Step 5 — commit** the TS sources (NOT dist yet; dist is rebuilt+committed at release) `feat(panel): backend version + member custom-duration run with busy-hint`

### Task REL: release b9

- [ ] Bump version ×3 (`manifest.json` + `const.py` `VERSION` with `v`, `frontend/package.json` without `v`) `b8`→`b9`.
- [ ] **REBUILD dist** (mandatory on any version bump — the bundle bakes the build-time VERSION): `cd frontend && npm run build`; `git add -f` the 3 dist bundles.
- [ ] `uvx black --check custom_components/smart_irrigation/` clean; full distributor+entity+websocket pytest green.
- [ ] Commit `build: release v2026.07.11b9`, push, show release notes for approval, then `gh release create v2026.07.11b9 --repo Eifel-Joe/HAsmartirrigation --target feature/gardena-distributor --prerelease ...`.
- [ ] Verify on 192.168.10.196: panel shows **v2026.07.11b9** (version-from-backend fix), test-run button greyed when commissioned, member zones show the custom-duration control (disabled+hint while the distributor runs).
