# Distributor Device + Entities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose each Gardena distributor as a HA device (like per-zone devices) with dynamic per-used-outlet zone sensors, a current-outlet sensor, `commissioned` + `watering_now` binary sensors, and a test-run button.

**Architecture:** Mirror the existing zone dispatcher pattern. A new `distributor_entity.py` holds a shared entity base + pure reconcile helpers. Three new dispatcher signals (`_distributor_register_entity`, `_distributor_updated`, `_distributor_removed`) are fired from the coordinator layer (never the store — matching `async_update_zone_config`). The three existing platform files (`sensor.py`, `binary_sensor.py`, `button.py`) gain distributor entities and a reconcile/removal handler that adds/removes the variable-count outlet sensors via the entity registry.

**Tech Stack:** Home Assistant custom integration, Python 3.12/3.13, pytest + `unittest.mock`. Entities are plain HA entities (NOT `CoordinatorEntity`); they read `store.get_distributor(id)` / `store.get_zone(id)` and refresh on dispatcher signals.

**Test env (verbatim):**
```
S="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad"
PYTHONPATH="$S" "$S/uvenv312/Scripts/python.exe" -m pytest <path> -p _local_socket_unblock -q
```
Format with `uvx black`; keep `uvx black --check custom_components/smart_irrigation/` clean.

**Verified source patterns (2026-07-05):**
- `entity.py:36-50` `zone_device_info()` — dict with `identifiers`, `name`, `model`, `manufacturer`, `via_device`; `coordinator_id(hass)` at 14-22.
- `binary_sensor.py:46-142` — `async_setup_entry` subscribes `DOMAIN + "_register_entity"`; tracker `hass.data[DOMAIN].setdefault("zone_binary_sensors", {})` keyed by `config["id"]`; base class `SmartIrrigationZoneBinarySensor` (`_attr_has_entity_name=True`, `unique_id = f"{DOMAIN}_{zone_id}_{suffix}"`, `device_info`, `_async_zone_updated` on `DOMAIN + "_config_updated"`, `async_added_to_hass`).
- `button.py:34-122` — same shape for buttons; `SmartIrrigationZoneButton`, `async_add_button_entity`.
- `__init__.py:591-596` `setup_SmartIrrigation_entities()` replays each zone via `DOMAIN + "_register_entity"`; `__init__.py:1337-1349` `async_update_zone_config` updates a zone then fires `DOMAIN + "_config_updated", zone_id`, or creates + fires `_register_entity`.
- `distributor.py:359-369` `_dist_persist_cycle` / `_dist_clear_cycle` call `self.store.async_update_distributor(...)`; `async_upsert_distributor` at 661-683 (create/update/delete). `async_run_distributor_test(distributor)` exists.
- `store.py:1091-1124` `async_create_distributor` / `async_delete_distributor` / `async_update_distributor` — mutate + `async_schedule_save()`, NO dispatch.

---

## File Structure

- **Create** `custom_components/smart_irrigation/distributor_entity.py` — shared `DistributorEntityBase` mixin + pure helpers `used_outlets(hass, distributor_id)` and `outlet_reconcile_diff(used, existing)`.
- **Modify** `custom_components/smart_irrigation/entity.py` — add `distributor_device_info()`.
- **Modify** `custom_components/smart_irrigation/distributor.py` — add `_dist_store_update()` (persist + fire `_distributor_updated`), route the in-cycle persists through it, and fire register/updated/removed from `async_upsert_distributor`.
- **Modify** `custom_components/smart_irrigation/__init__.py` — `setup_SmartIrrigation_entities` replays distributors; `async_update_zone_config` fires `_distributor_updated` for a member zone's distributor(s).
- **Modify** `custom_components/smart_irrigation/sensor.py` — current-outlet sensor + dynamic outlet-zone sensors + reconcile/removal handler.
- **Modify** `custom_components/smart_irrigation/binary_sensor.py` — `commissioned` + `watering_now` distributor sensors.
- **Modify** `custom_components/smart_irrigation/button.py` — test-run button.
- **Modify** `custom_components/smart_irrigation/translations/*.json` (8) — new entity keys.
- **Create** `tests/test_distributor_entities.py` — value logic, device_info, reconcile diff, signal firing.

---

### Task I1: Device info + pure reconcile helpers

**Files:**
- Modify: `custom_components/smart_irrigation/entity.py`
- Create: `custom_components/smart_irrigation/distributor_entity.py`
- Test: `tests/test_distributor_entities.py`

- [ ] **Step 1: Write the failing test** (`tests/test_distributor_entities.py`)

```python
from unittest.mock import Mock

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.entity import distributor_device_info
from custom_components.smart_irrigation.distributor_entity import (
    outlet_reconcile_diff,
    used_outlets,
)


def _hass_with_zones(zones):
    hass = Mock()
    coord = Mock()
    coord.id = "cid"
    coord.store.get_zone = lambda zid: next((z for z in zones if z["id"] == zid), None)
    coord.store.get_distributor = lambda did: None
    hass.data = {const.DOMAIN: {"coordinator": coord}}
    return hass


def test_distributor_device_info_identifiers_and_via_device():
    hass = _hass_with_zones([])
    info = distributor_device_info(hass, 0, "Gardena1")
    assert info["identifiers"] == {(const.DOMAIN, "cid_distributor_0")}
    assert info["name"] == "Gardena1"
    assert info["via_device"] == (const.DOMAIN, "cid")


def test_used_outlets_from_member_zones():
    zones = [
        {"id": 7, "distributor_id": 0, "outlet_number": 1, "name": "A"},
        {"id": 8, "distributor_id": 0, "outlet_number": 3, "name": "B"},
        {"id": 9, "distributor_id": 1, "outlet_number": 1, "name": "C"},
        {"id": 1, "distributor_id": None, "outlet_number": None, "name": "N"},
    ]
    hass = Mock()
    coord = Mock()
    coord.store.async_get_zones = None
    hass.data = {const.DOMAIN: {"coordinator": coord}}
    # used_outlets reads store.get_zones() sync snapshot
    coord.store.get_zones = lambda: zones
    assert used_outlets(hass, 0) == {1, 3}
    assert used_outlets(hass, 1) == {1}
    assert used_outlets(hass, 2) == set()


def test_outlet_reconcile_diff():
    assert outlet_reconcile_diff({1, 2, 3}, {1}) == ({2, 3}, set())      # grow
    assert outlet_reconcile_diff({1}, {1, 2, 3}) == (set(), {2, 3})      # shrink
    assert outlet_reconcile_diff({1, 2}, {1, 2}) == (set(), set())       # stable
```

- [ ] **Step 2: Run to verify it fails**

Run: `... tests/test_distributor_entities.py -q`
Expected: FAIL — `ImportError` (`distributor_device_info`, `outlet_reconcile_diff`, `used_outlets` not defined).

- [ ] **Step 3: Implement**

Append to `entity.py`:
```python
def distributor_device_info(hass: HomeAssistant, distributor_id, distributor_name: str) -> dict:
    """A per-distributor device, parented to the hub via ``via_device``."""
    cid = coordinator_id(hass)
    return {
        "identifiers": {(const.DOMAIN, f"{cid}_distributor_{distributor_id}")},
        "name": distributor_name,
        "model": "Gardena water distributor",
        "manufacturer": const.MANUFACTURER,
        "via_device": (const.DOMAIN, cid),
    }
```

Create `distributor_entity.py`:
```python
"""Shared base + pure helpers for per-distributor entities.

Distributor entities mirror the zone entities: they group under a per-distributor
device (``entity.distributor_device_info``), read the store directly, and refresh
on the ``DOMAIN + "_distributor_updated"`` dispatcher signal. The variable number
of per-outlet sensors is reconciled with ``outlet_reconcile_diff``.
"""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import const
from .entity import distributor_device_info


def _store(hass: HomeAssistant):
    """The store, or None when the integration is not (yet) set up."""
    try:
        return hass.data[const.DOMAIN]["coordinator"].store
    except (KeyError, AttributeError):
        return None


def _member_zones(hass: HomeAssistant, distributor_id) -> list:
    """Member zone dicts of a distributor (snapshot from the store)."""
    store = _store(hass)
    if store is None:
        return []
    zones = store.get_zones()
    return [z for z in zones if z.get(const.ZONE_DISTRIBUTOR_ID) == distributor_id]


def used_outlets(hass: HomeAssistant, distributor_id) -> set:
    """Outlet numbers that currently have a member zone assigned."""
    return {
        int(z[const.ZONE_OUTLET_NUMBER])
        for z in _member_zones(hass, distributor_id)
        if z.get(const.ZONE_OUTLET_NUMBER) is not None
    }


def outlet_reconcile_diff(used: set, existing: set):
    """(outlets_to_add, outlets_to_remove) to make ``existing`` match ``used``."""
    return (used - existing, existing - used)


def zone_on_outlet(hass: HomeAssistant, distributor_id, outlet_number):
    """The member zone dict on a given outlet, or None."""
    for z in _member_zones(hass, distributor_id):
        if z.get(const.ZONE_OUTLET_NUMBER) == outlet_number:
            return z
    return None


class DistributorEntityBase:
    """Base for per-distributor entities (distributor device + store refresh)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    suffix = ""

    def __init__(self, hass: HomeAssistant, entity_id: str, distributor: dict) -> None:
        """Initialize from a distributor dict."""
        self._hass = hass
        self.entity_id = entity_id
        self._distributor_id = distributor["id"]
        self._distributor_name = distributor.get("name") or f"Distributor {self._distributor_id}"
        self._distributor = distributor
        self._refresh(distributor)
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_updated", self._async_distributor_updated
        )

    def _refresh(self, distributor: dict) -> None:
        """Pull this entity's value(s) from the distributor dict (override)."""

    @callback
    def _async_distributor_updated(self, distributor_id=None):
        """Refresh from the store when this distributor changes."""
        if self._distributor_id != distributor_id or not (self.hass and self.hass.data):
            return
        store = _store(self.hass)
        dist = store.get_distributor(self._distributor_id) if store else None
        if dist:
            self._distributor_name = dist.get("name", self._distributor_name)
            self._distributor = dist
            self._refresh(dist)
            self.async_schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{const.DOMAIN}_distributor_{self._distributor_id}_{self.suffix}"

    @property
    def device_info(self) -> dict:
        return distributor_device_info(self._hass, self._distributor_id, self._distributor_name)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_schedule_update_ha_state()
```

> `store.get_zones()` (sync snapshot) is used by the helpers. Verify it exists in `store.py`; if only `async_get_zones` exists, add a tiny sync `get_zones(self): return [attr.asdict(z) for z in self.zones.values()]` to the store (mirror `get_zone`). Do this in Step 3 and note it in the commit.

- [ ] **Step 4: Run to verify it passes**

Run: `... tests/test_distributor_entities.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/entity.py custom_components/smart_irrigation/distributor_entity.py tests/test_distributor_entities.py custom_components/smart_irrigation/store.py
git commit -m "feat(distributor): device_info + entity base + reconcile helpers"
```

---

### Task I2: Coordinator signal plumbing

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (`_dist_persist_cycle`, `_dist_clear_cycle`, any other in-cycle `store.async_update_distributor` call, `async_upsert_distributor`)
- Modify: `custom_components/smart_irrigation/__init__.py` (`setup_SmartIrrigation_entities`, `async_update_zone_config`)
- Test: `tests/test_distributor_entities.py`

- [ ] **Step 1: Write the failing test** (append)

```python
import types
from unittest.mock import AsyncMock

from tests.test_distributor import _host, _dist   # reuse fixtures


async def test_persist_cycle_fires_distributor_updated(monkeypatch):
    c = _host()
    sent = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.distributor.async_dispatcher_send",
        lambda hass, signal, *a: sent.append((signal, a)),
    )
    c.store.async_update_distributor = AsyncMock()
    await c._dist_persist_cycle(0, 2, "watering")
    assert (const.DOMAIN + "_distributor_updated", (0,)) in sent


async def test_upsert_create_fires_register(monkeypatch):
    c = _host()
    sent = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.distributor.async_dispatcher_send",
        lambda hass, signal, *a: sent.append((signal, a)),
    )
    c.store.get_distributor = Mock(return_value=None)
    c.store.async_create_distributor = AsyncMock(return_value={"id": 5, "name": "New"})
    await c.async_upsert_distributor({"name": "New"})
    assert sent[-1][0] == const.DOMAIN + "_distributor_register_entity"


async def test_upsert_delete_fires_removed(monkeypatch):
    c = _host()
    sent = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.distributor.async_dispatcher_send",
        lambda hass, signal, *a: sent.append((signal, a)),
    )
    c.store.get_distributor = Mock(return_value={"id": 3})
    c.store.async_delete_distributor = AsyncMock(return_value=True)
    await c.async_upsert_distributor({"id": 3, "remove": True})
    assert (const.DOMAIN + "_distributor_removed", (3,)) in sent
```

- [ ] **Step 2: Run to verify it fails**

Run: `... tests/test_distributor_entities.py -k "fires" -q`
Expected: FAIL — no dispatch happens today.

- [ ] **Step 3: Implement**

In `distributor.py`, confirm the module imports `async_dispatcher_send` (grep; if not, add `from homeassistant.helpers.dispatcher import async_dispatcher_send`). Add a wrapper near `_dist_persist_cycle`:
```python
    async def _dist_store_update(self, distributor_id, changes: dict):
        """Persist a distributor change AND notify its HA entities."""
        res = await self.store.async_update_distributor(distributor_id, changes)
        async_dispatcher_send(
            self.hass, const.DOMAIN + "_distributor_updated", int(distributor_id)
        )
        return res
```
Replace **every** `await self.store.async_update_distributor(...)` call inside `distributor.py` (grep for it — `_dist_persist_cycle`, `_dist_clear_cycle`, `_dist_advance`, `_dist_mark_uncertain`, set-outlet / resync handlers, and the update branch of `async_upsert_distributor`) with `await self._dist_store_update(...)`. Same args.

In `async_upsert_distributor`, add register/removed dispatches (the update branch already dispatches `_distributor_updated` via `_dist_store_update`):
```python
            if remove:
                res = await self.store.async_delete_distributor(did)
                async_dispatcher_send(
                    self.hass, const.DOMAIN + "_distributor_removed", int(did)
                )
                return res
            data.pop("id")
            data.pop(const.ATTR_REMOVE, None)
            return await self._dist_store_update(did, data)
        created = await self.store.async_create_distributor(data)
        async_dispatcher_send(
            self.hass, const.DOMAIN + "_distributor_register_entity", created
        )
        return created
```

In `__init__.py` `setup_SmartIrrigation_entities` (after the zone replay loop, ~line 596):
```python
        for distributor in await self.store.async_get_distributors():
            async_dispatcher_send(
                self.hass, const.DOMAIN + "_distributor_register_entity", distributor
            )
```

In `__init__.py` `async_update_zone_config`, in the "modify a zone" branch (~line 1337-1340), capture the old distributor id before the update and notify both old + new distributor(s):
```python
        elif zone_id is not None and self.store.get_zone(zone_id):
            old_zone = self.store.get_zone(zone_id)
            entry = await self.store.async_update_zone(zone_id, data)
            async_dispatcher_send(self.hass, const.DOMAIN + "_config_updated", zone_id)
            for did in {
                old_zone.get(const.ZONE_DISTRIBUTOR_ID),
                entry.get(const.ZONE_DISTRIBUTOR_ID),
            }:
                if did is not None:
                    async_dispatcher_send(
                        self.hass, const.DOMAIN + "_distributor_updated", int(did)
                    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `... tests/test_distributor_entities.py -q`
Expected: PASS. Also run `... tests/test_distributor.py tests/test_distributor_dispatch.py -q` — no regressions (the persist/clear tests still pass; `_dist_store_update` is a transparent wrapper).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/__init__.py tests/test_distributor_entities.py
git commit -m "feat(distributor): fire register/updated/removed entity signals"
```

---

### Task I3: Current-outlet sensor + dynamic outlet-zone sensors (sensor.py)

**Files:**
- Modify: `custom_components/smart_irrigation/sensor.py`
- Test: `tests/test_distributor_entities.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from custom_components.smart_irrigation.sensor import (
    SmartIrrigationDistributorCurrentOutletSensor,
    SmartIrrigationDistributorOutletZoneSensor,
)


def _hass_full(zones, distributor):
    hass = Mock()
    coord = Mock()
    coord.id = "cid"
    coord.store.get_zones = lambda: zones
    coord.store.get_distributor = lambda did: distributor if did == distributor["id"] else None
    hass.data = {const.DOMAIN: {"coordinator": coord}}
    return hass


def test_current_outlet_sensor_value_and_attrs():
    dist = {"id": 0, "name": "G1", "current_outlet": 3,
            "position_state": "synced", "active_cycle": {"outlet": 3, "phase": "watering"}}
    hass = _hass_full([], dist)
    s = SmartIrrigationDistributorCurrentOutletSensor(hass, "sensor.g1_current_outlet", dist)
    assert s.native_value == 3
    assert s.extra_state_attributes["position_state"] == "synced"
    assert s.extra_state_attributes["phase"] == "watering"


def test_outlet_zone_sensor_resolves_zone_name():
    zones = [{"id": 7, "distributor_id": 0, "outlet_number": 2, "name": "Beet"}]
    dist = {"id": 0, "name": "G1", "current_outlet": 1, "active_cycle": {}}
    hass = _hass_full(zones, dist)
    s = SmartIrrigationDistributorOutletZoneSensor(hass, "sensor.g1_outlet_2_zone", dist, 2)
    assert s.native_value == "Beet"
    assert s.extra_state_attributes["zone_id"] == 7
    assert s.extra_state_attributes["outlet_number"] == 2
    assert s._attr_translation_placeholders == {"outlet": "2"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `... tests/test_distributor_entities.py -k "outlet" -q`
Expected: FAIL — `ImportError` (classes not defined).

- [ ] **Step 3: Implement** — add to `sensor.py`

Add imports at the top (mirror existing): `from .entity import ... ` already imports device_info helpers — add `from .distributor_entity import DistributorEntityBase, used_outlets, outlet_reconcile_diff, zone_on_outlet`. Import `slugify` if not present. Import the entity registry: `from homeassistant.helpers import entity_registry as er`.

Entity classes:
```python
class SmartIrrigationDistributorCurrentOutletSensor(DistributorEntityBase, SensorEntity):
    """The distributor's current ring position (1..n)."""

    suffix = "current_outlet"
    _attr_translation_key = "current_outlet"
    _attr_icon = "mdi:valve"

    def _refresh(self, distributor: dict) -> None:
        self._current = distributor.get("current_outlet")
        self._position_state = distributor.get("position_state")
        cycle = distributor.get("active_cycle") or {}
        self._phase = cycle.get("phase", "idle")

    @property
    def native_value(self):
        return self._current

    @property
    def extra_state_attributes(self) -> dict:
        zone = zone_on_outlet(self._hass, self._distributor_id, self._current)
        return {
            "position_state": self._position_state,
            "phase": self._phase,
            "zone_id": zone.get(const.ZONE_ID) if zone else None,
            "zone_name": zone.get(const.ZONE_NAME) if zone else None,
        }


class SmartIrrigationDistributorOutletZoneSensor(DistributorEntityBase, SensorEntity):
    """The zone connected to one outlet (state = zone name)."""

    _attr_translation_key = "outlet_zone"
    _attr_icon = "mdi:pipe-valve"

    def __init__(self, hass, entity_id, distributor: dict, outlet_number: int) -> None:
        self._outlet_number = int(outlet_number)
        self.suffix = f"outlet_{self._outlet_number}_zone"
        self._attr_translation_placeholders = {"outlet": str(self._outlet_number)}
        super().__init__(hass, entity_id, distributor)

    def _refresh(self, distributor: dict) -> None:
        self._zone = zone_on_outlet(self._hass, self._distributor_id, self._outlet_number)

    @property
    def native_value(self):
        return self._zone.get(const.ZONE_NAME) if self._zone else None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "zone_id": self._zone.get(const.ZONE_ID) if self._zone else None,
            "outlet_number": self._outlet_number,
        }
```

Reconcile + wiring in `async_setup_entry` (add alongside the existing zone subscription):
```python
    @callback
    def async_add_distributor_sensors(distributor: dict) -> None:
        if const.DOMAIN not in hass.data:
            return
        tracker = hass.data[const.DOMAIN].setdefault("distributor_sensors", {})
        did = distributor["id"]
        slot = tracker.setdefault(did, {"current": None, "outlets": {}})
        base = "{}.{}_distributor_{}".format(
            PLATFORM, const.DOMAIN, slugify(distributor.get("name") or f"d{did}")
        )
        new = []
        if slot["current"] is None:
            cur = SmartIrrigationDistributorCurrentOutletSensor(
                hass, f"{base}_current_outlet", distributor
            )
            slot["current"] = cur
            new.append(cur)
        _reconcile_outlet_sensors(distributor, slot, base, new)
        if new:
            async_add_devices(new)

    @callback
    def _reconcile_outlet_sensors(distributor, slot, base, new_out):
        did = distributor["id"]
        used = used_outlets(hass, did)
        to_add, to_remove = outlet_reconcile_diff(used, set(slot["outlets"]))
        for n in sorted(to_add):
            ent = SmartIrrigationDistributorOutletZoneSensor(
                hass, f"{base}_outlet_{n}_zone", distributor, n
            )
            slot["outlets"][n] = ent
            new_out.append(ent)
        for n in to_remove:
            ent = slot["outlets"].pop(n)
            _remove_entity(ent)

    @callback
    def _remove_entity(ent) -> None:
        registry = er.async_get(hass)
        eid = registry.async_get_entity_id(PLATFORM, const.DOMAIN, ent.unique_id)
        if eid:
            registry.async_remove(eid)

    @callback
    def async_reconcile_distributor_sensors(distributor_id) -> None:
        tracker = hass.data.get(const.DOMAIN, {}).get("distributor_sensors", {})
        slot = tracker.get(distributor_id)
        if slot is None:
            return
        store = hass.data[const.DOMAIN]["coordinator"].store
        distributor = store.get_distributor(distributor_id)
        if distributor is None:
            return
        base = "{}.{}_distributor_{}".format(
            PLATFORM, const.DOMAIN, slugify(distributor.get("name") or f"d{distributor_id}")
        )
        new = []
        _reconcile_outlet_sensors(distributor, slot, base, new)
        if new:
            async_add_devices(new)

    @callback
    def async_remove_distributor_sensors(distributor_id) -> None:
        tracker = hass.data.get(const.DOMAIN, {}).get("distributor_sensors", {})
        slot = tracker.pop(distributor_id, None)
        if slot is None:
            return
        for ent in [slot["current"], *slot["outlets"].values()]:
            if ent is not None:
                _remove_entity(ent)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_register_entity", async_add_distributor_sensors
        )
    )
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_updated", async_reconcile_distributor_sensors
        )
    )
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_removed", async_remove_distributor_sensors
        )
    )
```

> Confirm `SensorEntity`, `PLATFORM` (= `sensor`), `slugify`, `async_dispatcher_connect`, `callback` are imported in `sensor.py` (grep; the file already uses the register pattern so most are present). Add `er` import.

- [ ] **Step 4: Run to verify it passes**

Run: `... tests/test_distributor_entities.py -q`
Expected: PASS. Run `... tests/test_distributor.py tests/test_distributor_dispatch.py -q` — no regressions.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/sensor.py tests/test_distributor_entities.py
git commit -m "feat(distributor): current-outlet + dynamic outlet-zone sensors"
```

---

### Task I4: Commissioned + watering-now binary sensors (binary_sensor.py)

**Files:**
- Modify: `custom_components/smart_irrigation/binary_sensor.py`
- Test: `tests/test_distributor_entities.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from custom_components.smart_irrigation.binary_sensor import (
    SmartIrrigationDistributorCommissionedSensor,
    SmartIrrigationDistributorWateringNowSensor,
)


def test_commissioned_binary_sensor():
    dist = {"id": 0, "name": "G1", "commissioning_confirmed": True, "active_cycle": {}}
    hass = _hass_full([], dist)
    s = SmartIrrigationDistributorCommissionedSensor(hass, "binary_sensor.g1_commissioned", dist)
    assert s.is_on is True
    dist2 = {**dist, "commissioning_confirmed": False}
    s2 = SmartIrrigationDistributorCommissionedSensor(hass, "binary_sensor.g1_commissioned", dist2)
    assert s2.is_on is False


def test_watering_now_binary_sensor():
    dist = {"id": 0, "name": "G1", "commissioning_confirmed": True,
            "active_cycle": {"outlet": 2, "phase": "watering"}}
    hass = _hass_full([], dist)
    s = SmartIrrigationDistributorWateringNowSensor(hass, "binary_sensor.g1_watering_now", dist)
    assert s.is_on is True
    assert s.extra_state_attributes["phase"] == "watering"
    assert s.extra_state_attributes["outlet"] == 2
    idle = {**dist, "active_cycle": {}}
    s_idle = SmartIrrigationDistributorWateringNowSensor(hass, "binary_sensor.g1_watering_now", idle)
    assert s_idle.is_on is False
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`.

- [ ] **Step 3: Implement** — add to `binary_sensor.py`

Add `from .distributor_entity import DistributorEntityBase`. Then:
```python
class SmartIrrigationDistributorCommissionedSensor(DistributorEntityBase, BinarySensorEntity):
    """On when the distributor's commissioning is confirmed (armed)."""

    suffix = "commissioned"
    _attr_translation_key = "commissioned"
    _attr_icon = "mdi:check-decagram"

    def _refresh(self, distributor: dict) -> None:
        self._on = bool(distributor.get("commissioning_confirmed"))

    @property
    def is_on(self) -> bool:
        return self._on


class SmartIrrigationDistributorWateringNowSensor(DistributorEntityBase, BinarySensorEntity):
    """On while a distributor cycle is in progress (watering or pausing)."""

    suffix = "watering_now"
    _attr_translation_key = "watering_now"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def _refresh(self, distributor: dict) -> None:
        self._cycle = distributor.get("active_cycle") or {}

    @property
    def is_on(self) -> bool:
        return bool(self._cycle)

    @property
    def extra_state_attributes(self) -> dict:
        return {"phase": self._cycle.get("phase"), "outlet": self._cycle.get("outlet")}
```

Wire them in `async_setup_entry` — subscribe to `_distributor_register_entity` (create both, once per distributor) and `_distributor_removed` (remove). Mirror the sensor.py tracker pattern but simpler (no per-outlet dynamics — these are static per distributor):
```python
    @callback
    def async_add_distributor_binary_sensors(distributor: dict) -> None:
        if const.DOMAIN not in hass.data:
            return
        registered = hass.data[const.DOMAIN].setdefault("distributor_binary_sensors", {})
        did = distributor["id"]
        if did in registered:
            return
        base = "{}.{}_distributor_{}".format(
            PLATFORM, const.DOMAIN, slugify(distributor.get("name") or f"d{did}")
        )
        entities = [
            SmartIrrigationDistributorCommissionedSensor(hass, f"{base}_commissioned", distributor),
            SmartIrrigationDistributorWateringNowSensor(hass, f"{base}_watering_now", distributor),
        ]
        registered[did] = entities
        async_add_devices(entities)

    @callback
    def async_remove_distributor_binary_sensors(distributor_id) -> None:
        registered = hass.data.get(const.DOMAIN, {}).get("distributor_binary_sensors", {})
        entities = registered.pop(distributor_id, None)
        if not entities:
            return
        registry = er.async_get(hass)
        for ent in entities:
            eid = registry.async_get_entity_id(PLATFORM, const.DOMAIN, ent.unique_id)
            if eid:
                registry.async_remove(eid)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_register_entity", async_add_distributor_binary_sensors
        )
    )
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_removed", async_remove_distributor_binary_sensors
        )
    )
```
Add `from homeassistant.helpers import entity_registry as er` and confirm `slugify` import.

- [ ] **Step 4: Run to verify it passes** — `... tests/test_distributor_entities.py -q` PASS; no regressions in `tests/test_distributor*.py`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/binary_sensor.py tests/test_distributor_entities.py
git commit -m "feat(distributor): commissioned + watering-now binary sensors"
```

---

### Task I5: Test-run button (button.py)

**Files:**
- Modify: `custom_components/smart_irrigation/button.py`
- Test: `tests/test_distributor_entities.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from custom_components.smart_irrigation.button import SmartIrrigationDistributorTestRunButton


async def test_test_run_button_calls_coordinator():
    dist = {"id": 0, "name": "G1"}
    hass = _hass_full([], dist)
    coord = hass.data[const.DOMAIN]["coordinator"]
    coord.async_run_distributor_test = AsyncMock()
    coord.store.get_distributor = lambda did: dist
    b = SmartIrrigationDistributorTestRunButton(hass, "button.g1_test_run", dist)
    await b.async_press()
    coord.async_run_distributor_test.assert_awaited_once()
    assert coord.async_run_distributor_test.await_args.args[0]["id"] == 0
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`.

- [ ] **Step 3: Implement** — add to `button.py`

Add `from .distributor_entity import DistributorEntityBase`, `from homeassistant.helpers import entity_registry as er`. Then:
```python
class SmartIrrigationDistributorTestRunButton(DistributorEntityBase, ButtonEntity):
    """Run the commissioning test-run (fixed short window per outlet)."""

    suffix = "test_run"
    _attr_translation_key = "test_run"
    _attr_icon = "mdi:play-circle"

    async def async_press(self) -> None:
        coordinator = self.hass.data[const.DOMAIN]["coordinator"]
        distributor = coordinator.store.get_distributor(self._distributor_id)
        if distributor is not None:
            await coordinator.async_run_distributor_test(distributor)
```

Wire in `async_setup_entry` (static per distributor, add on register, remove on removed):
```python
    @callback
    def async_add_distributor_button(distributor: dict) -> None:
        if const.DOMAIN not in hass.data:
            return
        registered = hass.data[const.DOMAIN].setdefault("distributor_buttons", {})
        did = distributor["id"]
        if did in registered:
            return
        base = "{}.{}_distributor_{}".format(
            PLATFORM, const.DOMAIN, slugify(distributor.get("name") or f"d{did}")
        )
        ent = SmartIrrigationDistributorTestRunButton(hass, f"{base}_test_run", distributor)
        registered[did] = [ent]
        async_add_devices([ent])

    @callback
    def async_remove_distributor_button(distributor_id) -> None:
        registered = hass.data.get(const.DOMAIN, {}).get("distributor_buttons", {})
        entities = registered.pop(distributor_id, None)
        if not entities:
            return
        registry = er.async_get(hass)
        for ent in entities:
            eid = registry.async_get_entity_id(PLATFORM, const.DOMAIN, ent.unique_id)
            if eid:
                registry.async_remove(eid)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_register_entity", async_add_distributor_button
        )
    )
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, const.DOMAIN + "_distributor_removed", async_remove_distributor_button
        )
    )
```

- [ ] **Step 4: Run to verify it passes** — PASS; no regressions.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/button.py tests/test_distributor_entities.py
git commit -m "feat(distributor): test-run button"
```

---

### Task I6: i18n — all 8 languages

**Files:**
- Modify: `custom_components/smart_irrigation/translations/{en,de,nl,fr,it,es,sk,no}.json` (whatever the 8 are — `ls` the dir)

- [ ] **Step 1:** `ls custom_components/smart_irrigation/translations/` to confirm the 8 files. For EACH, under `entity.sensor`, `entity.binary_sensor`, `entity.button`, add the keys (translate the names per language; English shown):
  - `sensor.current_outlet.name` = "Current outlet"
  - `sensor.outlet_zone.name` = "Zone on outlet {outlet}"
  - `binary_sensor.commissioned.name` = "Commissioned"
  - `binary_sensor.watering_now.name` = "Watering now" (may already exist for zones — a shared key name is fine; HA scopes by platform+key, and the same translated string applies)
  - `button.test_run.name` = "Test run"

- [ ] **Step 2:** Edit each file via a Node script to preserve CRLF-canonical formatting (the repo convention):
```bash
node -e '
const fs=require("fs");
const langs={en:{co:"Current outlet",oz:"Zone on outlet {outlet}",cm:"Commissioned",wn:"Watering now",tr:"Test run"},
 de:{co:"Aktueller Ausgang",oz:"Zone an Ausgang {outlet}",cm:"Freigegeben",wn:"Bewässert gerade",tr:"Testlauf"},
 /* fill nl,fr,it,es,sk,no */};
for(const [l,t] of Object.entries(langs)){
  const p=`custom_components/smart_irrigation/translations/${l}.json`;
  const j=JSON.parse(fs.readFileSync(p,"utf8"));
  j.entity=j.entity||{}; j.entity.sensor=j.entity.sensor||{}; j.entity.binary_sensor=j.entity.binary_sensor||{}; j.entity.button=j.entity.button||{};
  j.entity.sensor.current_outlet={name:t.co}; j.entity.sensor.outlet_zone={name:t.oz};
  j.entity.binary_sensor.commissioned={name:t.cm}; j.entity.binary_sensor.watering_now=j.entity.binary_sensor.watering_now||{name:t.wn};
  j.entity.button.test_run={name:t.tr};
  fs.writeFileSync(p, JSON.stringify(j,null,2).replace(/\n/g,"\r\n")+"\r\n");
}'
```
Provide correct translations for all 8 languages (nl, fr, it, es, sk, no per the memory [[hasi-i18n-all-languages]] — match the languages actually present). Verify each file still parses (`node -e 'JSON.parse(require("fs").readFileSync(process.argv[1]))' <file>`).

- [ ] **Step 3:** Confirm no key is dropped and all 8 have the same 5 keys. Commit:
```bash
git add custom_components/smart_irrigation/translations/
git commit -m "i18n(distributor): entity names for device entities (8 languages)"
```

---

### Task I7: Release b8 (bundle H7 + this feature)

**Files:** `manifest.json`, `const.py` (`VERSION`), `frontend/package.json`, dist bundles (only if any TS changed — this feature is backend-only, so likely NOT).

- [ ] **Step 1:** Full suite green: `... tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_entities.py tests/test_scheduler_distributor.py tests/test_master.py -q`. `uvx black --check custom_components/smart_irrigation/` clean.
- [ ] **Step 2:** Bump version `v2026.07.11b7` → `v2026.07.11b8` in all three files (manifest + const with `v`, package.json without `v`). No frontend change → dist unchanged; do NOT rebuild unless `git status` shows a TS edit.
- [ ] **Step 3:** Commit `build: release v2026.07.11b8`, push `origin feature/gardena-distributor`.
- [ ] **Step 4:** Show the release notes to the user for approval (REGEL 5.6) BEFORE `gh release create`. Then `gh release create v2026.07.11b8 --repo Eifel-Joe/HAsmartirrigation --target feature/gardena-distributor --prerelease --title "..." --notes-file ...`.

---

## Self-Review (done)

- **Spec coverage:** device (I1) · current-outlet sensor (I3) · dynamic outlet-zone sensors + reconcile/removal (I3) · commissioned + watering-now binary (I4) · test-run button (I5) · signals register/updated/removed + zone coupling (I2) · i18n 8 (I6) · b8 bundle (I7) — all covered.
- **Type/name consistency:** `DistributorEntityBase`, `distributor_device_info`, `used_outlets`, `outlet_reconcile_diff`, `zone_on_outlet`, `_dist_store_update`, signal names `_distributor_register_entity`/`_distributor_updated`/`_distributor_removed`, tracker buckets `distributor_sensors`/`distributor_binary_sensors`/`distributor_buttons` — used consistently.
- **No placeholders:** every code step is complete except the i18n translations for nl/fr/it/es/sk/no, which the implementer fills from the existing translation files' language conventions (flagged explicitly in I6).
- **Testability caveat:** entity-registry add/remove and device grouping are verified in the live/click test on 192.168.10.196; the reconcile *diff* and all value logic are unit-tested.
