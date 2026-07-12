# Gardena Distributor — Plan B: Engine Primitives (`DistributorMixin`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the low-level, independently-testable building blocks of the distributor cycle — inlet actuation, position advance+persist, uncertain/de-arm+notify, global-master window control, and the finish-anchor duration estimate — in a new `DistributorMixin`. Plan C orchestrates these into the cycle loop and recovery.

**Architecture:** New focused file `custom_components/smart_irrigation/distributor.py` holding `DistributorMixin`, following the `master.py` / `self_closing.py` mixin pattern exactly. It reuses `MasterMixin`'s helpers (`_master_turn`, `_master_configured`, `_master_cfg`, `_master_sleep`, `async_master_begin_cycle`, `_master_on`) for the single global master, and the store's `async_update_distributor` (Plan A) for persistence. It is **not** wired into `SmartIrrigationCoordinator` here (that is Plan C) — it is unit-tested in isolation via a minimal `_DistHost(DistributorMixin, MasterMixin)`, mirroring `tests/test_master.py`.

**Tech Stack:** Python, attrs store, Home Assistant service calls, pytest + `pytest-homeassistant-custom-component`.

**Spec:** `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (§5.3, §6, §7). Depends on Plan A (landed): `DistributorEntry`, `store.async_update_distributor`, `const.POSITION_STATE_*`, `const.DISTRIBUTOR_MIN_*`.

**Distributor dict keys:** a distributor is passed around as the dict from `attr.asdict(DistributorEntry)` / `store.get_distributor(...)`. Fields are accessed by their **literal attr-name keys** (`"watering_mode"`, `"inlet_entity"`, `"run_service"`, `"pause_seconds"`, `"current_outlet"`, `"use_master"`, `"notify_target"`, `"id"`, `"name"`, …) — the attr names are the stable contract; value-constants (`WATERING_MODE_*`, `DURATION_UNIT_*`, `POSITION_STATE_*`) are reused.

**Test runner (verified working):** run from repo root `D:\Entwicklung\HASI\HAsmartirrigation`:
```
PYTHONPATH="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad" "C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad/uvenv312/Scripts/python.exe" -m pytest tests/test_distributor.py -p _local_socket_unblock -q
```
System Python (3.13) will NOT work; do not substitute plain `pytest`/`python`. All new tests go in `tests/test_distributor.py`.

---

### Task 1: Module + inlet actuation

**Files:**
- Modify: `custom_components/smart_irrigation/const.py` (append two constants)
- Create: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_distributor.py`:

```python
"""Gardena distributor engine primitives (DistributorMixin)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.distributor import DistributorMixin
from custom_components.smart_irrigation.master import MasterMixin


class _DistHost(DistributorMixin, MasterMixin):
    """Minimal host to unit-test the distributor mixin in isolation."""


def _host(**master_cfg):
    c = _DistHost()
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.hass.bus.async_fire = Mock()
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    c.store.config = SimpleNamespace(
        master_entity=master_cfg.get("master_entity", "switch.pump"),
        master_settle_seconds=master_cfg.get("master_settle_seconds", 10),
        master_kick_enabled=master_cfg.get("master_kick_enabled", False),
        master_kick_pause_seconds=master_cfg.get("master_kick_pause_seconds", 1.0),
        master_off_after=master_cfg.get("master_off_after", False),
    )
    c._master_sleep = AsyncMock()
    return c


def _dist(**kw):
    d = {
        "id": 0,
        "name": "Garten",
        "watering_mode": const.WATERING_MODE_CLASSIC,
        "inlet_entity": "switch.inlet",
        "run_service": "script.dist_inlet",
        "stop_service": None,
        "duration_field": "duration",
        "duration_unit": const.DURATION_UNIT_SECONDS,
        "run_data": {},
        "stop_data": {},
        "pause_seconds": 120,
        "skip_pulse_seconds": 20,
        "current_outlet": 1,
        "position_state": const.POSITION_STATE_SYNCED,
        "notify_target": None,
        "use_master": True,
        "commissioning_confirmed": True,
    }
    d.update(kw)
    return d


async def test_domain_turn_switch_uses_turn_on_off():
    c = _host()
    await c._dist_domain_turn("switch.inlet", True)
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_on", {"entity_id": "switch.inlet"}
    )


async def test_domain_turn_valve_uses_open_close():
    c = _host()
    await c._dist_domain_turn("valve.inlet", False)
    c.hass.services.async_call.assert_awaited_once_with(
        "valve", "close_valve", {"entity_id": "valve.inlet"}
    )


async def test_open_inlet_classic_opens_entity():
    c = _host()
    await c._dist_open_inlet(_dist(), 30)
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_on", {"entity_id": "switch.inlet"}
    )


async def test_open_inlet_service_fires_run_service_with_converted_duration():
    c = _host()
    d = _dist(
        watering_mode=const.WATERING_MODE_SERVICE,
        duration_field="dauer",
        duration_unit=const.DURATION_UNIT_MINUTES,
    )
    await c._dist_open_inlet(d, 600)  # 600 s -> 10 min
    domain, service, data = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("script", "dist_inlet")
    assert data["dauer"] == 10
    assert data["distributor_id"] == 0


async def test_close_inlet_classic_closes_entity():
    c = _host()
    await c._dist_close_inlet(_dist())
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_off", {"entity_id": "switch.inlet"}
    )


async def test_close_inlet_service_without_stop_is_noop():
    c = _host()
    await c._dist_close_inlet(_dist(watering_mode=const.WATERING_MODE_SERVICE))
    c.hass.services.async_call.assert_not_awaited()


async def test_close_inlet_service_fires_stop_service():
    c = _host()
    d = _dist(
        watering_mode=const.WATERING_MODE_SERVICE, stop_service="script.dist_off"
    )
    await c._dist_close_inlet(d)
    domain, service, _ = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("script", "dist_off")
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: ... distributor` / `ImportError`).

- [ ] **Step 3a: Append to `const.py`** (extend the distributor block from Plan A):

```python
# Fired when a distributor halts on doubtful sync (carries distributor_id + reason).
EVENT_DISTRIBUTOR_HALTED = "distributor_halted"
# Wall-clock safety margin added to a finish-anchored cycle estimate (spec §5.5).
DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS = 30
# Run-log trigger tag for distributor-delivered watering.
RUN_TRIGGER_DISTRIBUTOR = "distributor"
```

- [ ] **Step 3b: Create `custom_components/smart_irrigation/distributor.py`:**

```python
"""Gardena Wasserverteiler automatic: outlet-ring cycle engine (primitives).

A distributor waters 2..6 outlets one at a time through a single shared inlet
valve, behind the one global master. HASI is open-loop: it counts advances and
persists the position, it can never measure it. These are the low-level building
blocks (inlet actuation, position advance, uncertain/de-arm, master window
control, duration estimate); the cycle loop + recovery that orchestrate them
live in the coordinator (Plan C). Mixed into SmartIrrigationCoordinator.

Distributor dicts are attr.asdict(DistributorEntry); fields are accessed by their
literal attr-name keys.
"""

from __future__ import annotations

import logging
import math

from . import const

_LOGGER = logging.getLogger(__name__)


class DistributorMixin:
    """Distributor outlet-ring primitives. Mixed into SmartIrrigationCoordinator."""

    # --- inlet actuation ---------------------------------------------------

    async def _dist_domain_turn(self, entity: str, on: bool) -> None:
        """Open/close an inlet entity, domain-aware. valve.* needs open_valve/
        close_valve (homeassistant.turn_on silently no-ops on a valve); switch /
        input_boolean use turn_on/turn_off. Mirrors MasterMixin._master_turn."""
        if not isinstance(entity, str) or not entity:
            return
        if entity.split(".", 1)[0] == "valve":
            await self.hass.services.async_call(
                "valve",
                "open_valve" if on else "close_valve",
                {"entity_id": entity},
            )
            return
        await self.hass.services.async_call(
            "homeassistant",
            "turn_on" if on else "turn_off",
            {"entity_id": entity},
        )

    @staticmethod
    def _dist_split_service(dotted: str):
        """'domain.service' -> (domain, service)."""
        domain, _, service = (dotted or "").partition(".")
        return domain, service

    @staticmethod
    def _dist_convert(seconds: float, unit: str) -> int:
        """Convert a window (seconds) to the inlet hardware's unit, rounding up."""
        seconds = float(seconds or 0)
        if unit == const.DURATION_UNIT_MINUTES:
            return max(1, math.ceil(seconds / 60.0)) if seconds > 0 else 0
        return int(round(seconds))

    async def _dist_open_inlet(self, distributor: dict, seconds: float) -> None:
        """Open the inlet for a window. classic: domain-aware open (the loop owns
        the timed close). service (self-closing): fire the run_service with the
        converted duration; the hardware owns the close."""
        if distributor.get("watering_mode") == const.WATERING_MODE_SERVICE:
            domain, service = self._dist_split_service(distributor.get("run_service"))
            data = dict(distributor.get("run_data") or {})
            unit = distributor.get("duration_unit", const.DURATION_UNIT_SECONDS)
            field = distributor.get("duration_field") or "duration"
            data[field] = self._dist_convert(seconds, unit)
            data["distributor_id"] = distributor.get("id")
            await self.hass.services.async_call(domain, service, data)
            return
        await self._dist_domain_turn(distributor.get("inlet_entity"), True)

    async def _dist_close_inlet(self, distributor: dict) -> None:
        """Close the inlet. classic: domain-aware close. service: fire stop_service
        if configured, else rely on the hardware self-close (no-op)."""
        if distributor.get("watering_mode") == const.WATERING_MODE_SERVICE:
            stop = distributor.get("stop_service")
            if stop:
                domain, service = self._dist_split_service(stop)
                data = dict(distributor.get("stop_data") or {})
                data["distributor_id"] = distributor.get("id")
                await self.hass.services.async_call(domain, service, data)
            return
        await self._dist_domain_turn(distributor.get("inlet_entity"), False)
```

- [ ] **Step 4: Run — expect PASS** (7 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): engine module + inlet actuation primitives

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Position advance + persist

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (add methods to `DistributorMixin`)
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Append tests to `tests/test_distributor.py`:**

```python
async def test_advance_increments_and_persists():
    c = _host()
    new = await c._dist_advance(0, current_outlet=1, outlet_count=3)
    assert new == 2
    c.store.async_update_distributor.assert_awaited_once_with(0, {"current_outlet": 2})


async def test_advance_wraps_to_one_at_ring_end():
    c = _host()
    new = await c._dist_advance(0, current_outlet=3, outlet_count=3)
    assert new == 1
    c.store.async_update_distributor.assert_awaited_once_with(0, {"current_outlet": 1})
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... '_dist_advance'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` (after `_dist_close_inlet`):

```python
    # --- position advance --------------------------------------------------

    async def _dist_advance(
        self, distributor_id, current_outlet: int, outlet_count: int
    ) -> int:
        """Advance the ring by one and persist the new position immediately.

        For a blind device an "advance" is only ever "the pause timer elapsed" —
        there is no confirmation signal (spec §7). Position is written after each
        step so a crash never loses more than the in-flight step. Wraps n -> 1.
        """
        nxt = (int(current_outlet) % int(outlet_count)) + 1
        await self.store.async_update_distributor(
            distributor_id, {"current_outlet": nxt}
        )
        return nxt
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): position advance + persist (ring wrap)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Notify + mark-uncertain (de-arm)

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Append tests to `tests/test_distributor.py`:**

```python
async def test_notify_persistent_notification_when_bare_target():
    c = _host()
    await c._dist_notify(_dist(notify_target="persistent_notification"), "boom")
    domain, service, data = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("persistent_notification", "create")
    assert data["message"] == "boom"


async def test_notify_calls_notify_service():
    c = _host()
    await c._dist_notify(_dist(notify_target="notify.mobile"), "boom")
    domain, service, data = c.hass.services.async_call.await_args.args
    assert (domain, service) == ("notify", "mobile")
    assert data["message"] == "boom"


async def test_notify_noop_without_target():
    c = _host()
    await c._dist_notify(_dist(notify_target=None), "boom")
    c.hass.services.async_call.assert_not_awaited()


async def test_mark_uncertain_de_arms_persists_fires_and_notifies():
    c = _host()
    d = _dist(notify_target="notify.mobile")
    await c._dist_mark_uncertain(d, reason="no_flow")

    # position uncertain AND commissioning de-armed, in one persist
    c.store.async_update_distributor.assert_awaited_once_with(
        0,
        {
            "position_state": const.POSITION_STATE_UNCERTAIN,
            "commissioning_confirmed": False,
        },
    )
    # halted event fired with the reason
    evt = c.hass.bus.async_fire.call_args.args
    assert evt[0] == f"{const.DOMAIN}_{const.EVENT_DISTRIBUTOR_HALTED}"
    assert evt[1]["reason"] == "no_flow"
    assert evt[1]["distributor_id"] == 0
    # user notified
    c.hass.services.async_call.assert_awaited()
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... '_dist_notify'`).

- [ ] **Step 3: Add the methods** to `DistributorMixin` (after `_dist_advance`):

```python
    # --- notify + fail-safe de-arm ----------------------------------------

    async def _dist_notify(self, distributor: dict, message: str) -> None:
        """Send a halt notification to the configured target (if any). A dotted
        'domain.service' target is called with {message}; a bare target (or one
        without a service) falls back to a persistent_notification."""
        target = distributor.get("notify_target")
        if not target:
            return
        domain, service = self._dist_split_service(target)
        if domain and service:
            await self.hass.services.async_call(domain, service, {"message": message})
            return
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {"title": "Smart Irrigation", "message": message},
        )

    async def _dist_mark_uncertain(self, distributor: dict, reason: str) -> None:
        """Fail-safe: mark the position uncertain AND clear commissioning_confirmed
        (the single de-arm path, spec §7), persist both in one write, fire the
        halted event, and notify. An uncertain distributor is blocked from
        scheduled watering until the user re-syncs and re-confirms."""
        await self.store.async_update_distributor(
            distributor["id"],
            {
                "position_state": const.POSITION_STATE_UNCERTAIN,
                "commissioning_confirmed": False,
            },
        )
        self.hass.bus.async_fire(
            f"{const.DOMAIN}_{const.EVENT_DISTRIBUTOR_HALTED}",
            {
                "distributor_id": distributor.get("id"),
                "distributor": distributor.get("name"),
                "reason": reason,
            },
        )
        await self._dist_notify(
            distributor,
            f"Distributor '{distributor.get('name')}' halted ({reason}). "
            "Re-sync and re-confirm required.",
        )
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): notify + mark-uncertain de-arm

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Global-master window control

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Append tests to `tests/test_distributor.py`:**

```python
async def test_master_start_engages_begin_cycle():
    c = _host()
    c.async_master_begin_cycle = AsyncMock()
    await c._dist_master_start(_dist())
    c.async_master_begin_cycle.assert_awaited_once()


async def test_master_start_noop_when_use_master_false():
    c = _host()
    c.async_master_begin_cycle = AsyncMock()
    await c._dist_master_start(_dist(use_master=False))
    c.async_master_begin_cycle.assert_not_awaited()


async def test_window_off_powers_master_down_when_off_after_and_exclusive():
    c = _host(master_off_after=True)
    await c._dist_master_window_off(_dist(), concurrent=False)
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_off", {"entity_id": "switch.pump"}
    )


async def test_window_off_noop_when_not_off_after():
    c = _host(master_off_after=False)
    await c._dist_master_window_off(_dist(), concurrent=False)
    c.hass.services.async_call.assert_not_awaited()


async def test_window_off_noop_when_concurrent():
    c = _host(master_off_after=True)
    await c._dist_master_window_off(_dist(), concurrent=True)
    c.hass.services.async_call.assert_not_awaited()


async def test_window_on_powers_up_and_settles():
    c = _host(master_off_after=True, master_settle_seconds=7)
    await c._dist_master_window_on(_dist(), concurrent=False)
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_on", {"entity_id": "switch.pump"}
    )
    c._master_sleep.assert_awaited_once_with(7)


async def test_master_end_off_after_powers_down_and_clears_flag():
    c = _host(master_off_after=True)
    c._master_on = True
    await c._dist_master_end(_dist())
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_off", {"entity_id": "switch.pump"}
    )
    assert c._master_on is False


async def test_master_end_keeps_on_when_not_off_after_but_clears_flag():
    c = _host(master_off_after=False)
    c._master_on = True
    await c._dist_master_end(_dist())
    off = [
        ck
        for ck in c.hass.services.async_call.await_args_list
        if ck.args[1] in ("turn_off", "close_valve")
    ]
    assert off == []
    assert c._master_on is False
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... '_dist_master_start'`).

- [ ] **Step 3: Add the methods** to `DistributorMixin` (after `_dist_mark_uncertain`). These reuse `MasterMixin` helpers on the shared **single global master**:

```python
    # --- global-master window control -------------------------------------
    # The distributor drives the ONE global master synchronously inside its own
    # atomic cycle: on at start, (optionally) off during each pause + on before
    # the next window, off at the end. Per-window cycling is gated on the existing
    # master_off_after setting. NOT-TO-DO: never toggle the master while the inlet
    # is open (the caller closes the inlet BEFORE calling _dist_master_window_off,
    # and opens it AFTER _dist_master_window_on) — else the distributor sees an
    # extra pressure edge and advances unintentionally. `concurrent` suppresses
    # per-window off in parallel mode (other zones may need the master on).

    def _dist_uses_master(self, distributor: dict) -> bool:
        return bool(distributor.get("use_master", True)) and self._master_configured()

    def _dist_master_off_after(self) -> bool:
        return bool(getattr(self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False))

    async def _dist_master_start(self, distributor: dict) -> None:
        """Bring the global master up for the cycle (idempotent on+kick+settle)."""
        if not self._dist_uses_master(distributor):
            return
        await self.async_master_begin_cycle()

    async def _dist_master_window_off(
        self, distributor: dict, concurrent: bool
    ) -> None:
        """Power the master off during a pause, iff master_off_after and the
        distributor runs exclusively (not concurrent)."""
        if not self._dist_uses_master(distributor) or concurrent:
            return
        if not self._dist_master_off_after():
            return
        await self._master_turn(False)

    async def _dist_master_window_on(
        self, distributor: dict, concurrent: bool
    ) -> None:
        """Bring the master back up (+ settle) before the next window, iff it was
        powered down in the pause."""
        if not self._dist_uses_master(distributor) or concurrent:
            return
        if not self._dist_master_off_after():
            return
        await self._master_turn(True)
        settle = getattr(self._master_cfg(), const.CONF_MASTER_SETTLE_SECONDS, 10)
        if float(settle or 0) > 0:
            await self._master_sleep(settle)

    async def _dist_master_end(self, distributor: dict) -> None:
        """End of cycle: power the master off iff master_off_after; always clear the
        on-flag so a later normal cycle re-arms (and re-kicks a stay-on pump)."""
        if self._dist_uses_master(distributor) and self._dist_master_off_after():
            await self._master_turn(False)
        self._master_on = False
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): global-master window control (per-outlet cycling)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Finish-anchor cycle duration estimate

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Append tests to `tests/test_distributor.py`:**

```python
def _zone(duration):
    return {const.ZONE_DURATION: duration}


def test_cycle_estimate_sums_windows_pauses_and_buffer():
    c = _host(master_off_after=False)
    d = _dist(pause_seconds=100, skip_pulse_seconds=20)
    # 3 outlets: two due (60 s, 40 s), one skipped (-> 20 s pulse)
    zones = [_zone(60), _zone(40), _zone(0)]
    est = c.distributor_cycle_estimate(d, zones)
    # windows 60+40+20=120, pauses 3*100=300, buffer 30 -> 450 (no master settle)
    assert est == 120 + 300 + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS


def test_cycle_estimate_adds_master_settle_when_cycling():
    c = _host(master_off_after=True, master_settle_seconds=10)
    d = _dist(pause_seconds=100, skip_pulse_seconds=20)
    zones = [_zone(60), _zone(40), _zone(0)]
    est = c.distributor_cycle_estimate(d, zones)
    # + 3 outlets * 10 s settle
    assert est == 120 + 300 + 3 * 10 + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS


def test_cycle_estimate_clamps_sub_floor_pause_and_pulse():
    c = _host(master_off_after=False)
    d = _dist(pause_seconds=5, skip_pulse_seconds=2)  # below the 10 s floor
    zones = [_zone(0), _zone(0)]
    est = c.distributor_cycle_estimate(d, zones)
    # pause clamped to 10, skip clamped to 10: windows 10+10=20, pauses 2*10=20
    assert est == 20 + 20 + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS


def test_cycle_estimate_zero_for_no_members():
    c = _host()
    assert c.distributor_cycle_estimate(_dist(), []) == 0.0
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'distributor_cycle_estimate'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` (after `_dist_master_end`):

```python
    # --- finish-anchor duration estimate ----------------------------------

    def distributor_cycle_estimate(
        self, distributor: dict, member_zones: list
    ) -> float:
        """Deterministic wall-clock seconds for a full sweep, for finish-anchored
        schedules (spec §5.5): sum of each outlet's window (its due duration, else
        the skip-pulse) + n pauses + per-window master settle (if the master
        cycles) + a safety buffer. Pause/skip are floored (spec §4.5)."""
        n = len(member_zones)
        if n == 0:
            return 0.0
        pause = max(
            int(distributor.get("pause_seconds", 300)),
            const.DISTRIBUTOR_MIN_PAUSE_SECONDS,
        )
        skip = max(
            int(distributor.get("skip_pulse_seconds", 30)),
            const.DISTRIBUTOR_MIN_SKIP_PULSE_SECONDS,
        )
        windows = 0.0
        for z in member_zones:
            dur = float(z.get(const.ZONE_DURATION) or 0)
            windows += dur if dur > 0 else skip
        total = windows + n * pause
        if self._dist_uses_master(distributor) and self._dist_master_off_after():
            settle = float(
                getattr(self._master_cfg(), const.CONF_MASTER_SETTLE_SECONDS, 10) or 0
            )
            total += n * settle
        return total + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Run the full distributor test file for regressions:**

Run: `pytest tests/test_distributor.py -p _local_socket_unblock -q` (via the wrapper).
Expected: PASS (all ~24 tests).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): finish-anchor cycle duration estimate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan B Self-Review

- **Spec coverage:** inlet actuation classic/service + valve-domain (§6) → Task 1; advance+persist, "confirmed advance = pause elapsed" (§7) → Task 2; uncertain+de-arm+notify (§7) → Task 3; global-master window cycling from `master_off_after`, exclusive-only, NOT-TO-DO ordering (§5.3) → Task 4; finish-anchor estimate with floors + master settle + buffer (§4.5/§5.5) → Task 5.
- **Deferred to Plan C (orchestration):** the cycle loop (Rule A/B, guard, per-outlet windows, safety-halt, run-tracking), test-run, re-sync services, restart reconciliation. These *use* the Task 1–5 primitives.
- **Documented MVP limit:** full multi-holder master arbitration (distributor concurrent with other draws in **parallel** mode) is out of scope — per-window master-off is suppressed when `concurrent=True`, so the master simply stays on (spec §5.3; parallel is best-effort/discouraged). The `concurrent` flag is supplied by the loop (Plan C) from the active sequencing mode.
- **No placeholders:** every step has concrete code, exact commands, expected output.
- **Type consistency:** all methods live on `DistributorMixin`; the mixin reuses `MasterMixin` helpers (`_master_turn`, `_master_configured`, `_master_cfg`, `_master_sleep`, `async_master_begin_cycle`, `_master_on`) — the `_DistHost(DistributorMixin, MasterMixin)` test host provides them. Distributor field keys are the literal attr names throughout. `const.DISTRIBUTOR_MIN_*` / `POSITION_STATE_*` from Plan A; `CONF_MASTER_*` / `WATERING_MODE_*` / `DURATION_UNIT_*` / `ZONE_DURATION` pre-exist.

## Handoff to Plan C

Plan C (cycle loop + recovery) builds `async_run_distributor_cycle`, `async_run_distributor_test`, `async_distributor_set_outlet` / `resync_home`, and `async_resume_distributor_cycles` on top of these primitives, wires `DistributorMixin` into `SmartIrrigationCoordinator`, and passes the `concurrent` flag from the active sequencing mode.
