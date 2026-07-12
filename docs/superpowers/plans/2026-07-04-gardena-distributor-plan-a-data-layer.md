# Gardena Distributor — Plan A: Data Layer & Persistence

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the persistent `Distributor` storage collection, the two zone-membership fields, and the v10→v11 migration — the data foundation the cycle engine (Plan B) and panel UI (Plan C) build on.

**Architecture:** Mirror the existing attrs-based store pattern in `store.py` exactly: a new frozen `DistributorEntry` class, a `self.distributors` `OrderedDict`, hydration in `async_load`, serialization in `_data_to_save`, a migration block, and CRUD methods — one-for-one copies of the zone/module/mapping machinery. No `Config` changes (avoids the strict-allowlist strip); the in-flight cycle record lives on the distributor entry (`active_cycle`).

**Tech Stack:** Python, `attr` (attrs), Home Assistant `Store`, pytest + `pytest-homeassistant-custom-component` (`hass` fixture).

**Spec:** `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (§4).

**Test runner note:** commands below use `pytest`. Run them in the project's configured test env (per memory: uv / Python 3.12 with the socket-unblock conftest). All new tests go in `tests/test_store_distributor.py`.

---

### Task 1: Position-state constants + `DistributorEntry` storage class

**Files:**
- Modify: `custom_components/smart_irrigation/const.py` (append constants)
- Modify: `custom_components/smart_irrigation/store.py` (add class after `Config`, ~line 324)
- Test: `tests/test_store_distributor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_store_distributor.py`:

```python
"""Store schema and CRUD for the Gardena distributor collection."""

from unittest.mock import AsyncMock

import attr

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.store import (
    STORAGE_VERSION,
    DistributorEntry,
    MigratableStore,
    SmartIrrigationStorage,
    ZoneEntry,
    async_get_registry,
)


def test_distributor_entry_defaults():
    d = DistributorEntry()
    assert d.id is None
    assert d.name is None
    assert d.watering_mode == "classic"
    assert d.inlet_entity is None
    assert d.run_service is None
    assert d.stop_service is None
    assert d.duration_field == "duration"
    assert d.duration_unit == "seconds"
    assert d.run_data == {}
    assert d.stop_data == {}
    assert d.confirm_entity is None
    assert d.flow_sensor is None
    assert d.pause_seconds == 300
    assert d.skip_pulse_seconds == 30
    assert d.current_outlet == 1
    # Fresh distributor is NEVER trusted as synced (spec §4.2).
    assert d.position_state == const.POSITION_STATE_UNCERTAIN
    assert d.notify_target is None
    assert d.use_master is True
    assert d.commissioning_confirmed is False
    assert d.schedules == []
    assert d.active_cycle == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_distributor.py::test_distributor_entry_defaults -v`
Expected: FAIL — `ImportError: cannot import name 'DistributorEntry'` (collection error).

- [ ] **Step 3a: Add the constants to `const.py`**

Append to the end of `custom_components/smart_irrigation/const.py`:

```python
# --- Gardena Wasserverteiler automatic (distributor) -------------------------
# Position-state of the open-loop outlet counter. A distributor only waters via
# a schedule when synced AND commissioning-confirmed (see store/engine).
POSITION_STATE_SYNCED = "synced"
POSITION_STATE_UNCERTAIN = "uncertain"

# Zone membership (a zone behind a distributor has no own valve/schedule).
ZONE_DISTRIBUTOR_ID = "distributor_id"
ZONE_OUTLET_NUMBER = "outlet_number"

# Hard floor for the pressure-bleed pause and the skip-pulse (spec §4.5): below
# this the device may silently fail to advance (undetectable open-loop desync).
DISTRIBUTOR_MIN_PAUSE_SECONDS = 10
DISTRIBUTOR_MIN_SKIP_PULSE_SECONDS = 10
DISTRIBUTOR_DEFAULT_PAUSE_SECONDS = 300
DISTRIBUTOR_DEFAULT_SKIP_PULSE_SECONDS = 30
# Fixed watering window per outlet during a commissioning test-run (spec §10).
DISTRIBUTOR_TEST_RUN_SECONDS = 30
```

- [ ] **Step 3b: Add the `DistributorEntry` class to `store.py`**

Insert immediately after the `Config` class (after its last attribute, `master_off_after`, ~line 324) and before `class MigratableStore`:

```python
@attr.s(slots=True, frozen=True)
class DistributorEntry:
    """Gardena distributor storage Entry (a shared, pressure-driven outlet ring).

    The inlet valve is actuated like a zone (classic / service). ``current_outlet``
    is counted open-loop and persisted after every advance; ``position_state`` and
    ``commissioning_confirmed`` gate whether a scheduled cycle may run. ``active_cycle``
    holds the in-flight-cycle record for restart reconciliation (empty when idle).
    """

    id = attr.ib(type=int, default=None)
    name = attr.ib(type=str, default=None)
    # Inlet-valve actuation, mirroring the zone watering-mode shapes.
    watering_mode = attr.ib(type=str, default="classic")
    inlet_entity = attr.ib(type=str, default=None)
    run_service = attr.ib(type=str, default=None)
    stop_service = attr.ib(type=str, default=None)
    duration_field = attr.ib(type=str, default="duration")
    duration_unit = attr.ib(type=str, default="seconds")
    run_data = attr.ib(type=dict, factory=dict)
    stop_data = attr.ib(type=dict, factory=dict)
    # Shared sensors, physically on the distributor inlet.
    confirm_entity = attr.ib(type=str, default=None)
    flow_sensor = attr.ib(type=str, default=None)
    # Timing (seconds); hard floor enforced by the engine (spec §4.5).
    pause_seconds = attr.ib(type=int, default=300)
    skip_pulse_seconds = attr.ib(type=int, default=30)
    # Open-loop position + trust state. Fresh distributors start uncertain (§4.2).
    current_outlet = attr.ib(type=int, default=1)
    position_state = attr.ib(type=str, default="uncertain")
    notify_target = attr.ib(type=str, default=None)
    use_master = attr.ib(type=bool, default=True)
    # Commissioning gate: no scheduled watering until confirmed (§5.1); the single
    # "armed" switch, auto-cleared on any transition to uncertain (§7).
    commissioning_confirmed = attr.ib(type=bool, default=False)
    # Distributor-local recurring schedules (wired in Plan B).
    schedules = attr.ib(type=list, factory=list)
    # In-flight cycle record for restart reconciliation (empty = idle).
    active_cycle = attr.ib(type=dict, factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_distributor.py::test_distributor_entry_defaults -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py tests/test_store_distributor.py
git commit -m "feat(distributor): DistributorEntry storage class + constants

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Zone membership fields (`distributor_id`, `outlet_number`)

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (`ZoneEntry` attrs ~line 224; `async_load` hydration ~line 706)
- Test: `tests/test_store_distributor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store_distributor.py`:

```python
def test_zone_entry_has_membership_fields():
    z = ZoneEntry()
    assert z.distributor_id is None
    assert z.outlet_number is None


async def test_zone_membership_survives_reload(hass):
    """Regression: distributor_id/outlet_number must be hydrated on load."""
    reg = await async_get_registry(hass)
    created = await reg.async_create_zone(
        {
            "name": "Ring-Zone",
            "size": 10.0,
            "throughput": 5.0,
            "distributor_id": 0,
            "outlet_number": 3,
        }
    )
    zone_id = created["id"]

    data = {
        "config": attr.asdict(reg.config),
        "zones": [attr.asdict(z) for z in reg.zones.values()],
        "modules": [],
        "mappings": [],
        "distributors": [],
    }
    fresh = SmartIrrigationStorage(hass)
    fresh._store.async_load = AsyncMock(return_value=data)
    await fresh.async_load()

    z = fresh.get_zone(zone_id)
    assert z["distributor_id"] == 0
    assert z["outlet_number"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_distributor.py::test_zone_entry_has_membership_fields tests/test_store_distributor.py::test_zone_membership_survives_reload -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'distributor_id'` (and the reload test AttributeError/KeyError).

- [ ] **Step 3a: Add the attrs to `ZoneEntry`**

In `store.py`, after the last `ZoneEntry` attribute (`soil_moisture_threshold`, ~line 224), add:

```python
    # Gardena distributor membership. None = a normal, independently-valved zone.
    # A member zone has no own valve/schedule; the distributor owns actuation.
    distributor_id = attr.ib(type=int, default=None)
    outlet_number = attr.ib(type=int, default=None)
```

- [ ] **Step 3b: Hydrate them in `async_load`**

In `store.py`, inside the `ZoneEntry(...)` construction in `async_load`, after the `soil_moisture_threshold=zone.get("soil_moisture_threshold", None),` line (~line 707), add:

```python
                        distributor_id=zone.get("distributor_id", None),
                        outlet_number=zone.get("outlet_number", None),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_distributor.py::test_zone_entry_has_membership_fields tests/test_store_distributor.py::test_zone_membership_survives_reload -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/store.py tests/test_store_distributor.py
git commit -m "feat(distributor): zone membership fields (distributor_id, outlet_number)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Storage migration v10 → v11

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (`STORAGE_VERSION` line 158; migration block in `_async_migrate_func` after the `old_version <= 9` block, ~line 407)
- Test: `tests/test_store_distributor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store_distributor.py`:

```python
def test_storage_version_is_11():
    assert STORAGE_VERSION == 11


async def test_migration_v10_adds_distributors_and_zone_fields(hass):
    store = MigratableStore(hass, STORAGE_VERSION, "smart_irrigation.storage")
    old = {
        "config": {},
        "zones": [{"id": 0, "name": "A"}, {"id": 1, "name": "B"}],
        "modules": [],
        "mappings": [],
    }
    migrated = await store._async_migrate_func(10, old)
    assert migrated["distributors"] == []
    for z in migrated["zones"]:
        assert z["distributor_id"] is None
        assert z["outlet_number"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_distributor.py::test_storage_version_is_11 tests/test_store_distributor.py::test_migration_v10_adds_distributors_and_zone_fields -v`
Expected: FAIL — `assert 10 == 11` and `KeyError: 'distributors'`.

- [ ] **Step 3a: Bump the storage version**

In `store.py` line 158, change:

```python
STORAGE_VERSION = 11
```

- [ ] **Step 3b: Add the migration block**

In `_async_migrate_func`, immediately after the `if old_version <= 9:` block (ends ~line 406, before the `# CRITICAL:` comment ~line 408), add:

```python
        if old_version <= 10:
            # v11: Gardena distributor support. Additive only — create the empty
            # distributors collection and the zone membership fields. No config
            # keys are added (distributors are a top-level collection), so the
            # config-allowlist strip below leaves them untouched.
            data.setdefault("distributors", [])
            for zone in data.get("zones", []):
                zone.setdefault("distributor_id", None)
                zone.setdefault("outlet_number", None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_distributor.py::test_storage_version_is_11 tests/test_store_distributor.py::test_migration_v10_adds_distributors_and_zone_fields -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/store.py tests/test_store_distributor.py
git commit -m "feat(distributor): storage migration v10 -> v11

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `distributors` collection wiring (init / load / save)

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (`__init__` ~line 483; `async_load` locals ~line 506 and hydration after the `mappings` block ~line 754; `_data_to_save` ~line 881)
- Test: `tests/test_store_distributor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store_distributor.py`:

```python
async def test_distributor_collection_round_trip(hass):
    """A distributor placed in the collection survives a save/load round-trip."""
    reg = await async_get_registry(hass)
    reg.distributors[0] = DistributorEntry(
        id=0,
        name="Garten",
        watering_mode="service",
        run_service="script.distributor_inlet",
        pause_seconds=120,
        skip_pulse_seconds=20,
        current_outlet=2,
        position_state=const.POSITION_STATE_SYNCED,
        commissioning_confirmed=True,
    )

    data = reg._data_to_save()
    assert "distributors" in data
    assert data["distributors"][0]["name"] == "Garten"

    fresh = SmartIrrigationStorage(hass)
    fresh._store.async_load = AsyncMock(return_value=data)
    await fresh.async_load()

    d = fresh.distributors[0]
    assert d.name == "Garten"
    assert d.watering_mode == "service"
    assert d.run_service == "script.distributor_inlet"
    assert d.pause_seconds == 120
    assert d.skip_pulse_seconds == 20
    assert d.current_outlet == 2
    assert d.position_state == const.POSITION_STATE_SYNCED
    assert d.commissioning_confirmed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_distributor.py::test_distributor_collection_round_trip -v`
Expected: FAIL — `KeyError: 'distributors'` from `_data_to_save` (it does not persist the collection yet).

- [ ] **Step 3a: Initialise the collection**

In `SmartIrrigationStorage.__init__` (after `self.mappings: MutableMapping[MappingEntry] = {}`, ~line 483), add:

```python
        self.distributors: MutableMapping[DistributorEntry] = {}
```

- [ ] **Step 3b: Add the local OrderedDict in `async_load`**

After `mappings: OrderedDict[str, MappingEntry] = OrderedDict()` (~line 506), add:

```python
        distributors: OrderedDict[str, DistributorEntry] = OrderedDict()
```

- [ ] **Step 3c: Hydrate distributors**

In `async_load`, immediately after the `if "mappings" in data:` block (ends ~line 754, before `self.config = config`), add:

```python
            if "distributors" in data:
                for dist in data["distributors"]:
                    distributors[dist["id"]] = DistributorEntry(
                        id=dist["id"],
                        name=dist.get("name"),
                        watering_mode=dist.get("watering_mode", "classic"),
                        inlet_entity=dist.get("inlet_entity", None),
                        run_service=dist.get("run_service", None),
                        stop_service=dist.get("stop_service", None),
                        duration_field=dist.get("duration_field", "duration"),
                        duration_unit=dist.get("duration_unit", "seconds"),
                        run_data=dist.get("run_data", {}) or {},
                        stop_data=dist.get("stop_data", {}) or {},
                        confirm_entity=dist.get("confirm_entity", None),
                        flow_sensor=dist.get("flow_sensor", None),
                        pause_seconds=dist.get("pause_seconds", 300),
                        skip_pulse_seconds=dist.get("skip_pulse_seconds", 30),
                        current_outlet=dist.get("current_outlet", 1),
                        position_state=dist.get("position_state", "uncertain"),
                        notify_target=dist.get("notify_target", None),
                        use_master=dist.get("use_master", True),
                        commissioning_confirmed=dist.get(
                            "commissioning_confirmed", False
                        ),
                        schedules=dist.get("schedules", []) or [],
                        active_cycle=dist.get("active_cycle", {}) or {},
                    )
```

- [ ] **Step 3d: Assign the collection at the end of `async_load`**

After `self.mappings = mappings` (~line 759), add:

```python
        self.distributors = distributors
```

- [ ] **Step 3e: Persist the collection in `_data_to_save`**

In `_data_to_save`, after the `store_data["mappings"] = [...]` assignment (~line 881) and before `return store_data`, add:

```python
        store_data["distributors"] = [
            attr.asdict(entry) for entry in self.distributors.values()
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_distributor.py::test_distributor_collection_round_trip -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/store.py tests/test_store_distributor.py
git commit -m "feat(distributor): persist the distributors collection (init/load/save)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Distributor CRUD methods

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (add methods after `async_update_zone`, ~line 987)
- Test: `tests/test_store_distributor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store_distributor.py`:

```python
async def test_create_distributor_assigns_id_and_defaults_uncertain(hass):
    reg = await async_get_registry(hass)
    created = await reg.async_create_distributor({"name": "Garten"})
    assert created["id"] == 0
    assert created["name"] == "Garten"
    # A freshly created distributor is never trusted (spec §4.2).
    assert created["position_state"] == const.POSITION_STATE_UNCERTAIN
    assert created["commissioning_confirmed"] is False

    second = await reg.async_create_distributor({"name": "Vorgarten"})
    assert second["id"] == 1


async def test_create_distributor_ignores_unknown_keys(hass):
    reg = await async_get_registry(hass)
    created = await reg.async_create_distributor(
        {"name": "Garten", "not_a_field": "bogus"}
    )
    assert "not_a_field" not in created
    assert created["name"] == "Garten"


async def test_update_and_get_distributor(hass):
    reg = await async_get_registry(hass)
    created = await reg.async_create_distributor({"name": "Garten"})
    did = created["id"]

    updated = await reg.async_update_distributor(
        did, {"current_outlet": 4, "position_state": const.POSITION_STATE_SYNCED}
    )
    assert updated["current_outlet"] == 4
    assert updated["position_state"] == const.POSITION_STATE_SYNCED

    got = reg.get_distributor(did)
    assert got["current_outlet"] == 4
    assert reg.get_distributor(999) is None


async def test_delete_distributor(hass):
    reg = await async_get_registry(hass)
    created = await reg.async_create_distributor({"name": "Garten"})
    did = created["id"]
    assert await reg.async_delete_distributor(did) is True
    assert reg.get_distributor(did) is None
    assert await reg.async_delete_distributor(did) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_distributor.py -k distributor -v`
Expected: FAIL — `AttributeError: 'SmartIrrigationStorage' object has no attribute 'async_create_distributor'`.

- [ ] **Step 3: Add the CRUD methods**

In `store.py`, after `async_update_zone` (ends ~line 987) and before `get_module` (~line 989), add:

```python
    @callback
    def get_distributor(self, distributor_id) -> "DistributorEntry":
        """Get an existing DistributorEntry by id."""
        if distributor_id is not None:
            res = self.distributors.get(int(distributor_id))
            return attr.asdict(res) if res else None
        return None

    async def async_get_distributors(self):
        """Get all DistributorEntries."""
        return [attr.asdict(val) for val in self.distributors.values()]

    async def async_create_distributor(self, data: dict) -> "DistributorEntry":
        """Create a new DistributorEntry (unknown keys dropped)."""
        valid_fields = set(attr.fields_dict(DistributorEntry).keys())
        new_dist = DistributorEntry(
            **{k: v for k, v in data.items() if k in valid_fields}
        )
        if not new_dist.id:
            distributors = await self.async_get_distributors()
            new_dist = attr.evolve(
                new_dist, id=self.generate_next_id(distributors)
            )
        self.distributors[int(new_dist.id)] = new_dist
        self.async_schedule_save()
        return attr.asdict(new_dist)

    async def async_delete_distributor(self, distributor_id) -> bool:
        """Delete a DistributorEntry."""
        distributor_id = int(distributor_id)
        if distributor_id in self.distributors:
            del self.distributors[distributor_id]
            self.async_schedule_save()
            return True
        return False

    async def async_update_distributor(
        self, distributor_id, changes: dict
    ) -> "DistributorEntry":
        """Update an existing distributor (unknown keys dropped)."""
        distributor_id = int(distributor_id)
        old = self.distributors[distributor_id]
        changes.pop("id", None)
        valid_fields = set(attr.fields_dict(type(old)).keys())
        filtered = {k: v for k, v in changes.items() if k in valid_fields}
        new = self.distributors[distributor_id] = attr.evolve(old, **filtered)
        self.async_schedule_save()
        return attr.asdict(new)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_distributor.py -k distributor -v`
Expected: PASS (all distributor tests).

- [ ] **Step 5: Run the full store suite for regressions**

Run: `pytest tests/test_store_distributor.py tests/test_store.py tests/test_store_operations.py tests/test_store_self_closing.py -v`
Expected: PASS (no regressions in existing store tests).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/store.py tests/test_store_distributor.py
git commit -m "feat(distributor): store CRUD (get/create/update/delete)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan A Self-Review

- **Spec coverage (§4):** DistributorEntry fields (§4.1) → Task 1; fresh=uncertain default (§4.2) → Task 1 + Task 5; zone membership + hydration footgun (§4.3/§4.4) → Task 2; migration v10→v11 (§4.4) → Task 3; four store insertion points + no Config key (§4.4) → Task 4; CRUD → Task 5. Mapping-validation *enforcement* and the in-flight-cycle *population* are Plan B/C (this plan only defines the `active_cycle` field + `outlet_number`/`distributor_id` storage). Duration-floor *constants* are defined here (Task 1); enforcement is Plan B.
- **No placeholders:** every step has concrete code, exact commands, expected output.
- **Type consistency:** `DistributorEntry` field names are identical across Task 1 (class), Task 4 (hydration keys), and Task 5 (CRUD via `attr.fields_dict`). `position_state` default literal `"uncertain"` equals `const.POSITION_STATE_UNCERTAIN`. Distributor ids are `int`, keyed as `int(...)`, matching the zone pattern.

## Handoff to Plan B

After Plan A lands (all tests green), Plan B (cycle engine, master primitives, recovery, services, schedule binding) is written against these real signatures: `store.async_create_distributor/async_update_distributor/async_get_distributors/get_distributor`, `DistributorEntry.active_cycle`, `const.POSITION_STATE_*`, `const.DISTRIBUTOR_MIN_*`, and `ZoneEntry.distributor_id/outlet_number`.
