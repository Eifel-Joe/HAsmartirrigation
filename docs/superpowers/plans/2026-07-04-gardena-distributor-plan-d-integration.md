# Gardena Distributor — Plan D: Integration & Services

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the distributor engine *live* — wire `DistributorMixin` into the coordinator, run the restart-reconciliation at startup, exclude distributor member zones from the normal watering path, and expose the four operational services (`distributor_set_outlet`, `distributor_resync_home`, `distributor_test_run`, `distributor_run_now`) so the feature is fully usable via services (the commissioning flow + a manual full cycle). Automatic schedule dispatch is a later plan (Plan F / Beta 2).

**Architecture:** Add `DistributorMixin` to `SmartIrrigationCoordinator`'s mixin list (`__init__.py`), add the startup resume hook next to the self-closing one, add a one-condition exclusion to `_irrigate_linked_entities` (`irrigation.py`), add four service handlers to `DistributorMixin` + four `SERVICE_*`/two `ATTR_*` constants, register them in `services.py`, and document them in `services.yaml`.

**Tech Stack:** Python, Home Assistant services, pytest.

**Spec:** `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (§5.4, §10). Depends on Plans A–C (all landed): `DistributorMixin` with `async_run_distributor_cycle`/`async_run_distributor_test`/`async_distributor_set_outlet`/`async_distributor_resync_home`/`async_resume_distributor_cycles`, `store.get_distributor`, `const.ZONE_DISTRIBUTOR_ID`.

**Verified codebase facts (file:line):**
- Coordinator class + 9 mixins: `__init__.py:332-342`.
- Startup hook: `__init__.py:170-174` (`await coordinator.async_resume_self_closing_runs()`); service registration `__init__.py:256` (`async_register_services(hass)`).
- Service registration: `services.py:345` `async_register_services(hass)` → `coordinator = hass.data[const.DOMAIN]["coordinator"]` → `hass.services.async_register(const.DOMAIN, const.SERVICE_X, coordinator.handle_x)`.
- Handlers are `async def (self, call)` methods; `SmartIrrigationError` is in `const.py` (imported `from .const import SmartIrrigationError`).
- Zone-selection comprehension: `irrigation.py:452-466`.

**Test runner (verified):** from repo root:
```
PYTHONPATH="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad" "C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad/uvenv312/Scripts/python.exe" -m pytest tests/test_distributor_integration.py -p _local_socket_unblock -q
```
System Python (3.13) will NOT work. New tests go in `tests/test_distributor_integration.py`.

---

### Task 1: Wire `DistributorMixin` into the coordinator + startup resume hook

**Files:**
- Modify: `custom_components/smart_irrigation/__init__.py` (import + mixin list + resume hook)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_distributor_integration.py`:

```python
"""Distributor integration: coordinator wiring, zone exclusion, services."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const
from custom_components.smart_irrigation.distributor import DistributorMixin


def test_coordinator_inherits_distributor_mixin():
    assert issubclass(SmartIrrigationCoordinator, DistributorMixin)
    # the restart-reconciliation entry point is reachable on the coordinator
    assert hasattr(SmartIrrigationCoordinator, "async_resume_distributor_cycles")
```

- [ ] **Step 2: Run — expect FAIL** (`AssertionError` — the coordinator does not inherit `DistributorMixin` yet).

- [ ] **Step 3a: Import + add the mixin.** In `__init__.py`, next to the other mixin imports (e.g. `from .master import MasterMixin`, `from .self_closing import SelfClosingMixin`), add:

```python
from .distributor import DistributorMixin
```

Then add `DistributorMixin` to the class base list (after `MasterMixin`):

```python
class SmartIrrigationCoordinator(
    ServiceHandlersMixin,
    WateringCalendarMixin,
    IrrigationRunnerMixin,
    CalculationMixin,
    SkipConditionsMixin,
    LiveEstimateMixin,
    ObservedWateringMixin,
    SelfClosingMixin,
    MasterMixin,
    DistributorMixin,
):
```

- [ ] **Step 3b: Add the startup resume hook.** In `__init__.py` `async_setup_entry`, immediately AFTER:

```python
    # Reconcile any self-closing runs that were in flight across a restart.
    await coordinator.async_resume_self_closing_runs()
```

add:

```python
    # Reconcile any in-flight distributor cycles across a restart (before any
    # schedule can dispatch a new one).
    await coordinator.async_resume_distributor_cycles()
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/__init__.py tests/test_distributor_integration.py
git commit -m "feat(distributor): wire DistributorMixin + startup reconciliation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Exclude member zones from the normal watering path

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` (`_irrigate_linked_entities` comprehension, ~line 452)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append the failing test** to `tests/test_distributor_integration.py`:

```python
def _irrigation_coord(zones):
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = Mock()
    c.store = Mock()
    c.store.async_get_zones = AsyncMock(return_value=zones)
    c.store.config = SimpleNamespace(
        zone_sequencing=const.CONF_ZONE_SEQUENCING_PARALLEL,
        live_estimate_enabled=False,
    )
    c._sc_is_self_closing = Mock(return_value=False)
    c._rain_delay_active = Mock(return_value=False)
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda zs: zs)
    c._apply_live_durations = AsyncMock(side_effect=lambda zs: zs)
    c.async_master_begin_cycle = AsyncMock()
    c._master_note_run = Mock()
    c.async_master_schedule_off = AsyncMock()
    c._irrigate_zones_parallel = AsyncMock()
    return c


async def test_member_zone_excluded_from_normal_watering():
    # A member zone (distributor_id set, incl. 0!) with a STRAY linked entity
    # must NOT be watered by the normal path — the distributor owns it.
    normal = {
        const.ZONE_ID: 1,
        const.ZONE_LINKED_ENTITY: "switch.z1",
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 60,
        const.ZONE_BUCKET: -5,
        const.ZONE_BUCKET_THRESHOLD: 0,
        const.ZONE_DISTRIBUTOR_ID: None,
    }
    member = {
        const.ZONE_ID: 2,
        const.ZONE_LINKED_ENTITY: "switch.z2",  # stray/leftover
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 60,
        const.ZONE_BUCKET: -5,
        const.ZONE_BUCKET_THRESHOLD: 0,
        const.ZONE_DISTRIBUTOR_ID: 0,  # member of distributor 0 (note: id 0!)
    }
    c = _irrigation_coord([normal, member])
    await c._irrigate_linked_entities()
    dispatched = c._irrigate_zones_parallel.await_args.args[0]
    ids = {z[const.ZONE_ID] for z in dispatched}
    assert ids == {1}  # only the normal zone; member 0 excluded
```

- [ ] **Step 2: Run — expect FAIL** (the member zone is still dispatched → `ids == {1, 2}`).

- [ ] **Step 3: Add the exclusion.** In `irrigation.py`, in the `zones_to_irrigate = [...]` comprehension (~line 452), add a condition. The current comprehension is:

```python
        zones_to_irrigate = [
            z
            for z in zones
            if (z.get(const.ZONE_LINKED_ENTITY) or self._sc_is_self_closing(z))
            and z.get(const.ZONE_STATE) != const.ZONE_STATE_DISABLED
            and (target is None or int(z.get(const.ZONE_ID)) in target)
            and (
                live_gate
                or (
                    (z.get(const.ZONE_DURATION) or 0) > 0
                    and (z.get(const.ZONE_BUCKET) or 0)
                    < (z.get(const.ZONE_BUCKET_THRESHOLD) or 0)
                )
            )
        ]
```

Add `and z.get(const.ZONE_DISTRIBUTOR_ID) is None` as the FIRST condition after `for z in zones`. **Use `is None`, NOT `not z.get(...)`** — distributor ids start at 0 and `not 0` is truthy, which would wrongly include members of distributor 0. Result:

```python
        zones_to_irrigate = [
            z
            for z in zones
            if z.get(const.ZONE_DISTRIBUTOR_ID) is None
            and (z.get(const.ZONE_LINKED_ENTITY) or self._sc_is_self_closing(z))
            and z.get(const.ZONE_STATE) != const.ZONE_STATE_DISABLED
            and (target is None or int(z.get(const.ZONE_ID)) in target)
            and (
                live_gate
                or (
                    (z.get(const.ZONE_DURATION) or 0) > 0
                    and (z.get(const.ZONE_BUCKET) or 0)
                    < (z.get(const.ZONE_BUCKET_THRESHOLD) or 0)
                )
            )
        ]
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Run the existing irrigation/scheduler tests for regressions:**

Run: `pytest tests/test_run_zone.py tests/test_metered_run.py tests/test_soil_moisture_veto.py tests/test_rain_delay.py -p _local_socket_unblock -q` (via the wrapper).
Expected: PASS (member-zone exclusion doesn't affect normal-zone watering).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_distributor_integration.py
git commit -m "feat(distributor): exclude member zones from the normal watering path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Distributor service handlers + constants

**Files:**
- Modify: `custom_components/smart_irrigation/const.py` (append service/attr constants)
- Modify: `custom_components/smart_irrigation/distributor.py` (add handlers to `DistributorMixin`, after `async_resume_distributor_cycles`)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append the failing tests** to `tests/test_distributor_integration.py`:

```python
def _svc_coord(distributor):
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.store = Mock()
    c.store.get_distributor = Mock(return_value=distributor)
    c.async_distributor_set_outlet = AsyncMock()
    c.async_distributor_resync_home = AsyncMock()
    c.async_run_distributor_test = AsyncMock()
    c.async_run_distributor_cycle = AsyncMock()
    return c


def _call(**data):
    call = MagicMock()
    call.data = data
    return call


async def test_handle_set_outlet_calls_method():
    c = _svc_coord({"id": 0, "active_cycle": {}})
    await c.handle_distributor_set_outlet(
        _call(**{const.ATTR_DISTRIBUTOR_ID: 0, const.ATTR_OUTLET: 3})
    )
    c.async_distributor_set_outlet.assert_awaited_once_with(0, 3)


async def test_handle_resync_home_calls_method():
    c = _svc_coord({"id": 0, "active_cycle": {}})
    await c.handle_distributor_resync_home(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))
    c.async_distributor_resync_home.assert_awaited_once_with(0)


async def test_handle_test_run_calls_method():
    dist = {"id": 0, "active_cycle": {}}
    c = _svc_coord(dist)
    await c.handle_distributor_test_run(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))
    c.async_run_distributor_test.assert_awaited_once_with(dist)


async def test_handle_run_now_calls_cycle():
    dist = {"id": 0, "active_cycle": {}}
    c = _svc_coord(dist)
    await c.handle_distributor_run_now(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))
    c.async_run_distributor_cycle.assert_awaited_once_with(dist, concurrent=False)


async def test_handle_run_now_rejects_when_cycle_active():
    dist = {"id": 0, "active_cycle": {"outlet": 1, "phase": "watering"}}
    c = _svc_coord(dist)
    try:
        await c.handle_distributor_run_now(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))
        raised = False
    except const.SmartIrrigationError:
        raised = True
    assert raised is True
    c.async_run_distributor_cycle.assert_not_awaited()


async def test_handle_unknown_distributor_raises():
    c = _svc_coord(None)  # store.get_distributor returns None
    try:
        await c.handle_distributor_test_run(_call(**{const.ATTR_DISTRIBUTOR_ID: 99}))
        raised = False
    except const.SmartIrrigationError:
        raised = True
    assert raised is True
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'handle_distributor_set_outlet'` and missing consts).

- [ ] **Step 3a: Append constants to `const.py`** (near the other `SERVICE_*` constants):

```python
# Gardena distributor services
SERVICE_DISTRIBUTOR_SET_OUTLET = "distributor_set_outlet"
SERVICE_DISTRIBUTOR_RESYNC_HOME = "distributor_resync_home"
SERVICE_DISTRIBUTOR_TEST_RUN = "distributor_test_run"
SERVICE_DISTRIBUTOR_RUN_NOW = "distributor_run_now"
ATTR_DISTRIBUTOR_ID = "distributor_id"
ATTR_OUTLET = "outlet"
```

- [ ] **Step 3b: Add the handlers** to `DistributorMixin` in `distributor.py`, immediately AFTER `async_resume_distributor_cycles`:

```python
    # --- service handlers -------------------------------------------------

    def _dist_from_call(self, call) -> dict:
        """Resolve the distributor dict from a service call's distributor_id."""
        did = call.data.get(const.ATTR_DISTRIBUTOR_ID)
        if did is None:
            raise const.SmartIrrigationError("distributor_id is required")
        dist = self.store.get_distributor(did)
        if dist is None:
            raise const.SmartIrrigationError(f"No distributor with id {did}")
        return dist

    async def handle_distributor_set_outlet(self, call) -> None:
        """Service: re-sync the current outlet (user read the physical window)."""
        dist = self._dist_from_call(call)
        outlet = call.data.get(const.ATTR_OUTLET)
        if outlet is None:
            raise const.SmartIrrigationError("outlet is required")
        await self.async_distributor_set_outlet(dist["id"], int(outlet))

    async def handle_distributor_resync_home(self, call) -> None:
        """Service: re-sync to outlet 1."""
        dist = self._dist_from_call(call)
        await self.async_distributor_resync_home(dist["id"])

    async def handle_distributor_test_run(self, call) -> None:
        """Service: commissioning test-run (fixed short window per outlet)."""
        dist = self._dist_from_call(call)
        await self.async_run_distributor_test(dist)

    async def handle_distributor_run_now(self, call) -> None:
        """Service: run one full cycle now (manual, exclusive). Best-effort
        single-flight: rejected if a cycle is already in progress — a snapshot
        check on the persisted active_cycle at call time, adequate for a
        manually-invoked service (true locking is deferred to the scheduler plan)."""
        dist = self._dist_from_call(call)
        if dist.get("active_cycle"):
            raise const.SmartIrrigationError(
                f"Distributor {dist['id']} already has a cycle in progress"
            )
        await self.async_run_distributor_cycle(dist, concurrent=False)
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor_integration.py
git commit -m "feat(distributor): service handlers (set_outlet, resync_home, test_run, run_now)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Register the services + `services.yaml`

**Files:**
- Modify: `custom_components/smart_irrigation/services.py` (register 4 services in `async_register_services`)
- Modify: `custom_components/smart_irrigation/services.yaml` (document the 4 services)
- Test: `tests/test_distributor_integration.py`

- [ ] **Step 1: Append the failing test** to `tests/test_distributor_integration.py`:

```python
def test_distributor_services_are_registered():
    from custom_components.smart_irrigation.services import async_register_services

    coordinator = MagicMock(spec=SmartIrrigationCoordinator)
    hass = MagicMock()
    registered = []
    hass.services.async_register = lambda domain, service, handler: registered.append(
        service
    )
    hass.data = {const.DOMAIN: {"coordinator": coordinator}}

    async_register_services(hass)

    for svc in (
        const.SERVICE_DISTRIBUTOR_SET_OUTLET,
        const.SERVICE_DISTRIBUTOR_RESYNC_HOME,
        const.SERVICE_DISTRIBUTOR_TEST_RUN,
        const.SERVICE_DISTRIBUTOR_RUN_NOW,
    ):
        assert svc in registered
```

Note: `MagicMock(spec=SmartIrrigationCoordinator)` only allows attributes that exist on the real class — so this also proves the four `handle_distributor_*` handlers exist (Task 3).

- [ ] **Step 2: Run — expect FAIL** (the four services are not registered yet).

- [ ] **Step 3a: Register the services.** In `services.py` `async_register_services`, after the existing `hass.services.async_register(...)` calls (before the function ends), add:

```python
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISTRIBUTOR_SET_OUTLET,
        coordinator.handle_distributor_set_outlet,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISTRIBUTOR_RESYNC_HOME,
        coordinator.handle_distributor_resync_home,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISTRIBUTOR_TEST_RUN,
        coordinator.handle_distributor_test_run,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISTRIBUTOR_RUN_NOW,
        coordinator.handle_distributor_run_now,
    )
```

- [ ] **Step 3b: Document in `services.yaml`.** Append:

```yaml
distributor_set_outlet:
  name: Distributor — set current outlet
  description: Re-sync the distributor's outlet position to the value shown in its physical window. Marks the position as synced; you still confirm commissioning separately.
  fields:
    distributor_id:
      required: true
      example: 0
      description: "The distributor id."
      selector:
        number:
          min: 0
          max: 99
          mode: box
    outlet:
      required: true
      example: 1
      description: "The outlet number currently shown in the device window."
      selector:
        number:
          min: 1
          max: 6
          mode: box

distributor_resync_home:
  name: Distributor — re-sync to outlet 1
  description: Convenience re-sync of the distributor position to outlet 1 (after physically advancing the device to 1).
  fields:
    distributor_id:
      required: true
      example: 0
      description: "The distributor id."
      selector:
        number:
          min: 0
          max: 99
          mode: box

distributor_test_run:
  name: Distributor — commissioning test-run
  description: Sweep every outlet for a fixed short window so you can watch each zone water in order and the device advance. Requires a synced position; no watering is credited.
  fields:
    distributor_id:
      required: true
      example: 0
      description: "The distributor id."
      selector:
        number:
          min: 0
          max: 99
          mode: box

distributor_run_now:
  name: Distributor — run one cycle now
  description: Run one full distributor cycle immediately (manual). Requires the distributor to be synced and commissioning-confirmed; rejected if a cycle is already in progress.
  fields:
    distributor_id:
      required: true
      example: 0
      description: "The distributor id."
      selector:
        number:
          min: 0
          max: 99
          mode: box
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Run the service-registration + distributor suites for regressions:**

Run: `pytest tests/test_distributor_integration.py tests/test_services_registration.py tests/test_distributor.py tests/test_distributor_cycle.py -p _local_socket_unblock -q` (via the wrapper).
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/services.py custom_components/smart_irrigation/services.yaml tests/test_distributor_integration.py
git commit -m "feat(distributor): register services + services.yaml

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan D Self-Review

- **Spec coverage:** coordinator wiring + startup reconciliation (§5.4/§7) → Task 1; member-zone exclusion from `_irrigate_linked_entities`, with the `is None` (not `not`) fix (§5.4) → Task 2; services `set_outlet`/`resync_home`/`test_run`/`run_now` with the run_now single-flight guard (§10/§5.1) → Task 3+4.
- **Deferred to later plans:** Plan E — panel UI + i18n (the commissioning switch, test-run button, re-sync UI, zone→outlet mapping, visual-convention). Plan F — automatic schedule dispatch (schedule target discriminator + `_perform_schedule_action` branch + `concurrent` from the sequencing mode + finish-anchor `distributor_cycle_estimate`).
- **No placeholders:** every step has concrete code, exact commands, expected output.
- **Type consistency:** handlers are `async def (self, call)` on `DistributorMixin`, registered as `coordinator.handle_distributor_*`; they call the Plan-C `async_*` methods and `store.get_distributor` (Plan A). `const.ZONE_DISTRIBUTOR_ID` (Plan A), `SmartIrrigationError` (const.py), `CONF_ZONE_SEQUENCING_PARALLEL` (const.py) all exist. The `MagicMock(spec=SmartIrrigationCoordinator)` in the registration test enforces the handlers actually exist.

## Handoff to Plan E / Plan F

- **Plan E (UI + i18n):** create/configure distributors in the panel (fields from §4.1); zone→outlet mapping with the contiguous-1..n validation; the **test-run button**, **commissioning-confirmed switch (with popup)**, and **re-sync** UI; the parallel-mode + sequential/rotating-master-cycling hints; all strings in all 8 languages; reuse the existing panel look (§8 hard requirement). Consider per-distributor **entities** (a position/state sensor) so the services can optionally target an entity instead of a raw `distributor_id`.
- **Plan F (scheduling):** add a schedule target discriminator + a `_perform_schedule_action` branch calling `async_run_distributor_cycle(distributor, concurrent=<from sequencing mode>)`; wire `distributor_cycle_estimate` into the finish-anchor duration; promote the phase/reason string literals (`"watering"`/`"pausing"`/`"restart_mid_advance"`) to constants when the scheduler references them.
