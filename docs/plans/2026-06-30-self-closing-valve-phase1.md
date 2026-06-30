# Self-Closing Valve Mode — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-zone `service` watering mode so HASI delegates a zone's run to a self-closing valve (fire a service with the duration, credit optimistically, never run HASI's own close), with crash-safe accounting and stop support — classic mode untouched.

**Architecture:** A new `SelfClosingMixin` (`self_closing.py`) added to `SmartIrrigationCoordinator`. The classic actuator (`irrigation.py::_run_valve_metered`) stays as-is; the dispatcher routes zones whose `watering_mode == "service"` to the mixin instead. In-flight runs are persisted on the store `Config` (`active_valve_runs`) and reconciled on setup. New `ZoneEntry` fields hold the per-zone adapter config; `STORAGE_VERSION` bumps 8→9.

**Tech Stack:** Python 3.13, Home Assistant custom component, `attr`-based store, `pytest` + `pytest-homeassistant-custom-component`. Local test runner (Windows): `PYTHONPATH=<scratch> <uvenv312>/Scripts/python.exe -m pytest … -p _local_socket_unblock`.

**Scope (Phase 1 only):** `classic` + `service` adapters; optimistic bucket credit at start; confirm-open; stop + correction; restart reconciliation; migration; `irrigation_started/finished/zone_problem` events. **Out (Phase 2/3):** `duration_entity` + `mqtt` adapters; Jinja templating of `run_data`; master switch/valve.

> **Beyond the original Phase-1 plan, the following were also shipped** because they made the feature actually usable/testable: (a) the **zone-settings config UI** (a `watering_mode` dropdown + conditional service fields in `view-zone-settings.ts`, with a rebuilt `dist` bundle) — note the original "settable via `set_zone`" assumption was wrong, as `set_zone` only accepts a fixed `new_*_value` allow-list; the zone websocket POST (`ALLOW_EXTRA`) is the real config path the UI uses; and (b) **routing the manual `async_irrigate_now` / `async_run_zone` paths** for service-mode zones, so "irrigate now" and manual runs work, not only the scheduled `_irrigate_linked_entities`.

---

## File Structure

- **Create** `custom_components/smart_irrigation/self_closing.py` — `SelfClosingMixin`: the entire self-closing run lifecycle (dispatch, confirm, optimistic credit, persist, cleanup timer, stop+correction, restart reconciliation, events). One responsibility, isolated from the 63 KB `irrigation.py`.
- **Create** `tests/test_self_closing.py` — unit tests for the mixin (coordinator built via `__new__`, store/helpers mocked).
- **Modify** `custom_components/smart_irrigation/const.py` — new constants.
- **Modify** `custom_components/smart_irrigation/store.py` — `ZoneEntry` fields, `Config.active_valve_runs`, `STORAGE_VERSION` 8→9, migration block.
- **Modify** `custom_components/smart_irrigation/irrigation.py` — route `service`-mode zones; delegate `async_stop_zone`.
- **Modify** `custom_components/smart_irrigation/__init__.py` — add `SelfClosingMixin` to the coordinator bases; call `async_resume_self_closing_runs()` in `async_setup_entry`.

**Helpers reused from the coordinator (already exist on `IrrigationRunnerMixin`, verified on `upstream/master`):**
`self._confirm_valve_running(zone_id, entity_id)` (irrigation.py:265), `self._timed_volume_l(zone, seconds)` (irrigation.py:1154), `self._credited_depth_native(zone, volume_l)` (irrigation.py:1084), `self._record_run(zone_id, *, result, volume_l, planned_s, actual_s, detail, trigger, add_to_total)` (irrigation.py:1160), `self.store.async_update_zone(zone_id, changes)` (store.py:882), `self.store.async_update_config(changes)` (store.py:835), `self.store.get_zone(zone_id)` (store.py:849, returns a **dict**).

---

## Task 1: Constants

**Files:**
- Modify: `custom_components/smart_irrigation/const.py`

- [ ] **Step 1: Add the constants** (append near the other zone keys / events)

```python
# --- Self-closing valve mode (Phase 1) -------------------------------------
ZONE_WATERING_MODE = "watering_mode"          # per-zone actuation adapter
WATERING_MODE_CLASSIC = "classic"             # default: open -> sleep -> close
WATERING_MODE_SERVICE = "service"             # fire a service, valve self-closes

# 'service' adapter per-zone config
ZONE_RUN_SERVICE = "run_service"              # "domain.service" e.g. "script.irrigation_beet"
ZONE_DURATION_FIELD = "duration_field"        # data key the duration is passed under, e.g. "dauer"
ZONE_DURATION_UNIT = "duration_unit"          # DURATION_UNIT_SECONDS | DURATION_UNIT_MINUTES
ZONE_RUN_DATA = "run_data"                    # optional static dict merged into the call
ZONE_STOP_SERVICE = "stop_service"            # optional "domain.service" for early stop
ZONE_STOP_DATA = "stop_data"                  # optional static dict for the stop call

DURATION_UNIT_SECONDS = "seconds"
DURATION_UNIT_MINUTES = "minutes"

# Persisted in-flight self-closing runs (reboot resilience) — on Config
CONF_ACTIVE_VALVE_RUNS = "active_valve_runs"
RUN_ZONE_ID = "zone_id"
RUN_ENTITY_ID = "entity_id"          # the run_service string (for logging/identity)
RUN_STARTED = "started"              # ISO-8601 UTC
RUN_PLANNED_SECONDS = "planned_seconds"
RUN_PLANNED_MM = "planned_mm"
RUN_MODE = "mode"
RUN_CREDITED = "credited"

# Per-run events (new in this feature)
EVENT_IRRIGATE_STARTED = "irrigation_started"
EVENT_IRRIGATE_FINISHED = "irrigation_finished"
EVENT_ZONE_PROBLEM = "zone_problem"

# Run-log tags
RUN_TRIGGER_SELF_CLOSING = "self_closing"
RUN_DETAIL_OPTIMISTIC = "optimistic"
RUN_DETAIL_SELF_CLOSING_STOPPED = "self_closing_stopped"
PROBLEM_VALVE_DID_NOT_OPEN = "valve_did_not_open"
```

- [ ] **Step 2: Verify import** — `python -c "from custom_components.smart_irrigation import const; print(const.WATERING_MODE_SERVICE, const.CONF_ACTIVE_VALVE_RUNS)"` (run with the venv from a repo-root `PYTHONPATH`). Expected: `service active_valve_runs`.

- [ ] **Step 3: Commit**

```bash
git add custom_components/smart_irrigation/const.py
git commit -m "feat(self-closing): add watering-mode + active-run + event constants"
```

---

## Task 2: Store schema — ZoneEntry fields, Config.active_valve_runs, migration 8→9

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (`ZoneEntry` ~:162, `Config` ~:233, `STORAGE_VERSION` :158, `_async_migrate_func` :297)
- Test: `tests/test_store_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
"""Store schema for the self-closing valve mode."""
from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.store import Config, ZoneEntry, STORAGE_VERSION


def test_storage_version_is_9():
    assert STORAGE_VERSION == 9


def test_zone_entry_has_self_closing_fields():
    z = ZoneEntry()
    assert z.watering_mode == const.WATERING_MODE_CLASSIC
    assert z.run_service is None
    assert z.duration_field is None
    assert z.duration_unit == const.DURATION_UNIT_SECONDS
    assert z.run_data == {}
    assert z.stop_service is None
    assert z.stop_data == {}


def test_config_has_active_valve_runs():
    c = Config()
    assert c.active_valve_runs == []
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_store_self_closing.py -p _local_socket_unblock`
Expected: FAIL — `STORAGE_VERSION == 8`, `ZoneEntry` has no `watering_mode`.

- [ ] **Step 3: Implement**

In `store.py`, bump the version:
```python
STORAGE_VERSION = 9
```

Add fields to `ZoneEntry` (after `run_log = attr.ib(type=list, factory=list)`):
```python
    watering_mode = attr.ib(type=str, default=const.WATERING_MODE_CLASSIC)
    run_service = attr.ib(type=str, default=None)
    duration_field = attr.ib(type=str, default=None)
    duration_unit = attr.ib(type=str, default=const.DURATION_UNIT_SECONDS)
    run_data = attr.ib(type=dict, factory=dict)
    stop_service = attr.ib(type=str, default=None)
    stop_data = attr.ib(type=dict, factory=dict)
```
(Confirm `const` is imported in `store.py`; the file already imports many `const` names — add these to that import block, or use the literal default `"classic"` / `"seconds"` if the module imports names individually.)

Add to `Config` (class ~:233):
```python
    active_valve_runs = attr.ib(type=list, factory=list)
```

In `_async_migrate_func` (:297), append a stacked block (after the highest existing one):
```python
        if old_version <= 8:
            # Self-closing valve mode (v9): default every zone to classic and
            # seed the empty in-flight-run list. Additive only — no data moves.
            for zone in data.get("zones", []):
                zone.setdefault(const.ZONE_WATERING_MODE, const.WATERING_MODE_CLASSIC)
                zone.setdefault(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS)
            data.setdefault("config", {}).setdefault(
                const.CONF_ACTIVE_VALVE_RUNS, []
            )
```

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_store_self_closing.py -p _local_socket_unblock`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/store.py tests/test_store_self_closing.py
git commit -m "feat(self-closing): ZoneEntry adapter fields + active_valve_runs + 8->9 migration"
```

---

## Task 3: Duration conversion + service-open dispatch

**Files:**
- Create: `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
"""Self-closing valve mode (Phase 1)."""
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation import SmartIrrigationCoordinator


def _coord():
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.store = Mock()
    c.store.async_update_zone = AsyncMock()
    c.store.async_update_config = AsyncMock()
    return c


def _zone(**kw):
    z = {
        const.ZONE_ID: 2,
        const.ZONE_NAME: "Beet",
        const.ZONE_DURATION: 600.0,          # seconds (matches _run_valve_metered)
        const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        const.ZONE_RUN_SERVICE: "script.irrigation_beet",
        const.ZONE_DURATION_FIELD: "dauer",
        const.ZONE_DURATION_UNIT: const.DURATION_UNIT_MINUTES,
        const.ZONE_RUN_DATA: {},
    }
    z.update(kw)
    return z


def test_convert_duration_minutes_rounds_up_sub_minute():
    c = _coord()
    assert c._sc_convert(600.0, const.DURATION_UNIT_SECONDS) == 600
    assert c._sc_convert(600.0, const.DURATION_UNIT_MINUTES) == 10
    # sub-minute rounds up to 1 on minute hardware
    assert c._sc_convert(15.0, const.DURATION_UNIT_MINUTES) == 1


async def test_open_calls_run_service_with_duration_field():
    c = _coord()
    await c._sc_dispatch_open(_zone())
    c.hass.services.async_call.assert_awaited_once()
    domain, service, data = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("script", "irrigation_beet")
    assert data["dauer"] == 10                 # 600 s -> 10 min
    assert data["zone_id"] == 2
    assert data["zone_name"] == "Beet"
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "convert or open"`
Expected: FAIL — `SmartIrrigationCoordinator` has no `_sc_convert` / `_sc_dispatch_open` (and the mixin doesn't exist yet → also covered once Task 8 wires the base; for now add the mixin and a temporary direct test against the mixin if the base isn't wired — but Task 8 wiring is required for `SmartIrrigationCoordinator.__new__` to expose the methods. If running Task 3 before Task 8, temporarily test `SelfClosingMixin` directly via a throwaway subclass).

> Practical note: implement Task 8's one-line base-class change together with this task if the executor prefers the coordinator to expose the methods immediately; otherwise instantiate `SelfClosingMixin` directly in the test. The committed end state has the mixin on the coordinator.

- [ ] **Step 3: Implement** `self_closing.py`

```python
"""Self-closing valve mode: delegate the valve close to self-closing hardware.

A zone in WATERING_MODE_SERVICE is run by firing a configured service with the
run duration; the valve owns the close (a hardware countdown), so an HA outage
mid-run cannot cause continuous irrigation. The bucket is credited optimistically
at start and the in-flight run is persisted for restart reconciliation.
"""
from __future__ import annotations

import logging
import math

from homeassistant.util import dt as dt_util

from . import const

_LOGGER = logging.getLogger(__name__)


class SelfClosingMixin:
    """Self-closing actuation lifecycle. Mixed into SmartIrrigationCoordinator."""

    @staticmethod
    def _sc_convert(seconds: float, unit: str) -> int:
        """Convert a run duration (seconds) to the hardware's unit, rounding up."""
        seconds = float(seconds or 0)
        if unit == const.DURATION_UNIT_MINUTES:
            return max(1, math.ceil(seconds / 60.0)) if seconds > 0 else 0
        return int(round(seconds))

    def _sc_split_service(self, dotted: str):
        """'domain.service' -> (domain, service)."""
        domain, _, service = (dotted or "").partition(".")
        return domain, service

    async def _sc_dispatch_open(self, zone: dict) -> None:
        """Fire the zone's run_service with the converted duration."""
        seconds = float(zone.get(const.ZONE_DURATION) or 0)
        unit = zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS)
        field = zone.get(const.ZONE_DURATION_FIELD)
        domain, service = self._sc_split_service(zone.get(const.ZONE_RUN_SERVICE))
        data = dict(zone.get(const.ZONE_RUN_DATA) or {})
        if field:
            data[field] = self._sc_convert(seconds, unit)
        data["zone_id"] = zone.get(const.ZONE_ID)
        data["zone_name"] = zone.get(const.ZONE_NAME)
        await self.hass.services.async_call(domain, service, data)
```

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "convert or open"`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(self-closing): SelfClosingMixin duration conversion + service open"
```

---

## Task 4: Confirm-open, optimistic credit, persist active run, started event

**Files:**
- Modify: `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_run_credits_bucket_persists_and_fires_started():
    c = _coord()
    c.hass.bus.async_fire = Mock()
    # confirm-open succeeds, helpers return deterministic numbers
    c._confirm_valve_running = AsyncMock(return_value=True)
    c._timed_volume_l = Mock(return_value=20.0)        # litres
    c._credited_depth_native = Mock(return_value=4.0)  # mm
    zone = _zone(**{const.ZONE_BUCKET: -5.0, const.ZONE_MAXIMUM_BUCKET: 50.0})

    ok = await c.async_run_self_closing(zone, trigger="schedule")

    assert ok is True
    # open dispatched
    c.hass.services.async_call.assert_awaited()
    # bucket credited optimistically: -5 + 4 = -1
    bucket_calls = [ck for ck in c.store.async_update_zone.await_args_list
                    if const.ZONE_BUCKET in ck.args[1]]
    assert bucket_calls and bucket_calls[-1].args[1][const.ZONE_BUCKET] == -1.0
    # in-flight run persisted with credited=True
    cfg = c.store.async_update_config.await_args.args[0]
    runs = cfg[const.CONF_ACTIVE_VALVE_RUNS]
    assert len(runs) == 1 and runs[0][const.RUN_CREDITED] is True
    assert runs[0][const.RUN_ZONE_ID] == 2
    # started event fired
    evt = [a.args[0] for a in c.hass.bus.async_fire.call_args_list]
    assert f"{const.DOMAIN}_{const.EVENT_IRRIGATE_STARTED}" in evt


async def test_run_aborts_and_fires_problem_when_open_unconfirmed():
    c = _coord()
    c.hass.bus.async_fire = Mock()
    c._confirm_valve_running = AsyncMock(return_value=False)  # never opened
    c._timed_volume_l = Mock(return_value=20.0)
    c._credited_depth_native = Mock(return_value=4.0)
    zone = _zone()

    ok = await c.async_run_self_closing(zone, trigger="schedule")

    assert ok is False
    c.store.async_update_zone.assert_not_awaited()          # no credit
    c.store.async_update_config.assert_not_awaited()        # no persisted run
    evt = [a.args[0] for a in c.hass.bus.async_fire.call_args_list]
    assert f"{const.DOMAIN}_{const.EVENT_ZONE_PROBLEM}" in evt
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "credits or unconfirmed"`
Expected: FAIL — `async_run_self_closing` not defined.

- [ ] **Step 3: Implement** (append to `SelfClosingMixin`)

```python
    def _sc_fire(self, event: str, data: dict) -> None:
        self.hass.bus.async_fire(f"{const.DOMAIN}_{event}", data)

    async def _sc_active_runs(self) -> list:
        cfg = await self.store.async_get_config()
        return list(cfg.get(const.CONF_ACTIVE_VALVE_RUNS, []) or [])

    async def _sc_persist_runs(self, runs: list) -> None:
        await self.store.async_update_config({const.CONF_ACTIVE_VALVE_RUNS: runs})

    async def _sc_add_run(self, record: dict) -> None:
        runs = [r for r in await self._sc_active_runs()
                if r.get(const.RUN_ZONE_ID) != record[const.RUN_ZONE_ID]]
        runs.append(record)
        await self._sc_persist_runs(runs)

    async def _sc_remove_run(self, zone_id) -> None:
        runs = [r for r in await self._sc_active_runs()
                if r.get(const.RUN_ZONE_ID) != zone_id]
        await self._sc_persist_runs(runs)

    async def async_run_self_closing(self, zone: dict, *, trigger: str = "schedule") -> bool:
        """Fire a self-closing run for one zone. Returns True if started."""
        zone_id = zone.get(const.ZONE_ID)
        planned_seconds = float(zone.get(const.ZONE_DURATION) or 0)
        if planned_seconds <= 0:
            return False

        await self._sc_dispatch_open(zone)

        # Confirm the open BEFORE crediting (None = write-only valve, treat as ok).
        confirmed = await self._confirm_valve_running(
            zone_id, zone.get(const.ZONE_RUN_SERVICE)
        )
        if confirmed is False:
            self._sc_fire(const.EVENT_ZONE_PROBLEM, {
                "zone_id": zone_id, "zone": zone.get(const.ZONE_NAME),
                "entity_id": zone.get(const.ZONE_RUN_SERVICE),
                "reason": const.PROBLEM_VALVE_DID_NOT_OPEN,
            })
            return False

        # Optimistic bucket credit (the valve owns the close -> assume completion).
        volume_l = self._timed_volume_l(zone, planned_seconds)
        depth = self._credited_depth_native(zone, volume_l)
        ceiling = zone.get(const.ZONE_MAXIMUM_BUCKET)
        new_bucket = float(zone.get(const.ZONE_BUCKET) or 0) + depth
        if ceiling and new_bucket > ceiling:
            new_bucket = float(ceiling)
        await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: new_bucket})
        await self._record_run(
            zone_id, result=const.RUN_RESULT_COMPLETED, volume_l=volume_l,
            planned_s=planned_seconds, actual_s=planned_seconds,
            detail=const.RUN_DETAIL_OPTIMISTIC,
            trigger=const.RUN_TRIGGER_SELF_CLOSING, add_to_total=True,
        )

        # Persist the in-flight run for restart reconciliation.
        await self._sc_add_run({
            const.RUN_ZONE_ID: zone_id,
            const.RUN_ENTITY_ID: zone.get(const.ZONE_RUN_SERVICE),
            const.RUN_STARTED: dt_util.utcnow().isoformat(),
            const.RUN_PLANNED_SECONDS: planned_seconds,
            const.RUN_PLANNED_MM: depth,
            const.RUN_MODE: const.WATERING_MODE_SERVICE,
            const.RUN_CREDITED: True,
        })

        self._sc_fire(const.EVENT_IRRIGATE_STARTED, {
            "zones": [{"zone_id": zone_id, "zone": zone.get(const.ZONE_NAME),
                       "seconds": int(planned_seconds)}],
        })
        return True
```

> Execution cross-check: confirm `ZONE_DURATION` is seconds on `upstream/master` (the agent reported `_run_valve_metered` runs it as seconds). If it is minutes, multiply by 60 here and in the tests. Confirm `_record_run`'s `add_to_total` semantics match crediting usage once per run.

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "credits or unconfirmed"`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(self-closing): confirm-open, optimistic credit, persist run, started event"
```

---

## Task 5: Cleanup timer + finished event + remove active run

**Files:**
- Modify: `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_finish_removes_run_and_fires_finished():
    c = _coord()
    c.hass.bus.async_fire = Mock()
    # one persisted run to clear
    existing = {const.RUN_ZONE_ID: 2, const.RUN_PLANNED_SECONDS: 600.0}
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [existing]})
    zone = _zone(**{const.ZONE_BUCKET: -1.0})
    c.store.get_zone = Mock(return_value=zone)

    await c._sc_finish_run(2)

    # run removed from persistence
    cfg = c.store.async_update_config.await_args.args[0]
    assert cfg[const.CONF_ACTIVE_VALVE_RUNS] == []
    # finished event fired with the zone
    fired = {a.args[0]: a.args[1] for a in c.hass.bus.async_fire.call_args_list}
    key = f"{const.DOMAIN}_{const.EVENT_IRRIGATE_FINISHED}"
    assert key in fired
    assert fired[key]["zones"][0]["zone_id"] == 2
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "finish_removes"`
Expected: FAIL — `_sc_finish_run` not defined.

- [ ] **Step 3: Implement** (append to `SelfClosingMixin`)

```python
    async def _sc_finish_run(self, zone_id) -> None:
        """Finalise a completed/closed run: clear persistence + fire finished."""
        await self._sc_remove_run(zone_id)
        zone = self.store.get_zone(zone_id) or {}
        self._sc_fire(const.EVENT_IRRIGATE_FINISHED, {
            "zones": [{
                "zone_id": zone_id,
                "zone": zone.get(const.ZONE_NAME),
                "bucket": zone.get(const.ZONE_BUCKET),
            }],
            "problems": [],
        })

    def _sc_schedule_cleanup(self, zone_id, delay_seconds: float) -> None:
        """Schedule the cosmetic finish after the run's planned duration."""
        from homeassistant.helpers.event import async_call_later

        async def _done(_now):
            await self._sc_finish_run(zone_id)

        async_call_later(self.hass, max(0.0, delay_seconds), _done)
```

Then, at the end of `async_run_self_closing` (just before `return True`), add:
```python
        self._sc_schedule_cleanup(zone_id, planned_seconds)
```

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "finish_removes"`
Expected: PASS. Re-run the Task-4 tests to confirm no regression: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "credits"` → PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(self-closing): cleanup timer + finished event"
```

---

## Task 6: Stop + bucket correction

**Files:**
- Modify: `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_stop_calls_stop_service_and_corrects_bucket():
    c = _coord()
    c.hass.bus.async_fire = Mock()
    c._timed_volume_l = Mock(return_value=20.0)        # for full planned run
    c._credited_depth_native = Mock(return_value=4.0)  # planned depth 4 mm
    # one persisted run started 'now' with 600 s planned, fully credited
    started = "2026-06-30T08:00:00+00:00"
    run = {const.RUN_ZONE_ID: 2, const.RUN_STARTED: started,
           const.RUN_PLANNED_SECONDS: 600.0, const.RUN_PLANNED_MM: 4.0,
           const.RUN_CREDITED: True}
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [run]})
    zone = _zone(**{const.ZONE_BUCKET: -1.0, const.ZONE_STOP_SERVICE: "script.beet_off"})
    c.store.get_zone = Mock(return_value=zone)
    # half the run elapsed -> deliver 50% -> remove 2 mm of the 4 mm credit
    c._sc_elapsed = Mock(return_value=300.0)

    await c.async_stop_self_closing(2)

    # stop_service called
    domain, service, _ = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("script", "beet_off")
    # bucket corrected down by the undelivered 2 mm: -1 - 2 = -3
    bcalls = [ck for ck in c.store.async_update_zone.await_args_list
              if const.ZONE_BUCKET in ck.args[1]]
    assert bcalls[-1].args[1][const.ZONE_BUCKET] == -3.0
    # run cleared
    cfg = c.store.async_update_config.await_args.args[0]
    assert cfg[const.CONF_ACTIVE_VALVE_RUNS] == []
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "stop_calls"`
Expected: FAIL — `async_stop_self_closing` / `_sc_elapsed` not defined.

- [ ] **Step 3: Implement** (append to `SelfClosingMixin`)

```python
    def _sc_elapsed(self, started_iso: str) -> float:
        started = dt_util.parse_datetime(started_iso)
        if started is None:
            return 0.0
        return max(0.0, (dt_util.utcnow() - started).total_seconds())

    async def _sc_find_run(self, zone_id):
        for r in await self._sc_active_runs():
            if r.get(const.RUN_ZONE_ID) == zone_id:
                return r
        return None

    async def async_stop_self_closing(self, zone_id) -> bool:
        """Stop a self-closing run early: close the valve + correct the bucket."""
        run = await self._sc_find_run(zone_id)
        if run is None:
            return False
        zone = self.store.get_zone(zone_id) or {}

        # Close the valve via the configured stop service (best-effort).
        stop_svc = zone.get(const.ZONE_STOP_SERVICE)
        if stop_svc:
            domain, service = self._sc_split_service(stop_svc)
            data = dict(zone.get(const.ZONE_STOP_DATA) or {})
            data["zone_id"] = zone_id
            await self.hass.services.async_call(domain, service, data)
        else:
            _LOGGER.warning(
                "Zone %s stopped in self-closing mode without a stop_service; "
                "cannot close the valve, correcting accounting only", zone_id,
            )

        # Correct the bucket: remove the undelivered portion of the credit.
        planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
        planned_mm = float(run.get(const.RUN_PLANNED_MM) or 0)
        elapsed = self._sc_elapsed(run.get(const.RUN_STARTED))
        delivered_frac = min(elapsed / planned, 1.0) if planned > 0 else 1.0
        undelivered_mm = planned_mm * (1.0 - delivered_frac)
        if undelivered_mm:
            new_bucket = float(zone.get(const.ZONE_BUCKET) or 0) - undelivered_mm
            await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: new_bucket})

        await self._sc_remove_run(zone_id)
        await self._record_run(
            zone_id, result=const.RUN_RESULT_PARTIAL,
            planned_s=planned, actual_s=elapsed,
            detail=const.RUN_DETAIL_SELF_CLOSING_STOPPED,
            trigger=const.RUN_TRIGGER_SELF_CLOSING, add_to_total=False,
        )
        return True
```

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "stop_calls"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(self-closing): early stop via stop_service + bucket correction"
```

---

## Task 7: Restart reconciliation

**Files:**
- Modify: `custom_components/smart_irrigation/self_closing.py`
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_resume_finalises_overdue_and_reschedules_partial():
    c = _coord()
    c.hass.bus.async_fire = Mock()
    overdue = {const.RUN_ZONE_ID: 1, const.RUN_STARTED: "2026-06-30T08:00:00+00:00",
               const.RUN_PLANNED_SECONDS: 60.0}     # long past -> already closed
    partial = {const.RUN_ZONE_ID: 2, const.RUN_STARTED: "2026-06-30T08:00:00+00:00",
               const.RUN_PLANNED_SECONDS: 600.0}    # may still be running
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [overdue, partial]})
    c.store.get_zone = Mock(return_value=_zone())
    # zone 1 overdue (elapsed 10000 > 60), zone 2 partial (elapsed 100 < 600)
    elapsed = {1: 10000.0, 2: 100.0}
    c._sc_elapsed = Mock(side_effect=lambda iso, z=elapsed: 10000.0)  # patched per-call below
    finished = []
    c._sc_finish_run = AsyncMock(side_effect=lambda zid: finished.append(zid))
    rescheduled = []
    c._sc_schedule_cleanup = Mock(side_effect=lambda zid, delay: rescheduled.append((zid, delay)))

    # make elapsed depend on the run's zone via started parse: simplest is to
    # stub _sc_elapsed to read a marker — here drive by planned vs a fixed elapsed.
    def _el(iso):
        return 10000.0 if iso == overdue[const.RUN_STARTED] and False else None
    # Instead, drive deterministically:
    c._sc_elapsed = Mock(side_effect=[10000.0, 100.0])

    await c.async_resume_self_closing_runs()

    assert finished == [1]                    # overdue finalised
    assert rescheduled == [(2, 500.0)]        # partial rescheduled for remaining 500 s
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "resume_finalises"`
Expected: FAIL — `async_resume_self_closing_runs` not defined.

- [ ] **Step 3: Implement** (append to `SelfClosingMixin`)

```python
    async def async_resume_self_closing_runs(self) -> None:
        """Reconcile persisted in-flight runs after a restart.

        Self-closing hardware closes on its own, so we NEVER re-open: if the
        run is overdue it has already closed (finalise); if it is still within
        its window the hardware countdown is still running (reschedule the
        cosmetic cleanup for the remainder). The bucket was credited at start
        (credited=True), so it is never re-credited here.
        """
        for run in await self._sc_active_runs():
            zone_id = run.get(const.RUN_ZONE_ID)
            planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
            elapsed = self._sc_elapsed(run.get(const.RUN_STARTED))
            if elapsed >= planned:
                await self._sc_finish_run(zone_id)
            else:
                self._sc_schedule_cleanup(zone_id, planned - elapsed)
```

> Note: simplify the test's `_sc_elapsed` stub to `Mock(side_effect=[10000.0, 100.0])` (remove the dead `_el`/marker lines before committing — they are illustrative of the ordering only).

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "resume_finalises"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(self-closing): restart reconciliation (no re-open for self-closing hw)"
```

---

## Task 8: Wire the mixin + route actuation + delegate stop + resume on setup

**Files:**
- Modify: `custom_components/smart_irrigation/__init__.py` (coordinator bases ~:311; `async_setup_entry` ~:329)
- Modify: `custom_components/smart_irrigation/irrigation.py` (single-zone actuation; `async_stop_zone` :193)
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_classic_zone_unaffected_and_service_zone_routed():
    c = _coord()
    c.async_run_self_closing = AsyncMock(return_value=True)
    # classic zone -> not routed to self-closing
    classic = _zone(**{const.ZONE_WATERING_MODE: const.WATERING_MODE_CLASSIC})
    assert c._sc_is_self_closing(classic) is False
    # service zone -> routed
    svc = _zone()
    assert c._sc_is_self_closing(svc) is True


async def test_stop_zone_delegates_to_self_closing(monkeypatch):
    c = _coord()
    c.store.get_zone = Mock(return_value=_zone())
    c.async_stop_self_closing = AsyncMock(return_value=True)
    # classic stop path must NOT run for a service zone
    handled = await c._sc_maybe_stop(2)
    assert handled is True
    c.async_stop_self_closing.assert_awaited_once_with(2)
```

- [ ] **Step 2: Run it — RED**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock -k "routed or delegates"`
Expected: FAIL — `_sc_is_self_closing` / `_sc_maybe_stop` not defined; `SmartIrrigationCoordinator` doesn't include `SelfClosingMixin`.

- [ ] **Step 3: Implement**

Add the routing helpers to `SelfClosingMixin` (`self_closing.py`):
```python
    @staticmethod
    def _sc_is_self_closing(zone: dict) -> bool:
        return zone.get(const.ZONE_WATERING_MODE) == const.WATERING_MODE_SERVICE

    async def _sc_maybe_stop(self, zone_id) -> bool:
        """Return True if this zone is self-closing and was stopped here."""
        zone = self.store.get_zone(zone_id) or {}
        if not self._sc_is_self_closing(zone):
            return False
        await self.async_stop_self_closing(zone_id)
        return True
```

Wire the mixin into the coordinator (`__init__.py`):
```python
from .self_closing import SelfClosingMixin
```
and add it to the class bases:
```python
class SmartIrrigationCoordinator(
    SelfClosingMixin,
    ServiceHandlersMixin,
    WateringCalendarMixin,
    IrrigationRunnerMixin,
    CalculationMixin,
    SkipConditionsMixin,
    LiveEstimateMixin,
    ObservedWateringMixin,
):
```

Call resume at the end of `async_setup_entry` (`__init__.py`, after the coordinator + zones are in `hass.data`):
```python
    await coordinator.async_resume_self_closing_runs()
```

Route the actuation in `irrigation.py`. In the single-zone runner entry (the body that, for each eligible zone, calls `_run_valve_metered`), branch first:
```python
        if self._sc_is_self_closing(zone):
            await self.async_run_self_closing(zone, trigger=trigger)
            continue
        # ... existing classic _run_valve_metered path ...
```
And at the top of `async_stop_zone` (irrigation.py:193), delegate self-closing zones:
```python
    async def async_stop_zone(self, zone_id) -> None:
        if await self._sc_maybe_stop(zone_id):
            return
        # ... existing classic stop body ...
```

- [ ] **Step 4: Run it — GREEN**

Run: `pytest tests/test_self_closing.py -p _local_socket_unblock`
Expected: PASS (all self-closing tests).

- [ ] **Step 5: Run the full suite for regressions**

Run: `PYTHONPATH=<scratch> <uvenv312>/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -p no:cacheprovider -p no:sugar --tb=short -q -o addopts="" --timeout=120`
Expected: the prior baseline failing set is unchanged (the 44 environmental failures), plus the new self-closing tests pass. Diff the failing set against `baseline_fails.txt` exactly as for the bugfix branches.

- [ ] **Step 6: Lint + commit**

```bash
<uvenv312>/Scripts/python.exe -m ruff check custom_components/smart_irrigation/self_closing.py custom_components/smart_irrigation/__init__.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/irrigation.py custom_components/smart_irrigation/const.py
<uvenv312>/Scripts/python.exe -m black custom_components/smart_irrigation/self_closing.py
git add -A
git commit -m "feat(self-closing): wire mixin, route actuation + stop, resume on setup"
```

---

## Self-Review

**Spec coverage (vs `docs/specs/2026-06-30-self-closing-valve-mode.md`):**
- §4.1 `watering_mode` (classic/service) → Task 2 (schema) + Task 8 (routing). ✓ (`duration_entity`/`mqtt` are out of Phase 1 scope per §13.)
- §4.2 `service` config (run_service/duration_field/duration_unit/run_data/stop_service) → Task 2 fields + Task 3/4/6 use. ✓
- §4.3 persisted active-run record → Task 4 (`_sc_add_run`) + Task 2 (`Config.active_valve_runs`). ✓
- §5 flow (convert + sub-minute round-up + open + confirm-open + optimistic credit + cleanup timer) → Tasks 3,4,5. ✓
- §5.1 events (started/finished/zone_problem) → Tasks 4,5. ✓
- §6 stop + correction + restart reconciliation (wall-clock, no re-open) → Tasks 6,7. ✓
- §8 backward-compat (classic default + 8→9 migration) → Task 2 + Task 8 classic-unaffected test. ✓
- §11 testing (dispatch, optimistic credit, stop correction, reconciliation, granularity, migration, classic regression) → covered across tasks. ✓

**Out of Phase 1 (tracked for later plans):** `duration_entity` + `mqtt` adapters, Jinja `run_data` templating, master switch/valve, frontend UI.

**Placeholder scan:** Task 3 Step 2 and Task 7 Step 3 carry explicit "execution note" cross-checks (ZONE_DURATION unit; trim the illustrative test stub) — these are verification reminders, not missing code; the code shown is complete. No TBD/TODO remain.

**Type/name consistency:** `_sc_convert`, `_sc_dispatch_open`, `async_run_self_closing`, `_sc_add_run`/`_sc_remove_run`/`_sc_active_runs`/`_sc_persist_runs`, `_sc_finish_run`, `_sc_schedule_cleanup`, `async_stop_self_closing`, `_sc_elapsed`, `_sc_find_run`, `async_resume_self_closing_runs`, `_sc_is_self_closing`, `_sc_maybe_stop` — all defined before use and referenced consistently. Const names match Task 1.

**Known cross-checks for the executor (read the real code before relying on these):**
1. `ZONE_DURATION` unit (seconds assumed) vs `_run_valve_metered`.
2. `_record_run` `add_to_total` semantics (avoid double-counting usage with the optimistic credit).
3. The exact location of the per-zone actuation call inside the sequential/parallel/rotating runners in `irrigation.py` (Task 8 branch must sit before `_run_valve_metered` in each path that a `service` zone can reach).
