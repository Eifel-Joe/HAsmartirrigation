# Gardena Distributor — Plan E: Config API (websocket + HTTP CRUD)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose distributor configuration to the frontend — a coordinator upsert method (create/update/delete routing), the HTTP POST view + websocket read command that the panel will call, and the two zone-membership fields on the zone config POST so a zone can be mapped to a distributor+outlet. This is the API layer the Panel UI (next plan) sits on.

**Architecture:** Mirror the existing zone config layer exactly: the frontend reads via a websocket command (`smart_irrigation/distributors`) and writes via an HTTP POST view (`SmartIrrigationDistributorView` at `/api/smart_irrigation/distributors`, `remove: true` to delete), which delegates to a new `async_upsert_distributor` coordinator method that routes to the Plan-A store CRUD.

**Tech Stack:** Python, Home Assistant `HomeAssistantView` + `websocket_api`, pytest.

**Spec:** `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (§8). Depends on Plans A–D. The store CRUD (`async_create/update/delete_distributor`, `async_get_distributors`) is landed (Plan A); `SmartIrrigationError`, `ATTR_REMOVE` exist in `const.py`.

**Verified codebase facts (file:line):**
- Websocket/HTTP layer: `websockets.py`. Zone HTTP view `SmartIrrigationZoneView` (`websockets.py:222-284`) — `@RequestDataValidator(vol.Schema({...}))` on `post(self, request, data)`, delegates to `coordinator.async_update_zone_config`, then `async_dispatcher_send(hass, DOMAIN + "_update_frontend")`.
- WS read `websocket_get_zones` (`websockets.py:324-329`, `@async_response`) → `store.async_get_zones()` → `connection.send_result`.
- Registration in `async_register_websockets` (`websockets.py:888-1117`): `hass.http.register_view(SmartIrrigationZoneView)` + `async_register_command(hass, DOMAIN + "/zones", websocket_get_zones, schema)`.
- HTTP-view test pattern: `tests/test_watering_calendar_api.py` (instantiate the view, override `view.json`, fake request with `request.app["hass"]`). NOTE: `@async_response` WS handlers are NOT unit-testable under the suite's websocket_api mock — so the testable logic lives in `async_upsert_distributor` (undecorated).

**Test runner (verified):** from repo root:
```
PYTHONPATH="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad" "C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad/uvenv312/Scripts/python.exe" -m pytest tests/test_distributor_integration.py -p _local_socket_unblock -q
```
System Python (3.13) will NOT work. Tests append to `tests/test_distributor_integration.py`.

---

### Task 1: `async_upsert_distributor` coordinator method (create/update/delete routing)

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (add to `DistributorMixin`, after the service handlers)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append tests to `tests/test_distributor_integration.py`:**

```python
def _upsert_coord():
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.store = Mock()
    c.store.async_create_distributor = AsyncMock(return_value={"id": 0})
    c.store.async_update_distributor = AsyncMock(return_value={"id": 5})
    c.store.async_delete_distributor = AsyncMock(return_value=True)
    return c


async def test_upsert_creates_when_no_id():
    c = _upsert_coord()
    await c.async_upsert_distributor({"name": "Garten"})
    c.store.async_create_distributor.assert_awaited_once_with({"name": "Garten"})
    c.store.async_update_distributor.assert_not_awaited()


async def test_upsert_updates_when_id_present_including_zero():
    c = _upsert_coord()
    # id 0 is a valid distributor id — must UPDATE, not create.
    await c.async_upsert_distributor({"id": 0, "name": "Garten", "pause_seconds": 120})
    c.store.async_update_distributor.assert_awaited_once_with(
        0, {"name": "Garten", "pause_seconds": 120}
    )
    c.store.async_create_distributor.assert_not_awaited()


async def test_upsert_deletes_when_remove_flag():
    c = _upsert_coord()
    await c.async_upsert_distributor({"id": 3, const.ATTR_REMOVE: True})
    c.store.async_delete_distributor.assert_awaited_once_with(3)
    c.store.async_update_distributor.assert_not_awaited()
    c.store.async_create_distributor.assert_not_awaited()
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'async_upsert_distributor'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` in `distributor.py`, immediately AFTER `handle_distributor_run_now`:

```python
    # --- config CRUD (frontend POST) --------------------------------------

    async def async_upsert_distributor(self, data: dict):
        """Create / update / delete a distributor from a frontend config POST.

        Routing mirrors the zone config POST: ``remove: true`` deletes; an ``id``
        that is present (INCLUDING 0 — a valid distributor id) updates; otherwise
        it creates. Unknown keys are dropped by the store CRUD (attrs allowlist)."""
        data = dict(data)
        if data.get(const.ATTR_REMOVE):
            return await self.store.async_delete_distributor(data["id"])
        if data.get("id") is not None:
            did = data.pop("id")
            data.pop(const.ATTR_REMOVE, None)
            return await self.store.async_update_distributor(did, data)
        return await self.store.async_create_distributor(data)
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_integration.py
git commit -m "feat(distributor): async_upsert_distributor (config create/update/delete)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: HTTP POST view + websocket read command + registration

**Files:**
- Modify: `custom_components/smart_irrigation/websockets.py` (add view + WS handler + register both)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append the test to `tests/test_distributor_integration.py`:**

```python
def test_distributor_view_url():
    from custom_components.smart_irrigation.websockets import (
        SmartIrrigationDistributorView,
    )

    assert SmartIrrigationDistributorView.url == "/api/" + const.DOMAIN + "/distributors"


async def test_distributor_view_post_upserts_and_dispatches():
    from unittest.mock import patch

    from custom_components.smart_irrigation.websockets import (
        SmartIrrigationDistributorView,
    )

    coordinator = AsyncMock()
    hass = SimpleNamespace(data={const.DOMAIN: {"coordinator": coordinator}})
    request = MagicMock()
    request.app = {"hass": hass}
    data = {"name": "Garten", "pause_seconds": 120}
    # RequestDataValidator reads the body via request.json(), validates against the
    # view's schema, then calls the inner post(view, request, validated_data).
    request.json = AsyncMock(return_value=data)

    view = SmartIrrigationDistributorView()
    view.json = MagicMock(return_value="OK")

    with patch(
        "custom_components.smart_irrigation.websockets.async_dispatcher_send"
    ) as disp:
        result = await view.post(request)  # decorated: exercises the real validator

    coordinator.async_upsert_distributor.assert_awaited_once()
    passed = coordinator.async_upsert_distributor.await_args.args[0]
    assert passed["name"] == "Garten"
    assert passed["pause_seconds"] == 120
    disp.assert_called_once_with(hass, const.DOMAIN + "_update_frontend")
    assert result == "OK"
    view.json.assert_called_once_with({"success": True})
```

Note: calling the DECORATED `view.post(request)` exercises the real `RequestDataValidator` (it `await request.json()` → validates against the view schema → calls the inner). This is why the request is given a mocked `request.json`. If a future HA version's validator needs more request attributes, the `test_distributor_view_url` test + Task-1 coverage still guard the essentials.

- [ ] **Step 2: Run — expect FAIL** (`ImportError: cannot import name 'SmartIrrigationDistributorView'`).

- [ ] **Step 3a: Add the view + WS handler.** In `websockets.py`, add near `SmartIrrigationZoneView` (mirror its imports — `HomeAssistantView`, `RequestDataValidator`, `vol`, `cv`, `async_dispatcher_send`, `const`, `SmartIrrigationError` are already imported there):

```python
class SmartIrrigationDistributorView(HomeAssistantView):
    """HTTP API for Gardena distributor configuration (create/update/delete)."""

    url = "/api/" + const.DOMAIN + "/distributors"
    name = "api:" + const.DOMAIN + ":distributors"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Optional("id"): vol.Coerce(int),
                vol.Optional("name"): cv.string,
                vol.Optional("watering_mode"): cv.string,
                vol.Optional("inlet_entity"): vol.Any(cv.string, None),
                vol.Optional("run_service"): vol.Any(cv.string, None),
                vol.Optional("stop_service"): vol.Any(cv.string, None),
                vol.Optional("duration_field"): cv.string,
                vol.Optional("duration_unit"): cv.string,
                vol.Optional("run_data"): dict,
                vol.Optional("stop_data"): dict,
                vol.Optional("confirm_entity"): vol.Any(cv.string, None),
                vol.Optional("flow_sensor"): vol.Any(cv.string, None),
                vol.Optional("pause_seconds"): vol.Coerce(int),
                vol.Optional("skip_pulse_seconds"): vol.Coerce(int),
                vol.Optional("current_outlet"): vol.Coerce(int),
                vol.Optional("position_state"): cv.string,
                vol.Optional("notify_target"): vol.Any(cv.string, None),
                vol.Optional("use_master"): cv.boolean,
                vol.Optional("commissioning_confirmed"): cv.boolean,
                vol.Optional(const.ATTR_REMOVE): cv.boolean,
            },
            extra=vol.ALLOW_EXTRA,
        )
    )
    async def post(self, request, data):
        """Create/update/delete a distributor from the panel."""
        hass = request.app["hass"]
        coordinator = hass.data[const.DOMAIN]["coordinator"]
        try:
            await coordinator.async_upsert_distributor(dict(data))
        except SmartIrrigationError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        async_dispatcher_send(hass, const.DOMAIN + "_update_frontend")
        return self.json({"success": True})


@async_response
async def websocket_get_distributors(hass: HomeAssistant, connection, msg):
    """Publish distributor data to the panel."""
    coordinator = hass.data[const.DOMAIN]["coordinator"]
    distributors = await coordinator.store.async_get_distributors()
    connection.send_result(msg["id"], distributors)
```

(If `SmartIrrigationError` is referenced as `const.SmartIrrigationError` elsewhere in this file rather than a bare import, match the file's existing style.)

- [ ] **Step 3b: Register both.** In `async_register_websockets`, next to `hass.http.register_view(SmartIrrigationZoneView)` add:

```python
    hass.http.register_view(SmartIrrigationDistributorView)
```

and next to the `async_register_command(hass, const.DOMAIN + "/zones", ...)` block add:

```python
    async_register_command(
        hass,
        const.DOMAIN + "/distributors",
        websocket_get_distributors,
        websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
            {vol.Required("type"): const.DOMAIN + "/distributors"}
        ),
    )
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/websockets.py tests/test_distributor_integration.py
git commit -m "feat(distributor): config HTTP view + websocket read command

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Zone membership fields on the zone config POST

**Files:**
- Modify: `custom_components/smart_irrigation/websockets.py` (`SmartIrrigationZoneView` schema)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append the test to `tests/test_distributor_integration.py`:**

```python
async def test_zone_view_accepts_membership_fields():
    from unittest.mock import patch

    from custom_components.smart_irrigation.websockets import SmartIrrigationZoneView

    coordinator = AsyncMock()
    hass = SimpleNamespace(data={const.DOMAIN: {"coordinator": coordinator}})
    request = MagicMock()
    request.app = {"hass": hass}
    # a zone-to-outlet mapping update carries distributor_id + outlet_number
    data = {const.ZONE_ID: 2, "distributor_id": 0, "outlet_number": 3}
    request.json = AsyncMock(return_value=data)

    view = SmartIrrigationZoneView()
    view.json = MagicMock(return_value="OK")

    with patch("custom_components.smart_irrigation.websockets.async_dispatcher_send"):
        # decorated: the schema must ACCEPT the membership fields, else the
        # validator short-circuits and the inner handler never runs.
        await view.post(request)

    coordinator.async_update_zone_config.assert_awaited_once()
    called = coordinator.async_update_zone_config.await_args
    forwarded = called.args[1] if len(called.args) > 1 else called.kwargs.get("data")
    assert forwarded["distributor_id"] == 0
    assert forwarded["outlet_number"] == 3
```

Note: if the existing zone schema already uses `extra=vol.ALLOW_EXTRA`, the fields pass through even before the change, so this test may go GREEN with no RED phase — that is expected; add the explicit typed fields anyway (a documented, coerced contract) and report the observation. If the schema is strict (the default), the pre-change validator rejects the fields (returns an error, the inner never runs → `assert_awaited_once` fails as RED), and the added schema fields fix it.

- [ ] **Step 2: Run — expect FAIL** (the schema rejects `distributor_id`/`outlet_number` — they aren't allowed keys — OR they're dropped, so the assert fails).

- [ ] **Step 3: Add the fields.** In `websockets.py`, in the `SmartIrrigationZoneView` `@RequestDataValidator(vol.Schema({...}))`, add:

```python
                vol.Optional("distributor_id"): vol.Any(vol.Coerce(int), None),
                vol.Optional("outlet_number"): vol.Any(vol.Coerce(int), None),
```

(If the zone schema already uses `extra=vol.ALLOW_EXTRA`, the fields pass through already; still add them explicitly for a typed, documented contract, and the test confirms they reach the coordinator.)

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Run the distributor + zone-view suites for regressions:**

Run: `pytest tests/test_distributor_integration.py tests/test_panel.py tests/test_distributor.py tests/test_distributor_cycle.py -p _local_socket_unblock -q` (via the wrapper).
Expected: PASS for the distributor suites (test_panel.py may carry pre-existing unrelated failures — compare against baseline via `git stash` if in doubt).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/websockets.py tests/test_distributor_integration.py
git commit -m "feat(distributor): zone config POST accepts distributor_id + outlet_number

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan E Self-Review

- **Spec coverage (§8 config plumbing):** create/update/delete routing incl. id-0 (`async_upsert_distributor`) → Task 1; the HTTP POST view + WS read the panel calls → Task 2; zone→outlet mapping settable from the zone form → Task 3.
- **Deferred to Plan F (frontend):** the actual panel UI (distributor list/form, test-run button, commissioning switch + popup, re-sync UI, zone-mapping selector), i18n in 8 languages, and the rollup build. Plan G — automatic scheduling.
- **Testability note:** `@async_response` WS handlers aren't unit-testable under the suite's mock; the meaningful logic is in `async_upsert_distributor` (fully tested). The HTTP view is tested via `post.__wrapped__` (with a documented fallback if that attribute isn't present).
- **No placeholders:** every step has concrete code, exact commands, expected output.
- **Type consistency:** `async_upsert_distributor` on `DistributorMixin` calls the Plan-A store CRUD; the view delegates to it; `ATTR_REMOVE`/`SmartIrrigationError` exist; the id-0 routing uses `is not None` (not truthiness).

## Handoff to Plan F (Panel UI)

Plan F builds the Lit/TypeScript panel branch on this API: `data/websockets.ts` helpers (`getDistributors` WS, `saveDistributor`/`deleteDistributor` HTTP POST mirroring `saveZone`/`deleteZone`); `components/si-distributor-form.ts` + `views/setup/view-distributor-settings.ts` (reusing `si-field`/`ha-card`/`ha-dialog`); the zone form gains a distributor+outlet selector (POSTs `distributor_id`/`outlet_number`); the **test-run button**, **commissioning-confirmed switch (with popup)** and **re-sync** call the Plan-D services via `hass.callService`; strings in all 8 `localize/languages/*.json`; wire into `view-setup.ts` tabs; `npm run build`. Reuse the existing look (spec §8).
