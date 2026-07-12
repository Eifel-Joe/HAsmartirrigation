# Gardena Distributor — Plan C: Cycle Loop & Recovery

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Orchestrate the Plan-B primitives into the full distributor cycle — the Rule A/B sweep loop with guard, skip-pulse, safety-halt, run-tracking and restart-safe in-flight persistence — plus the commissioning test-run, the manual re-sync, and the restart reconciliation. All as methods on `DistributorMixin`, unit-tested in isolation.

**Architecture:** Extends `custom_components/smart_irrigation/distributor.py` (`DistributorMixin`) with the orchestration layer on top of the Task-1..5 primitives. The loop reuses the coordinator's existing decision/accounting helpers (`_rain_delay_active`, `_apply_soil_moisture_veto`, `_timed_volume_l`, `_credited_depth_native`, `_record_run`, `_confirm_valve_running`) — provided by the coordinator at runtime and mocked in the isolated `_CycleHost(DistributorMixin, MasterMixin)` tests. Wiring the mixin into `SmartIrrigationCoordinator`, the services, the schedule dispatch and the startup resume hook is **Plan D** (integration).

**Tech Stack:** Python, asyncio, attrs store, pytest.

**Spec:** `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (§5.1, §5.2, §5.4, §6, §7). Depends on Plan A (store) + Plan B (primitives).

**Key design decisions baked in (from spec + coordinator internals):**
- **Rule B (empty cycle):** if a **rain delay** is active, or **no** member zone needs actual watering, the cycle does nothing — no switching, no advance (no drift). Member zones are gathered regardless of state; a **disabled** member still gets a skip-pulse in a Rule-A sweep.
- **"needs actual watering"** = not disabled AND `duration > 0` AND `bucket < bucket_threshold` (the coordinator's classic gate) AND not soil-vetoed. (Live-estimate gating is out of MVP scope — documented; the distributor uses the classic daily gate.)
- **Soil veto** is applied via the existing `_apply_soil_moisture_veto` (which re-anchors the bucket + fires `zone_skipped` + records a skipped run for vetoed zones); vetoed zones are then **skip-pulsed** to advance the ring.
- **In-flight persistence is phase-based** (not elapsed): `active_cycle = {"outlet", "phase"}` with phase `"watering"` or `"pausing"`. Restart reconciliation: crashed mid-**watering** → position still known → close inlet, stay synced; crashed mid-**pausing** → advance completion unknown → mark uncertain (spec §7).
- **Bucket credit** for a watered window is applied once at the window's end (`bucket = min(ceiling, bucket + credited_depth)`), and `_record_run(..., trigger=RUN_TRIGGER_DISTRIBUTOR, add_to_total=True)`.
- **Master `_master_on` de-arm caveat (Plan B final review):** the loop only calls the master primitives for the exclusive/sequential case; `concurrent` is passed by the caller (Plan D) from the active sequencing mode. Full multi-holder arbitration remains deferred (spec §5.3).

**Test runner (verified):** from repo root:
```
PYTHONPATH="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad" "C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad/uvenv312/Scripts/python.exe" -m pytest tests/test_distributor_cycle.py -p _local_socket_unblock -q
```
System Python (3.13) will NOT work. New tests go in `tests/test_distributor_cycle.py`.

---

### Task 1: Member gathering + decision + sleep/persist helpers

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (add to `DistributorMixin` after `distributor_cycle_estimate`)
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_distributor_cycle.py`:

```python
"""Gardena distributor cycle loop + recovery (DistributorMixin orchestration)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.distributor import DistributorMixin
from custom_components.smart_irrigation.master import MasterMixin


class _CycleHost(DistributorMixin, MasterMixin):
    """Minimal host to unit-test the cycle orchestration in isolation."""


def _mem(zid, outlet, **kw):
    z = {
        const.ZONE_ID: zid,
        const.ZONE_NAME: f"Z{zid}",
        "distributor_id": 0,
        "outlet_number": outlet,
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 60.0,
        const.ZONE_BUCKET: -5.0,
        const.ZONE_BUCKET_THRESHOLD: 0.0,
    }
    z.update(kw)
    return z


def test_needs_water_true_for_due_zone():
    c = _CycleHost()
    assert c._dist_needs_water(_mem(1, 1)) is True


def test_needs_water_false_when_disabled():
    c = _CycleHost()
    assert c._dist_needs_water(_mem(1, 1, **{const.ZONE_STATE: const.ZONE_STATE_DISABLED})) is False


def test_needs_water_false_when_duration_zero():
    c = _CycleHost()
    assert c._dist_needs_water(_mem(1, 1, **{const.ZONE_DURATION: 0})) is False


def test_needs_water_false_when_bucket_above_threshold():
    c = _CycleHost()
    assert c._dist_needs_water(_mem(1, 1, **{const.ZONE_BUCKET: 5.0})) is False


async def test_members_sorted_by_outlet():
    c = _CycleHost()
    c.store = Mock()
    c.store.async_get_zones = AsyncMock(
        return_value=[
            _mem(1, 3),
            {const.ZONE_ID: 9, "distributor_id": 1, "outlet_number": 1},  # other dist
            _mem(2, 1),
            _mem(3, 2),
        ]
    )
    members = await c._dist_members(0)
    assert [m[const.ZONE_ID] for m in members] == [2, 3, 1]


async def test_persist_and_clear_cycle():
    c = _CycleHost()
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    await c._dist_persist_cycle(0, 2, "watering")
    c.store.async_update_distributor.assert_awaited_with(
        0, {"active_cycle": {"outlet": 2, "phase": "watering"}}
    )
    await c._dist_clear_cycle(0)
    c.store.async_update_distributor.assert_awaited_with(0, {"active_cycle": {}})
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... '_dist_needs_water'`).

- [ ] **Step 3: Add the helpers** to `DistributorMixin` (after `distributor_cycle_estimate`):

```python
    # --- cycle orchestration: helpers -------------------------------------

    async def _dist_sleep(self, seconds) -> None:
        """Awaitable sleep wrapper (isolated/overridable in unit tests)."""
        import asyncio

        await asyncio.sleep(max(0.0, float(seconds or 0)))

    async def _dist_members(self, distributor_id) -> list:
        """This distributor's member zones (dicts), ordered by outlet 1..n."""
        zones = await self.store.async_get_zones()
        members = [z for z in zones if z.get("distributor_id") == distributor_id]
        return sorted(members, key=lambda z: z.get("outlet_number") or 0)

    def _dist_needs_water(self, zone: dict) -> bool:
        """Classic daily gate: automatic-eligible, calculated duration > 0, and
        the bucket still below its threshold. (Live-estimate gating is out of
        MVP scope — the distributor uses the daily gate.)"""
        return (
            zone.get(const.ZONE_STATE) != const.ZONE_STATE_DISABLED
            and (zone.get(const.ZONE_DURATION) or 0) > 0
            and (zone.get(const.ZONE_BUCKET) or 0)
            < (zone.get(const.ZONE_BUCKET_THRESHOLD) or 0)
        )

    async def _dist_persist_cycle(self, distributor_id, outlet: int, phase: str) -> None:
        """Persist the in-flight cycle record (phase-based, for restart recon)."""
        await self.store.async_update_distributor(
            distributor_id, {"active_cycle": {"outlet": outlet, "phase": phase}}
        )

    async def _dist_clear_cycle(self, distributor_id) -> None:
        """Clear the in-flight cycle record (cycle finished / aborted)."""
        await self.store.async_update_distributor(
            distributor_id, {"active_cycle": {}}
        )
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): cycle helpers (members, due gate, in-flight persist)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Zone bucket credit for a watered window

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Append tests:**

```python
def _credit_host():
    c = _CycleHost()
    c.store = Mock()
    c.store.async_update_zone = AsyncMock()
    c._timed_volume_l = Mock(return_value=20.0)  # litres
    c._credited_depth_native = Mock(return_value=4.0)  # mm
    c._record_run = AsyncMock()
    return c


async def test_credit_zone_credits_bucket_and_records_run():
    c = _credit_host()
    z = _mem(2, 1, **{const.ZONE_BUCKET: -5.0, const.ZONE_MAXIMUM_BUCKET: 50.0})
    await c._dist_credit_zone(z, 60.0)
    # bucket -5 + 4 = -1
    c.store.async_update_zone.assert_awaited_once_with(2, {const.ZONE_BUCKET: -1.0})
    kwargs = c._record_run.await_args.kwargs
    assert kwargs["result"] == const.RUN_RESULT_COMPLETED
    assert kwargs["volume_l"] == 20.0
    assert kwargs["trigger"] == const.RUN_TRIGGER_DISTRIBUTOR
    assert kwargs["add_to_total"] is True


async def test_credit_zone_caps_at_maximum_bucket():
    c = _credit_host()
    c._credited_depth_native = Mock(return_value=100.0)
    z = _mem(2, 1, **{const.ZONE_BUCKET: -5.0, const.ZONE_MAXIMUM_BUCKET: 10.0})
    await c._dist_credit_zone(z, 60.0)
    c.store.async_update_zone.assert_awaited_once_with(2, {const.ZONE_BUCKET: 10.0})
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... '_dist_credit_zone'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` (after `_dist_clear_cycle`):

```python
    async def _dist_credit_zone(self, zone: dict, seconds: float) -> None:
        """Credit a watered member zone's bucket and log the run. The distributor
        delivers a full timed window, so credit once at its end (bucket +=
        delivered depth, capped at maximum_bucket) and record usage — mirrors the
        timed-run accounting (_timed_volume_l -> _credited_depth_native)."""
        zone_id = zone.get(const.ZONE_ID)
        volume_l = self._timed_volume_l(zone, seconds)
        depth = self._credited_depth_native(zone, volume_l)
        new_bucket = float(zone.get(const.ZONE_BUCKET) or 0) + depth
        ceiling = zone.get(const.ZONE_MAXIMUM_BUCKET)
        if ceiling is not None and new_bucket > float(ceiling):
            new_bucket = float(ceiling)
        await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: new_bucket})
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_COMPLETED,
            volume_l=volume_l,
            planned_s=seconds,
            actual_s=seconds,
            trigger=const.RUN_TRIGGER_DISTRIBUTOR,
            add_to_total=True,
        )
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): per-window zone bucket credit + run log

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: The cycle loop — `async_run_distributor_cycle`

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Append tests:**

```python
def _dist_cfg(**kw):
    d = {
        "id": 0,
        "name": "Garten",
        "pause_seconds": 60,
        "skip_pulse_seconds": 20,
        "current_outlet": 1,
        "position_state": const.POSITION_STATE_SYNCED,
        "commissioning_confirmed": True,
        "confirm_entity": None,
        "use_master": True,
    }
    d.update(kw)
    return d


def _loop_host(members, **cfg_over):
    c = _CycleHost()
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    # isolate the loop: mock the primitives + coordinator helpers
    c._dist_members = AsyncMock(return_value=members)
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda zs: list(zs))
    c._rain_delay_active = Mock(return_value=False)
    c._dist_master_start = AsyncMock()
    c._dist_master_end = AsyncMock()
    c._dist_master_window_off = AsyncMock()
    c._dist_master_window_on = AsyncMock()
    c._dist_open_inlet = AsyncMock()
    c._dist_close_inlet = AsyncMock()
    c._dist_sleep = AsyncMock()
    c._dist_credit_zone = AsyncMock()
    c._dist_mark_uncertain = AsyncMock()
    c._dist_persist_cycle = AsyncMock()
    c._dist_clear_cycle = AsyncMock()
    c._confirm_valve_running = AsyncMock(return_value=None)
    c._dist_advance = AsyncMock(side_effect=lambda did, cur, n: (cur % n) + 1)
    return c


async def test_cycle_blocked_when_not_confirmed():
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    ran = await c.async_run_distributor_cycle(_dist_cfg(commissioning_confirmed=False))
    assert ran is False
    c._dist_master_start.assert_not_awaited()


async def test_cycle_blocked_when_uncertain():
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    ran = await c.async_run_distributor_cycle(
        _dist_cfg(position_state=const.POSITION_STATE_UNCERTAIN)
    )
    assert ran is False
    c._dist_master_start.assert_not_awaited()


async def test_cycle_rule_b_when_rain_delay():
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    c._rain_delay_active = Mock(return_value=True)
    ran = await c.async_run_distributor_cycle(_dist_cfg())
    assert ran is False
    c._dist_open_inlet.assert_not_awaited()  # no switching, no advance


async def test_cycle_rule_b_when_nothing_due():
    c = _loop_host(
        [_mem(1, 1, **{const.ZONE_DURATION: 0}), _mem(2, 2, **{const.ZONE_BUCKET: 5.0})]
    )
    ran = await c.async_run_distributor_cycle(_dist_cfg())
    assert ran is False
    c._dist_open_inlet.assert_not_awaited()


async def test_cycle_full_sweep_waters_due_and_pulses_rest():
    # 3 outlets: outlet 1 & 3 due, outlet 2 not due -> full sweep, 3 windows,
    # 3 advances, outlet 2 skip-pulsed, credits only for 1 & 3.
    members = [
        _mem(1, 1),
        _mem(2, 2, **{const.ZONE_DURATION: 0}),  # not due
        _mem(3, 3),
    ]
    c = _loop_host(members)
    ran = await c.async_run_distributor_cycle(_dist_cfg())
    assert ran is True
    assert c._dist_open_inlet.await_count == 3  # every outlet gets a window
    assert c._dist_advance.await_count == 3     # full ring
    assert c._dist_credit_zone.await_count == 2  # only the two due zones
    # window durations: due -> 60 (ZONE_DURATION), not-due -> 20 (skip pulse)
    windows = [ck.args[1] for ck in c._dist_open_inlet.await_args_list]
    assert windows == [60.0, 20, 60.0]
    c._dist_master_start.assert_awaited_once()
    c._dist_master_end.assert_awaited_once()
    c._dist_clear_cycle.assert_awaited()


async def test_cycle_safety_halt_on_no_flow():
    members = [_mem(1, 1), _mem(2, 2)]
    c = _loop_host(members, confirm_entity="binary_sensor.flow")
    # loop passes confirm_entity from the distributor dict
    c._confirm_valve_running = AsyncMock(return_value=False)  # no flow
    ran = await c.async_run_distributor_cycle(_dist_cfg(confirm_entity="binary_sensor.flow"))
    assert ran is False
    c._dist_close_inlet.assert_awaited()          # inlet closed defensively
    c._dist_mark_uncertain.assert_awaited_once()  # de-armed + halted
    # halted on the FIRST outlet -> only one window opened
    assert c._dist_open_inlet.await_count == 1


async def test_cycle_starts_at_current_outlet_when_not_home():
    # current_outlet=2 on a 3-outlet ring: physical order is z2, z3, z1.
    members = [_mem(1, 1), _mem(2, 2), _mem(3, 3)]
    c = _loop_host(members)
    ran = await c.async_run_distributor_cycle(_dist_cfg(current_outlet=2))
    assert ran is True
    watered = [ck.args[0][const.ZONE_ID] for ck in c._dist_credit_zone.await_args_list]
    assert watered == [2, 3, 1]  # physical order starting at outlet 2, wrapping
    # the first in-flight persist records the physical start outlet (2), not 1
    assert c._dist_persist_cycle.await_args_list[0].args == (0, 2, "watering")


async def test_cycle_survives_none_pause_and_skip():
    # A distributor persisted with None timings must not crash the cycle.
    members = [_mem(1, 1), _mem(2, 2)]
    c = _loop_host(members)
    ran = await c.async_run_distributor_cycle(
        _dist_cfg(pause_seconds=None, skip_pulse_seconds=None)
    )
    assert ran is True
    c._dist_master_end.assert_awaited_once()  # completed + master cleaned up
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'async_run_distributor_cycle'`).

- [ ] **Step 3: Add the loop** to `DistributorMixin` (after `_dist_credit_zone`):

```python
    # --- cycle loop --------------------------------------------------------

    async def async_run_distributor_cycle(
        self, distributor: dict, *, concurrent: bool = False, test_run: bool = False
    ) -> bool:
        """Run one distributor cycle. Returns True if a sweep ran.

        Guard (§5.1): a scheduled cycle runs only when synced AND commissioning-
        confirmed; a test-run bypasses the confirm gate but still needs synced.
        Rule B: a rain delay, or no member needing water, does nothing (no
        switching, no advance). Rule A: sweep all n outlets in order from the
        persisted position — water the due ones, skip-pulse the rest — advancing
        (and persisting) after each. A configured flow sensor that reports no
        flow during a watering window triggers a safety-halt (§7).
        """
        dist_id = distributor.get("id")
        if distributor.get("position_state") != const.POSITION_STATE_SYNCED:
            return False
        if not test_run and not distributor.get("commissioning_confirmed"):
            return False

        members = await self._dist_members(dist_id)
        n = len(members)
        if n == 0:
            return False

        if test_run:
            to_water = set()
            fixed = const.DISTRIBUTOR_TEST_RUN_SECONDS
        else:
            if self._rain_delay_active():
                return False
            survivors = await self._apply_soil_moisture_veto(list(members))
            survivor_ids = {m.get(const.ZONE_ID) for m in survivors}
            to_water = {
                m.get(const.ZONE_ID)
                for m in members
                if m.get(const.ZONE_ID) in survivor_ids and self._dist_needs_water(m)
            }
            if not to_water:
                return False

        # `or default` (not the get-default) so a persisted None can't crash the
        # cycle after the master is already armed.
        pause = max(
            int(distributor.get("pause_seconds") or 300),
            const.DISTRIBUTOR_MIN_PAUSE_SECONDS,
        )
        skip = max(
            int(distributor.get("skip_pulse_seconds") or 30),
            const.DISTRIBUTOR_MIN_SKIP_PULSE_SECONDS,
        )
        confirm_entity = distributor.get("confirm_entity")
        # Normalise the persisted position into 1..n, then sweep in PHYSICAL order
        # STARTING at the current outlet — the device flows on `current` first.
        # Members are sorted 1..n (contiguous, enforced by the mapping validation),
        # so members[current-1] is the outlet flowing now; `current` and `order[i]`
        # stay in lockstep as we advance.
        current = ((int(distributor.get("current_outlet") or 1) - 1) % n) + 1
        order = [members[(current - 1 + k) % n] for k in range(n)]

        await self._dist_master_start(distributor)
        for i, zone in enumerate(order):
            zid = zone.get(const.ZONE_ID)
            if test_run:
                water = False
                window = fixed
            else:
                water = zid in to_water
                window = float(zone.get(const.ZONE_DURATION) or 0) if water else skip

            await self._dist_persist_cycle(dist_id, current, "watering")
            await self._dist_open_inlet(distributor, window)

            if confirm_entity:
                # Poll the shared inlet flow sensor across its grace window
                # (_confirm_valve_running polls until VALVE_CONFIRM_TIMEOUT — NOT
                # a single poll). retry=False = poll-only: the confirm target is a
                # flow sensor, which must never be re-actuated. None (unreadable)
                # fails open (only a definite False halts).
                confirmed = await self._confirm_valve_running(
                    zid, confirm_entity, retry=False
                )
                if confirmed is False:
                    await self._dist_close_inlet(distributor)
                    await self._dist_master_end(distributor)
                    await self._dist_clear_cycle(dist_id)
                    await self._dist_mark_uncertain(
                        distributor, reason=const.PROBLEM_VALVE_DID_NOT_OPEN
                    )
                    return False

            await self._dist_sleep(window)
            if water:
                await self._dist_credit_zone(zone, window)
            await self._dist_close_inlet(distributor)

            await self._dist_persist_cycle(dist_id, current, "pausing")
            await self._dist_master_window_off(distributor, concurrent)
            await self._dist_sleep(pause)
            current = await self._dist_advance(dist_id, current, n)
            if i < n - 1:
                await self._dist_master_window_on(distributor, concurrent)

        await self._dist_master_end(distributor)
        await self._dist_clear_cycle(dist_id)
        return True
```

- [ ] **Step 4: Run — expect PASS** (6 loop tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): cycle loop (Rule A/B, guard, skip-pulse, safety-halt)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Commissioning test-run

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Append tests:**

```python
async def test_test_run_sweeps_all_outlets_fixed_and_bypasses_confirm_gate():
    members = [_mem(1, 1), _mem(2, 2, **{const.ZONE_DURATION: 0}), _mem(3, 3)]
    # not confirmed, but synced -> a test-run is allowed
    c = _loop_host(members)
    ran = await c.async_run_distributor_test(
        _dist_cfg(commissioning_confirmed=False)
    )
    assert ran is True
    assert c._dist_open_inlet.await_count == 3          # every outlet
    assert c._dist_advance.await_count == 3
    c._dist_credit_zone.assert_not_awaited()            # test-run never credits
    windows = [ck.args[1] for ck in c._dist_open_inlet.await_args_list]
    assert windows == [const.DISTRIBUTOR_TEST_RUN_SECONDS] * 3


async def test_test_run_still_requires_synced():
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    ran = await c.async_run_distributor_test(
        _dist_cfg(position_state=const.POSITION_STATE_UNCERTAIN)
    )
    assert ran is False
    c._dist_master_start.assert_not_awaited()
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'async_run_distributor_test'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` (after `async_run_distributor_cycle`):

```python
    async def async_run_distributor_test(self, distributor: dict) -> bool:
        """Commissioning test-run: sweep EVERY outlet for a fixed short window
        (DISTRIBUTOR_TEST_RUN_SECONDS) regardless of due/skip, so the user can
        watch that each zone waters in order and the device advances reliably.
        Requires synced but is exempt from the commissioning-confirmed gate
        (§10); never credits a bucket."""
        return await self.async_run_distributor_cycle(distributor, test_run=True)
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): commissioning test-run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Manual re-sync services

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Append tests:**

```python
async def test_set_outlet_sets_position_synced():
    c = _CycleHost()
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    await c.async_distributor_set_outlet(0, 3)
    c.store.async_update_distributor.assert_awaited_once_with(
        0, {"current_outlet": 3, "position_state": const.POSITION_STATE_SYNCED}
    )


async def test_resync_home_sets_outlet_one():
    c = _CycleHost()
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    await c.async_distributor_resync_home(0)
    c.store.async_update_distributor.assert_awaited_once_with(
        0, {"current_outlet": 1, "position_state": const.POSITION_STATE_SYNCED}
    )
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'async_distributor_set_outlet'`).

- [ ] **Step 3: Add the methods** to `DistributorMixin` (after `async_run_distributor_test`):

```python
    # --- manual re-sync (recovery) ----------------------------------------

    async def async_distributor_set_outlet(self, distributor_id, outlet: int) -> None:
        """Re-sync: the user read the physical window and sets the current outlet.
        Marks the position synced. Does NOT re-arm commissioning_confirmed — the
        user re-confirms that separately (spec §7)."""
        await self.store.async_update_distributor(
            distributor_id,
            {
                "current_outlet": int(outlet),
                "position_state": const.POSITION_STATE_SYNCED,
            },
        )

    async def async_distributor_resync_home(self, distributor_id) -> None:
        """Convenience re-sync to outlet 1."""
        await self.async_distributor_set_outlet(distributor_id, 1)
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): manual re-sync services (set_outlet, resync_home)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Restart reconciliation

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py`
- Test: `tests/test_distributor_cycle.py`

- [ ] **Step 1: Append tests:**

```python
def _recon_host(distributors):
    c = _CycleHost()
    c.store = Mock()
    c.store.async_get_distributors = AsyncMock(return_value=distributors)
    c.store.async_update_distributor = AsyncMock()
    c._dist_close_inlet = AsyncMock()
    c._dist_clear_cycle = AsyncMock()
    c._dist_mark_uncertain = AsyncMock()
    return c


async def test_resume_no_active_cycle_is_noop():
    c = _recon_host([_dist_cfg(**{"active_cycle": {}})])
    await c.async_resume_distributor_cycles()
    c._dist_close_inlet.assert_not_awaited()
    c._dist_mark_uncertain.assert_not_awaited()


async def test_resume_mid_watering_stays_synced_closes_inlet():
    d = _dist_cfg(**{"active_cycle": {"outlet": 2, "phase": "watering"}})
    c = _recon_host([d])
    await c.async_resume_distributor_cycles()
    c._dist_close_inlet.assert_awaited_once()   # defensive close
    c._dist_clear_cycle.assert_awaited_once_with(0)
    c._dist_mark_uncertain.assert_not_awaited()  # position still known


async def test_resume_mid_pausing_marks_uncertain():
    d = _dist_cfg(**{"active_cycle": {"outlet": 2, "phase": "pausing"}})
    c = _recon_host([d])
    await c.async_resume_distributor_cycles()
    c._dist_close_inlet.assert_awaited_once()
    c._dist_clear_cycle.assert_awaited_once_with(0)
    c._dist_mark_uncertain.assert_awaited_once()  # advance completion unknown
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'async_resume_distributor_cycles'`).

- [ ] **Step 3: Add the method** to `DistributorMixin` (after `async_distributor_resync_home`):

```python
    # --- restart reconciliation -------------------------------------------

    async def async_resume_distributor_cycles(self) -> None:
        """Reconcile in-flight distributor cycles after a restart (spec §7).

        crashed mid-watering (before the advance) -> the position is still known
        (current_outlet == the watered outlet): defensively close the inlet and
        clear the in-flight record, staying synced.
        crashed mid-pausing (the advance may or may not have completed on the
        blind device) -> mark uncertain (de-arm) and require a re-sync.
        """
        for dist in await self.store.async_get_distributors():
            cycle = dist.get("active_cycle") or {}
            if not cycle:
                continue
            await self._dist_close_inlet(dist)
            await self._dist_clear_cycle(dist.get("id"))
            if cycle.get("phase") == "pausing":
                await self._dist_mark_uncertain(dist, reason="restart_mid_advance")
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Run the full distributor test files for regressions:**

Run (via the wrapper): `-m pytest tests/test_distributor.py tests/test_distributor_cycle.py tests/test_master.py -p _local_socket_unblock -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -m "feat(distributor): restart reconciliation (phase-based)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan C Self-Review

- **Spec coverage:** guard synced+confirmed / test-run exempt (§5.1) → Task 3/4; Rule B rain-delay + nothing-due (§5.1/§5.2) → Task 3; full sweep, skip-pulse, disabled-still-pulses, soil-veto side-effects (§5.2) → Task 3; safety-halt on no-flow (§7) → Task 3; per-window credit (§6) → Task 2; test-run (§10) → Task 4; manual re-sync, no auto re-arm (§7) → Task 5; phase-based restart reconciliation (§7) → Task 6.
- **Deferred to Plan D (integration):** wiring `DistributorMixin` into `SmartIrrigationCoordinator` (add to the mixin list); the services (`distributor_set_outlet`/`resync_home`/`run_now`/`test_run`) in `services.py`/`services.yaml`; schedule-target dispatch (`_perform_schedule_action` → `async_run_distributor_cycle`, passing `concurrent` from the sequencing mode; excluding member zones from `_irrigate_linked_entities`); the startup resume hook (`await coordinator.async_resume_distributor_cycles()` next to `async_resume_self_closing_runs()` in `__init__.py`); the finish-anchor duration via `distributor_cycle_estimate`.
- **Documented MVP limits:** live-estimate gating not applied (classic daily gate used); full multi-holder master arbitration deferred; `concurrent` supplied by the caller.
- **No placeholders:** every step has concrete code, exact commands, expected output.
- **Type consistency:** all methods on `DistributorMixin`; the loop calls Plan-B primitives (`_dist_open_inlet`/`_dist_close_inlet`/`_dist_master_*`/`_dist_advance`/`_dist_mark_uncertain`) and coordinator helpers (`_rain_delay_active`/`_apply_soil_moisture_veto`/`_timed_volume_l`/`_credited_depth_native`/`_record_run`/`_confirm_valve_running`) — all provided by the real coordinator (Plan D) and mocked in `_CycleHost`/`_loop_host`. `RUN_TRIGGER_DISTRIBUTOR`/`DISTRIBUTOR_TEST_RUN_SECONDS`/`PROBLEM_VALVE_DID_NOT_OPEN`/`POSITION_STATE_*`/`DISTRIBUTOR_MIN_*` all exist.

## Handoff to Plan D (integration)

Plan D wires `DistributorMixin` into the coordinator, adds the services + `services.yaml`, the schedule-target discriminator + dispatch (passing `concurrent` from the sequencing mode and excluding member zones from `_irrigate_linked_entities`), the startup `async_resume_distributor_cycles()` hook, and consumes `distributor_cycle_estimate` for finish-anchored schedules. It must also honour the Plan-B caveat: guard the shared `_master_on` for non-exclusive holders.

**Plan-D notes from the Plan-C review:**
- Harden `distributor_cycle_estimate` (Plan B) the same way as the loop — `int(distributor.get("pause_seconds") or 300)` — so a persisted `None` can't raise (latent; DistributorEntry defaults are never None, but the UI could send None).
- `store.async_update_zone` zeroes a zone's `duration` when a bucket update lands **exactly** at `0.0` for an automatic zone (store.py:1063-1068). Harmless for the distributor credit path (bucket is capped at/below maximum, rarely exactly 0), but be aware when wiring.
