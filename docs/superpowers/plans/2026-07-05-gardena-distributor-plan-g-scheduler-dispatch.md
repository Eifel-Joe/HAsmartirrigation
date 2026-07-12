# Gardena Distributor — Plan G: Scheduler → distributor dispatch

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a scheduled "irrigate" run actually dispatch each Gardena distributor whose member zones are due — only due outlets water for their computed duration, the rest get a skip-pulse — so the panel outlook prediction (which already shows member zones as watered at the schedule time) becomes reality.

**Architecture:** A recurring schedule's `irrigate` action already calls `_irrigate_linked_entities(zones)` for the *non-member* zones (member zones are excluded at `irrigation.py:462`). Plan G adds one sibling call `_dispatch_distributor_cycles(zones)` right after it in `scheduler.py:_perform_schedule_action`, which runs `async_run_distributor_cycle` for each qualifying distributor. The distributor cycle already exists (Plan C/D) — Plan G is the missing *dispatch + prediction-parity + shared-master coordination* layer. The finish-anchor estimate is reworked so member zones are counted as one distributor-cycle estimate instead of their raw per-zone durations.

**Tech Stack:** Home Assistant custom integration, Python 3.12/3.13, pytest + `unittest.mock` (`AsyncMock`/`Mock`). Existing distributor unit tests use `_DistHost(DistributorMixin, MasterMixin)` in `tests/test_distributor.py`.

**Verified against source (2026-07-05):** `scheduler.py:730-791` (schedule action), `irrigation.py:434-528` (linked-entity path + member exclusion at 462 + early-return at 476-480 + rain gate at 485), `distributor.py:307-411` (cycle + guards), `distributor.py:176-210` (`_dist_master_start/window_off/window_on`), `distributor.py:205-210` (`_dist_master_end`), `distributor.py:214-243` (`distributor_cycle_estimate`), `master.py:69-135` (`async_master_begin_cycle`, `_master_note_run`, `async_master_schedule_off` — deadline-based, overlap-safe), `skip_conditions.py:376-411` (`get_total_irrigation_duration`).

---

## Key design decisions (why this shape)

1. **Hook at `scheduler.py:_perform_schedule_action`, right after line 782** (`await self.coordinator._irrigate_linked_entities(zones)`) — NOT inside `_irrigate_linked_entities` at line 511. Reason: `_irrigate_linked_entities` early-returns at 476-480 when there is no *non-member* zone to water. The user's real case is "only distributor member zones are due" → that early return fires and a line-511 hook would never run. A sibling call at the schedule level runs regardless, still sits after the weather-skip check (`scheduler.py:754`), and the only caller of `_irrigate_linked_entities` is this schedule path (verified: grep found exactly one call site), so no automatic entry point is missed.

2. **Rain-delay** is enforced twice: an explicit pre-check in `_dispatch_distributor_cycles` (records a skipped run for parity with the normal path) plus the cycle's own `_rain_delay_active()` guard at `distributor.py:335`.

3. **Shared-master coordination (mixed run: normal zones + distributor members both due).** The master is a single shared entity with a deadline-based, overlap-safe off (`master.py:_master_note_run` + `async_master_schedule_off`: turning off only fires after the latest noted run, and a later run reschedules it). Today the distributor's `_dist_master_end` bypasses this with an immediate `_master_turn(False)` — in a sequential/rotating mixed run the normal zones run as background tasks (`irrigation.py:524/526` `create_task`) and the distributor's end-off would stomp them. Plan G fixes this in two places:
   - `_dist_master_end` → uses `_master_note_run(0)` + `async_master_schedule_off()` (deadline-aware) instead of the immediate turn-off, so it never powers off while a concurrent run is pending.
   - `concurrent` is True when the master is already claimed by a pending run (a normal-zone deadline is set), suppressing the per-pause master cycling that would otherwise interrupt those zones. In parallel sequencing the normal zones are awaited before dispatch, so there is no overlap anyway; in a distributor-only sequential/rotating run no deadline is pending, so per-pause cycling still works as the user configured.

4. **Prediction parity (finish-anchor).** The outlook already *predicts* member zones by summing their raw `ZONE_DURATION` (`skip_conditions.py:get_total_irrigation_duration`), which is wrong for a distributor sweep (windows + n·pause + settle + buffer). Plan G reworks that estimate to add one `distributor_cycle_estimate` per in-scope distributor instead, so the finish-anchor start-time math and the executed cycle agree.

## Files touched

- **Modify** `custom_components/smart_irrigation/const.py` — 3 new phase/reason constants (after the distributor block, ~line 621).
- **Modify** `custom_components/smart_irrigation/distributor.py` — replace 4 phase string literals with constants; rework `_dist_master_end` to be deadline-aware; add `_distributor_concurrent(...)` and `_dispatch_distributor_cycles(...)` (these live on the same coordinator class that already mixes in `DistributorMixin` — put them in `distributor.py` next to the other `_dist_*` helpers so the distributor logic stays together).
- **Modify** `custom_components/smart_irrigation/scheduler.py` — one line in `_perform_schedule_action` after 782.
- **Modify** `custom_components/smart_irrigation/skip_conditions.py` — rework `get_total_irrigation_duration` (376-411) for distributor estimates.
- **Test** `tests/test_distributor_dispatch.py` (new) — dispatch, guards, concurrency, master coordination, hook, estimate, no-double-drive.

> **Host for tests:** the coordinator composes many mixins. For unit tests, extend the existing `_DistHost` pattern (`tests/test_distributor.py:11-30`) to a `_DispatchHost(DistributorMixin, MasterMixin)` and attach the new methods' dependencies as `Mock`/`AsyncMock`: `self.store` (with `async_get_distributors`, `async_get_zones`, `config`), `self.async_run_distributor_cycle` (AsyncMock when testing the dispatcher in isolation), `self._dist_members` (AsyncMock), `self._dist_needs_water` (Mock), `self._rain_delay_active` (Mock), `self._record_skipped_run` (AsyncMock). Because the new methods are defined on `DistributorMixin`, `_DispatchHost` gets the real ones; patch only what a given test isolates.

---

### Task G1: Promote distributor phase literals to constants

**Files:**
- Modify: `custom_components/smart_irrigation/const.py` (after the distributor block ~line 621)
- Modify: `custom_components/smart_irrigation/distributor.py:376, 402, 456, 457`
- Test: `tests/test_distributor.py` (add one test)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_distributor.py
from unittest.mock import AsyncMock

async def test_cycle_persists_phase_constants_not_raw_strings():
    c = _host()
    c.store.async_get_zones = AsyncMock(return_value=[
        {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 5,
         "bucket": -1, "bucket_threshold": 0, "state": "automatic"},
    ])
    c._dist_persist_cycle = AsyncMock()
    c._dist_sleep = AsyncMock()
    c._dist_open_inlet = AsyncMock()
    c._dist_close_inlet = AsyncMock()
    await c.async_run_distributor_cycle(_dist(current_outlet=1), test_run=True)
    phases = [call.args[2] for call in c._dist_persist_cycle.await_args_list]
    assert const.DISTRIBUTOR_PHASE_WATERING in phases
    assert const.DISTRIBUTOR_PHASE_PAUSING in phases
    assert "watering" not in [p for p in phases if not isinstance(p, str)]  # constants only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_distributor.py::test_cycle_persists_phase_constants_not_raw_strings -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'DISTRIBUTOR_PHASE_WATERING'`

- [ ] **Step 3: Add the constants**

```python
# const.py, after DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS (~line 619-621)
DISTRIBUTOR_PHASE_WATERING = "watering"
DISTRIBUTOR_PHASE_PAUSING = "pausing"
DISTRIBUTOR_REASON_RESTART_MID_ADVANCE = "restart_mid_advance"
```

- [ ] **Step 4: Replace the 4 literals in distributor.py**

- `distributor.py:376` `..., "watering")` → `..., const.DISTRIBUTOR_PHASE_WATERING)`
- `distributor.py:402` `..., "pausing")` → `..., const.DISTRIBUTOR_PHASE_PAUSING)`
- `distributor.py:456` `== "pausing"` → `== const.DISTRIBUTOR_PHASE_PAUSING`
- `distributor.py:457` `reason="restart_mid_advance"` → `reason=const.DISTRIBUTOR_REASON_RESTART_MID_ADVANCE`

- [ ] **Step 5: Run test + full suite**

Run: `pytest tests/test_distributor.py -q`
Expected: PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "refactor(distributor): promote cycle phase literals to constants"
```

---

### Task G2: Deadline-aware distributor master-end

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:205-210` (`_dist_master_end`)
- Test: `tests/test_distributor_dispatch.py` (new file)

**Current code (`distributor.py:205-210`):**
```python
async def _dist_master_end(self, distributor: dict) -> None:
    if self._dist_uses_master(distributor) and self._dist_master_off_after():
        await self._master_turn(False)
    self._master_on = False
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_distributor_dispatch.py
import datetime
from unittest.mock import AsyncMock, Mock
from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.distributor import DistributorMixin
from custom_components.smart_irrigation.master import MasterMixin
from tests.test_distributor import _host, _dist   # reuse fixtures


async def test_master_end_defers_to_pending_deadline_not_immediate_off():
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c.async_master_schedule_off = AsyncMock()
    # a concurrent normal-zone run has already claimed the master
    c._master_off_deadline = c._master_now() + datetime.timedelta(seconds=120)
    await c._dist_master_end(_dist())
    # must NOT power the master off directly while a run is pending
    c.hass.services.async_call.assert_not_awaited()
    # must hand the shutdown to the overlap-safe deadline mechanism
    c.async_master_schedule_off.assert_awaited_once()
```

(`_host` must expose `_master_now`; it already does via MasterMixin. If not, set `c._master_now = lambda: datetime.datetime.now(datetime.timezone.utc)` in the test.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_distributor_dispatch.py::test_master_end_defers_to_pending_deadline_not_immediate_off -v`
Expected: FAIL — current code calls `_master_turn(False)` (→ `hass.services.async_call`) immediately.

- [ ] **Step 3: Rework `_dist_master_end`**

```python
async def _dist_master_end(self, distributor: dict) -> None:
    """End of cycle: hand the master shutdown to the shared, overlap-safe
    deadline mechanism so a concurrent normal-zone run is never stomped. Note
    a zero-length run (extends the deadline to now iff nothing later is
    pending) then schedule the off; async_master_schedule_off powers down and
    clears _master_on only once the latest deadline has passed."""
    if not self._dist_uses_master(distributor):
        self._master_on = False
        return
    self._master_note_run(0)
    await self.async_master_schedule_off()
```

- [ ] **Step 4: Run test + the existing master-coupled distributor tests**

Run: `pytest tests/test_distributor.py tests/test_distributor_dispatch.py -q`
Expected: PASS. If a pre-existing test asserted the old immediate-off behaviour, update it to assert the deadline path (note it in the commit).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git commit -m "fix(distributor): master-end uses the shared overlap-safe off deadline"
```

---

### Task G3: `_distributor_concurrent` — parallel OR shared-master-pending

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (new method near `_dist_uses_master`)
- Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_distributor_concurrent_true_for_parallel_or_pending_master():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    c._master_off_deadline = None
    assert c._distributor_concurrent() is True             # parallel

    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
    c._master_off_deadline = None
    assert c._distributor_concurrent() is False            # solo sequential

    # a normal-zone run already claimed the master -> keep master up
    import datetime
    c._master_off_deadline = c._master_now() + datetime.timedelta(seconds=60)
    assert c._distributor_concurrent() is True             # mixed run
```

- [ ] **Step 2: Run to verify FAIL** (`AttributeError`).

- [ ] **Step 3: Implement**

```python
def _distributor_concurrent(self) -> bool:
    """True when the distributor must keep the shared master powered through
    its pauses: parallel zone_sequencing (other zones run at once), OR a
    normal-zone run has already claimed the master (a future off-deadline is
    set), i.e. a mixed schedule run. False for a solo sequential/rotating
    distributor run, where per-pause master cycling is the configured
    behaviour."""
    if self.store.config.zone_sequencing == const.CONF_ZONE_SEQUENCING_PARALLEL:
        return True
    deadline = getattr(self, "_master_off_deadline", None)
    return deadline is not None and self._master_now() < deadline
```

- [ ] **Step 4: Run test PASS.**
- [ ] **Step 5: Commit** `feat(distributor): derive cycle concurrency from sequencing + shared master`

---

### Task G4: `_dispatch_distributor_cycles` — skip unqualified distributors

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (new async method)
- Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_dispatch_skips_unqualified_distributors():
    c = _host()
    c.async_run_distributor_cycle = AsyncMock(return_value=False)
    c._rain_delay_active = Mock(return_value=False)
    c.store.async_get_distributors = AsyncMock(return_value=[
        _dist(id=0, position_state=const.POSITION_STATE_UNCERTAIN),
        _dist(id=1, commissioning_confirmed=False),
        _dist(id=2, active_cycle={"outlet": 1, "phase": "watering"}),
        _dist(id=3),                       # synced+confirmed but no members
    ])
    async def _members(did):
        return [] if did == 3 else [{"id": 99, "distributor_id": did}]
    c._dist_members = AsyncMock(side_effect=_members)
    c._dist_needs_water = Mock(return_value=True)
    await c._dispatch_distributor_cycles("all")
    c.async_run_distributor_cycle.assert_not_awaited()
```

- [ ] **Step 2: Run FAIL** (`AttributeError`).

- [ ] **Step 3: Implement (skip-gates only, no run call yet — but include the loop so step 4 flips it)**

```python
async def _dispatch_distributor_cycles(self, zone_ids=None) -> None:
    """Plan G: run each qualifying distributor's cycle on a scheduled irrigate.
    Member zones were excluded from the normal path (irrigation.py:462), so this
    is their sole automatic driver. Pre-guards avoid arming the master for a
    distributor that would immediately no-op; the cycle's own guards
    (distributor.py:321/323/335/344) remain authoritative."""
    if self._rain_delay_active():
        await self._record_skipped_run(zone_ids, const.SKIP_REASON_PAUSED)
        return
    want_all = zone_ids is None or zone_ids == "all"
    target = None if want_all else {int(z) for z in zone_ids}
    concurrent = self._distributor_concurrent()
    for dist in await self.store.async_get_distributors():
        if dist.get("position_state") != const.POSITION_STATE_SYNCED:
            continue
        if not dist.get("commissioning_confirmed"):
            continue
        if dist.get("active_cycle"):
            continue
        members = await self._dist_members(dist.get("id"))
        if not members:
            continue
        if target is not None and not any(
            int(m.get(const.ZONE_ID)) in target for m in members
        ):
            continue
        if not any(self._dist_needs_water(m) for m in members):
            continue
        await self.async_run_distributor_cycle(dist, concurrent=concurrent)
```

> Verify `const.SKIP_REASON_PAUSED` exists (used at `irrigation.py:490`). It does.

- [ ] **Step 4: Run test PASS** (all four distributors are skipped by a guard).
- [ ] **Step 5: Commit** `feat(distributor): dispatch skip-gates for scheduled cycles`

---

### Task G5: `_dispatch_distributor_cycles` runs a qualified distributor with the derived concurrency + honours a zone subset

**Files:** as G4. Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_dispatch_runs_due_distributor_with_derived_concurrency():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    c._master_off_deadline = None
    c.async_run_distributor_cycle = AsyncMock(return_value=True)
    c._rain_delay_active = Mock(return_value=False)
    d = _dist(id=0)
    c.store.async_get_distributors = AsyncMock(return_value=[d])
    c._dist_members = AsyncMock(return_value=[{"id": 7, "distributor_id": 0}])
    c._dist_needs_water = Mock(return_value=True)
    await c._dispatch_distributor_cycles("all")
    c.async_run_distributor_cycle.assert_awaited_once()
    assert c.async_run_distributor_cycle.await_args.kwargs["concurrent"] is True


async def test_dispatch_respects_target_subset():
    c = _host()
    c.async_run_distributor_cycle = AsyncMock(return_value=True)
    c._rain_delay_active = Mock(return_value=False)
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0), _dist(id=1)])
    async def _members(did):
        return [{"id": 7 if did == 0 else 8, "distributor_id": did}]
    c._dist_members = AsyncMock(side_effect=_members)
    c._dist_needs_water = Mock(return_value=True)
    await c._dispatch_distributor_cycles([7])          # only distributor 0 owns zone 7
    assert c.async_run_distributor_cycle.await_count == 1
    assert c.async_run_distributor_cycle.await_args.args[0].get("id") == 0
```

- [ ] **Step 2: Run.** These PASS already if G4's loop is complete (it is). If either fails, fix the loop. (This task locks the run-call + subset behaviour with tests; no new impl expected.)
- [ ] **Step 3: Commit** `test(distributor): dispatch runs due distributor + honours subset`

---

### Task G6: Rain-delay pre-check records a skipped run

**Files:** as G4. Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Failing test**

```python
async def test_dispatch_rain_delay_records_skip_and_runs_nothing():
    c = _host()
    c._rain_delay_active = Mock(return_value=True)
    c._record_skipped_run = AsyncMock()
    c.async_run_distributor_cycle = AsyncMock()
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    await c._dispatch_distributor_cycles("all")
    c.async_run_distributor_cycle.assert_not_awaited()
    c._record_skipped_run.assert_awaited_once()
```

- [ ] **Step 2: Run.** PASSES if G4 included the rain-delay pre-check (it does). Otherwise add it.
- [ ] **Step 3: Commit** `test(distributor): rain-delay pre-check on scheduled dispatch`

---

### Task G7: Hook the dispatch into the schedule action

**Files:**
- Modify: `custom_components/smart_irrigation/scheduler.py:782-783`
- Test: `tests/test_scheduler_distributor.py` (new) — or add to the dispatch test file with a scheduler host.

**Insertion (`scheduler.py`, after 782):**
```python
                await self.coordinator._irrigate_linked_entities(zones)
                # Plan G: also run distributor cycles for due member zones. Members
                # are excluded from _irrigate_linked_entities (irrigation.py:462), so
                # this is their sole automatic driver, and it runs even when no
                # non-member zone is due (that path early-returns at irrigation.py:476).
                await self.coordinator._dispatch_distributor_cycles(zones)
                await self.coordinator._reset_days_since_irrigation()
```

- [ ] **Step 1: Failing test** — assert the schedule action calls dispatch after linked-entities, and that a *member-only* schedule (linked-entities a no-op) still dispatches.

```python
# tests/test_scheduler_distributor.py
from unittest.mock import AsyncMock, Mock

async def test_scheduled_irrigate_dispatches_distributors_even_when_no_normal_zone(make_scheduler):
    sched = make_scheduler()                       # helper builds Scheduler with a Mock coordinator
    coord = sched.coordinator
    coord._check_skip_conditions = AsyncMock(return_value=False)
    coord._irrigate_linked_entities = AsyncMock()  # no-op: no normal zones due
    coord._dispatch_distributor_cycles = AsyncMock()
    coord._reset_days_since_irrigation = AsyncMock()
    await sched._perform_schedule_action("irrigate", "all", "test")
    coord._dispatch_distributor_cycles.assert_awaited_once_with("all")
```

> `make_scheduler` fixture: instantiate the scheduler class with `hass=Mock()` and `coordinator=Mock()` whose async methods are `AsyncMock`. Mirror how the existing scheduler tests build it (`tests/test_scheduler*.py`); if none exist, construct directly.

- [ ] **Step 2: Run FAIL** (`_dispatch_distributor_cycles` not called — the line isn't there yet).
- [ ] **Step 3: Add the one line** (above).
- [ ] **Step 4: Second test — weather-skip blocks dispatch**

```python
async def test_weather_skip_blocks_distributor_dispatch(make_scheduler):
    sched = make_scheduler()
    coord = sched.coordinator
    coord._check_skip_conditions = AsyncMock(return_value=True)
    coord._record_skipped_run = AsyncMock()
    coord._dispatch_distributor_cycles = AsyncMock()
    await sched._perform_schedule_action("irrigate", "all", "test")
    coord._dispatch_distributor_cycles.assert_not_awaited()   # returns at the skip branch
```

- [ ] **Step 5: Run both PASS.**
- [ ] **Step 6: Commit** `feat(distributor): scheduled irrigate dispatches distributor cycles (Plan G)`

---

### Task G8: Finish-anchor estimate counts the distributor cycle, not raw member durations

**Files:**
- Modify: `custom_components/smart_irrigation/skip_conditions.py:376-411` (`get_total_irrigation_duration`)
- Test: `tests/test_distributor_dispatch.py` (host must own `distributor_cycle_estimate` + `_dist_members` — `_DispatchHost` does)

- [ ] **Step 1: Failing test**

```python
async def test_total_duration_uses_distributor_cycle_estimate_not_raw_sum():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
    members = [
        {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 60,
         "state": "automatic"},
        {"id": 8, "distributor_id": 0, "outlet_number": 2, "duration": 0,
         "state": "automatic"},
        {"id": 9, "distributor_id": 0, "outlet_number": 3, "duration": 60,
         "state": "automatic"},
    ]
    normal = {"id": 1, "distributor_id": None, "duration": 120, "state": "automatic"}
    c.store.async_get_zones = AsyncMock(return_value=members + [normal])
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    c._dist_members = AsyncMock(return_value=members)
    est = c.distributor_cycle_estimate(_dist(id=0), members)   # real formula
    total = await c.get_total_irrigation_duration("all")
    assert total == int(120 + est)
    assert total != 120 + 60 + 0 + 60          # NOT the naive per-member sum
```

- [ ] **Step 2: Run FAIL** (current code sums raw member durations → 240).
- [ ] **Step 3: Rework `get_total_irrigation_duration`**

```python
async def get_total_irrigation_duration(self, zone_ids=None) -> int:
    """... (docstring unchanged, plus:) distributor member zones are counted as
    ONE distributor_cycle_estimate per distributor, not as their individual
    durations, so the finish-anchor start time matches the real sweep."""
    zones = await self.store.async_get_zones()
    want_all = zone_ids is None or zone_ids == "all"
    target = None if want_all else {int(z) for z in zone_ids}

    durations = []
    for zone in zones:
        if zone.get(const.ZONE_STATE) not in (
            const.ZONE_STATE_AUTOMATIC,
            const.ZONE_STATE_MANUAL,
        ):
            continue
        if target is not None and int(zone.get(const.ZONE_ID)) not in target:
            continue
        if zone.get(const.ZONE_DISTRIBUTOR_ID) is not None:
            continue                       # counted via its distributor below
        duration = zone.get(const.ZONE_DURATION, 0) or 0
        if duration > 0:
            durations.append(duration)

    for dist in await self.store.async_get_distributors():
        members = await self._dist_members(dist.get("id"))
        in_scope = [
            m for m in members
            if target is None or int(m.get(const.ZONE_ID)) in target
        ]
        if in_scope:
            durations.append(int(self.distributor_cycle_estimate(dist, in_scope)))

    if not durations:
        return 0
    if self.store.config.zone_sequencing == const.CONF_ZONE_SEQUENCING_PARALLEL:
        return int(max(durations))
    return int(sum(durations))
```

- [ ] **Step 4: Add the parallel-reduction test**

```python
async def test_total_duration_parallel_takes_max_over_distributor_and_zones():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    members = [{"id": 7, "distributor_id": 0, "outlet_number": 1,
                "duration": 30, "state": "automatic"}]
    normal = {"id": 1, "distributor_id": None, "duration": 5, "state": "automatic"}
    c.store.async_get_zones = AsyncMock(return_value=members + [normal])
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    c._dist_members = AsyncMock(return_value=members)
    est = int(c.distributor_cycle_estimate(_dist(id=0), members))
    assert await c.get_total_irrigation_duration("all") == max(5, est)
```

- [ ] **Step 5: Run both PASS + full suite.**
- [ ] **Step 6: Commit** `fix(distributor): finish-anchor estimate uses cycle estimate for member zones`

---

### Task G9: Regression lock — member zones never double-driven

**Files:** test-only (guards `irrigation.py:462`). Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Test**

```python
async def test_member_zone_excluded_from_linked_entity_candidates():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    c._rain_delay_active = Mock(return_value=False)
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    c._apply_live_durations = AsyncMock(side_effect=lambda z: z)
    c.async_master_begin_cycle = AsyncMock()
    c.async_master_schedule_off = AsyncMock()
    c._master_note_run = Mock()
    c._irrigate_zones_parallel = AsyncMock()
    c._sc_is_self_closing = Mock(return_value=False)
    member = {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 30,
              "bucket": -1, "bucket_threshold": 0, "state": "automatic",
              "linked_entity": "switch.x"}
    normal = {"id": 1, "distributor_id": None, "duration": 30, "bucket": -1,
              "bucket_threshold": 0, "state": "automatic", "linked_entity": "switch.y"}
    c.store.async_get_zones = AsyncMock(return_value=[member, normal])
    await c._irrigate_linked_entities("all")
    passed = c._irrigate_zones_parallel.await_args.args[0]
    ids = {z["id"] for z in passed}
    assert 7 not in ids and 1 in ids       # member excluded, normal kept
```

- [ ] **Step 2: Run.** PASSES (locks the existing exclusion at line 462). If it fails, the exclusion regressed — fix `irrigation.py:462`.
- [ ] **Step 3: Commit** `test(distributor): lock member-zone exclusion from the normal path`

---

## Known limitation (document, out of Plan G scope)

**Cross-distributor partial-target schedules are not outlet-precise.** A schedule targeting a specific zone subset dispatches a distributor if *any* of its members is in the subset; the cycle then waters *all* of that distributor's currently-due members (the engine's `to_water` set), not only the targeted ones. This is correct for the common cases (schedule targets "all" or whole distributors). Outlet-precise subset selection would require passing a `to_water_filter` into `async_run_distributor_cycle` — a later enhancement. Note this in the distributor docs.

## After Plan G → Beta 2

Bump to the next PEP440 `bN`, rebuild `dist`, run `uvx black --check`, run the full pytest suite, release as a pre-release for the test-HA (192.168.10.196). Re-verify via MCP: arm a distributor, let the daily schedule fire, and confirm the inlet/master pulse pattern matches the outlook estimate.

## Self-review checklist (done)

- **Spec coverage:** dispatch (G4/G5), hook (G7), concurrency (G3), master coordination (G2/G3), rain-delay (G6), weather-skip (G7), finish-anchor parity (G8), no-double-drive (G9), constants (G1) — all covered.
- **Type/name consistency:** `_dispatch_distributor_cycles`, `_distributor_concurrent`, `distributor_cycle_estimate`, `_dist_members`, `_dist_needs_water`, `async_run_distributor_cycle`, `_master_note_run`, `async_master_schedule_off` — used consistently across tasks.
- **No placeholders:** every code step shows real code.
