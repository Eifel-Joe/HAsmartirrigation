# The chain carries its plan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A sequential self-closing chain delivers the run its cycle planned, never waters a zone twice, and never drops a queued zone without saying so.

**Architecture:** `Chain.zones` keeps holding bare ints. A sibling dict `Chain.planned` maps `zone_id -> ZonePlan(seconds, live)` and carries what the dispatching cycle decided. At dispatch the stored zone is re-read as it is today and only `ZONE_DURATION` is overlaid — the same shape the rotation already uses at `run_chain.py:407` / `:433-434`. A missing plan means "use the stored duration" (today's behaviour), never "drop the zone".

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest + pytest-homeassistant-custom-component. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-22-chain-carries-its-plan-design.md`

**Issues:** `Eifel-Joe#2` (F1, F3, F4) and `Eifel-Joe#43` (M1).

---

## Before you start

**Worktree:** `D:/Entwicklung/HASI/issue2-work/wt`, branch `fix/chain-carries-zone-snapshots`, based on `upstream/master` = `965a4f9d`.

**The worktree has no `.venv`.** Use the main checkout's interpreter. Canonical test command for this plan:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock -q
```

**Baseline, measured on `965a4f9d`:** 7 failed, 3191 passed, 9 skipped, 320 errors. The 327 failing/erroring test names are in `D:/Entwicklung/HASI/issue2-work/baseline-names.txt`. They are pre-existing Windows environment failures; CI is the real gate.

**A throwaway repro exists** at `tests/test_zz_repro_issue2.py`. It asserts today's buggy behaviour and is green on `965a4f9d`. Leave it in place while you work — it is the cross-check that you are changing what you think you are changing. Task 10 removes it.

**Never** solve any of this by registering the chain's queued zones through `_claim_chain_zones`. After such a claim `run_chain.py:248` would `continue` past every waiting zone and `run_chain.py:408-412` would zero the whole rotation on the first pass. `tests/test_opensprinkler.py:602` goes red if you do.

---

## File structure

| File | Responsibility | Change |
| --- | --- | --- |
| `custom_components/irrigation_plus/run_chain.py` | the chain engine; the one production file this plan really changes | modified throughout |
| `custom_components/irrigation_plus/irrigation.py:204-207` | `_drop_live_run_marker`'s docstring, which this plan makes `run_chain.py` a caller of | one dangling name corrected (Task 4) |
| `tests/test_chain_carries_its_plan.py` | new test module for everything in this plan | created in Task 1 |
| `tests/test_service_chain.py` | existing oracle for service-mode chaining | **unchanged** — it supplies the fixtures we import |
| `tests/test_opensprinkler.py` | the engine's declared oracle (`run_chain.py:17-19`) | **unchanged** — must keep passing |
| `tests/test_zz_repro_issue2.py` | throwaway cross-check | deleted in Task 10 |

---

## Task 1: `ZonePlan` carries the duration the cycle decided

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:51-81` (dataclasses), `:188-190` (build), `:241-251` (consume)
- Test: `tests/test_chain_carries_its_plan.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_chain_carries_its_plan.py`:

```python
"""The sequential chain delivers the run its cycle planned (Eifel-Joe#2).

``Chain.zones`` holds bare ids and ``_chain_advance`` re-reads the stored zone, so
everything the dispatching cycle decided about a queued zone -- the live duration and
the live-estimate marker -- used to be dropped between the two. A sibling
``Chain.planned`` now carries it, mirroring how ``Rotation.remaining`` already carries
the rotating half's own plan.

The fixtures come from test_service_chain.py, whose ``_coord`` spy records
``(zone_id, duration)`` for every dispatch.
"""

from custom_components.irrigation_plus import const

from .test_service_chain import (
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)


def _live(zone, duration):
    """What irrigation._apply_live_durations hands the dispatcher: a COPY."""
    return {**zone, const.ZONE_DURATION: duration}


class TestTheQueueRemembersWhatTheCycleDecided:
    async def test_a_queued_zone_waters_the_live_duration_not_the_stored_one(
        self, hass
    ):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        await _finish(c, 1)
        assert c._dispatched == [(1, 300.0), (2, 300.0)]

    async def test_a_zone_with_no_plan_falls_back_to_the_stored_duration(self, hass):
        """Drift must degrade to today's behaviour, never to a dropped zone."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        state.planned.clear()  # simulate the two structures drifting apart
        await _finish(c, 1)
        assert c._dispatched == [(1, 600.0), (2, 600.0)]

    async def test_the_stored_duration_no_longer_decides_a_planned_zone(self, hass):
        """A calculation landing mid-chain cannot shorten or delete the run."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        c._zones[2] = {**c._zones[2], const.ZONE_DURATION: 0}
        await _finish(c, 1)
        assert c._dispatched == [(1, 600.0), (2, 600.0)]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 3 failed.
- `test_a_queued_zone_waters_the_live_duration_not_the_stored_one`: `assert [(1, 300.0), (2, 600.0)] == [(1, 300.0), (2, 300.0)]`
- `test_a_zone_with_no_plan_falls_back_to_the_stored_duration`: `AttributeError: 'Chain' object has no attribute 'planned'`
- `test_the_stored_duration_no_longer_decides_a_planned_zone`: `assert [(1, 600.0)] == [(1, 600.0), (2, 600.0)]`

- [ ] **Step 3: Add the `ZonePlan` dataclass**

In `run_chain.py`, immediately above `class Chain` (currently line 67):

```python
@dataclass(frozen=True)
class ZonePlan:
    """What the dispatching cycle decided for a zone still waiting its turn.

    The queue holds ids and the advance re-reads the store, which is right for
    everything that can legitimately change while a zone waits -- its valve, its
    confirm entity, and above all its bucket, which is the absolute anchor the run
    reconciles from (``self_closing.py:657``). It is wrong for the one thing the
    cycle itself decided: how long this run is. ``_apply_live_durations`` prices
    that into a COPY (``irrigation.py:2316``) that nothing stores, so without this
    the copy dies at the queue and the zone waters its stale daily duration.

    ``live`` travels with it because the marker set is rebound wholesale on every
    scheduled call (``irrigation.py:2296``), which would otherwise strip a queued
    zone's ceiling allowance before its turn came.
    """

    seconds: float
    live: bool = False
```

- [ ] **Step 4: Add the `planned` field to `Chain`**

In `run_chain.py`, change the `Chain` dataclass body. Current:

```python
    zones: list = field(default_factory=list)
    trigger: object | None = None
```

becomes:

```python
    zones: list = field(default_factory=list)
    planned: dict = field(default_factory=dict)
    trigger: object | None = None
```

and extend the class docstring's second paragraph with:

```python
    ``planned`` maps a queued zone's id to its :class:`ZonePlan`. It is a sibling of
    ``zones`` rather than its element type because ``_chain_drop_zone`` compares
    ``int(z)`` against a zone id (:meth:`_chain_drop_zone`) and that method is the
    first thing ``async_stop_zone`` calls. A missing entry means "use the stored
    duration", so the two structures drifting apart degrades to the old behaviour
    instead of dropping a run.
```

- [ ] **Step 5: Build the plan at dispatch**

In `async_dispatch_chained_zones`, replace the single assignment at line 189:

```python
        state.zones = [int(z.get(const.ZONE_ID)) for z in zones[1:]]
```

with:

```python
        live_now = getattr(self, "_live_run_zones", None) or set()
        state.zones = [int(z.get(const.ZONE_ID)) for z in zones[1:]]
        state.planned = {
            int(z.get(const.ZONE_ID)): ZonePlan(
                seconds=float(z.get(const.ZONE_DURATION) or 0),
                live=int(z.get(const.ZONE_ID)) in live_now,
            )
            for z in zones[1:]
        }
```

- [ ] **Step 6: Consume the plan at the advance**

In `_chain_advance`, replace the loop body's first four lines. Current:

```python
        while state.zones:
            zone_id = state.zones.pop(0)
            zone = self.store.get_zone(zone_id) or {}
            if self._chain_zone_mode(zone) != mode:
                continue
            if (zone.get(const.ZONE_DURATION) or 0) <= 0:
                continue
```

becomes:

```python
        while state.zones:
            zone_id = state.zones.pop(0)
            plan = state.planned.pop(zone_id, None)
            zone = self.store.get_zone(zone_id) or {}
            if self._chain_zone_mode(zone) != mode:
                continue
            if plan is not None:
                # One field, not a snapshot. Everything else is re-read on purpose:
                # ZONE_BUCKET is the run's absolute reconcile anchor and must be
                # current, not as it stood when the cycle began.
                zone = dict(zone, **{const.ZONE_DURATION: plan.seconds})
            if (zone.get(const.ZONE_DURATION) or 0) <= 0:
                continue
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 3 passed.

- [ ] **Step 8: Run the two oracles to verify nothing regressed**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_chain.py tests/test_opensprinkler.py -p _local_socket_unblock -q
```

Expected: 93 passed, 14 errors (the 14 errors are the pre-existing Windows environment failures).

- [ ] **Step 9: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): a queued zone waters the duration its cycle decided

The sequential chain held its waiters as bare ids and re-read the stored zone
when their turn came, so the duration the live estimate priced into the
dispatch copy (irrigation.py:2316) never reached them: zones 2..N watered the
stale daily figure, and a stored 0 dropped the run outright.

A sibling Chain.planned now carries it, the way Rotation.remaining already
carries the rotating half's plan. Only ZONE_DURATION is overlaid; the rest of
the zone is still re-read, because ZONE_BUCKET is the run's absolute reconcile
anchor and freezing it would rewind every credit that landed mid-cycle.

A missing plan means "use the stored duration", so drift between the two
structures degrades to the previous behaviour rather than dropping a run.
EOF
```

---

## Task 2: `planned` stays in step with `zones`

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:269-302` (`_chain_drop_zone`, `_chain_release`, `_chain_teardown`), `:344-346` (`_chain_start_rotation`)
- Test: `tests/test_chain_carries_its_plan.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chain_carries_its_plan.py`:

```python
class TestThePlanIsDroppedWithTheQueue:
    async def test_stopping_a_queued_zone_drops_its_plan_too(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        c._chain_drop_zone(2)
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        assert state.zones == []
        assert state.planned == {}

    async def test_releasing_the_chain_clears_the_plan(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        await c._chain_release(const.WATERING_MODE_SERVICE)
        assert c._chain_state(const.WATERING_MODE_SERVICE).planned == {}

    async def test_teardown_clears_the_plan(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        c._chain_teardown()
        assert c._chain_state(const.WATERING_MODE_SERVICE).planned == {}

    async def test_starting_a_rotation_clears_a_sequential_plan(self, hass):
        """The two geometries are exclusive; a leftover plan must not survive."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        await c._chain_start_rotation(
            [c._zones[1], c._zones[2]],
            mode=const.WATERING_MODE_SERVICE,
            trigger="schedule",
        )
        assert c._chain_state(const.WATERING_MODE_SERVICE).planned == {}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestThePlanIsDroppedWithTheQueue -p _local_socket_unblock -q
```

Expected: 4 failed, each with `assert {2: ZonePlan(seconds=300.0, live=False)} == {}`.

- [ ] **Step 3: Keep `planned` in step in `_chain_drop_zone`**

Replace the last line of `_chain_drop_zone`:

```python
            state.zones = [z for z in state.zones if int(z) != zid]
```

with:

```python
            state.zones = [z for z in state.zones if int(z) != zid]
            state.planned.pop(zid, None)
```

- [ ] **Step 4: Keep `planned` in step in `_chain_release`**

Replace:

```python
        state.zones, state.trigger, state.rotation = [], None, None
```

with:

```python
        state.zones, state.trigger, state.rotation = [], None, None
        state.planned = {}
```

- [ ] **Step 5: Keep `planned` in step in `_chain_teardown`**

Replace:

```python
            state.zones, state.trigger, state.token = [], None, None
            state.rotation = None
```

with:

```python
            state.zones, state.trigger, state.token = [], None, None
            state.rotation = None
            state.planned = {}
```

- [ ] **Step 6: Keep `planned` in step in `_chain_start_rotation`**

Replace:

```python
        state.rotation = rotation
        state.zones = []
```

with:

```python
        state.rotation = rotation
        state.zones = []
        # The two geometries are exclusive (see the Chain docstring); a sequential
        # plan left over from a cycle this one replaces must not outlive it.
        state.planned = {}
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): drop a queued zone's plan wherever its id is dropped

Chain.planned is a sibling of Chain.zones, so every site that empties or
filters the queue has to empty the plan with it -- otherwise a stopped zone's
plan outlives the stop and is picked up by the next cycle that reuses the id.

Covers the stop path, the release, the unload teardown, and the rotation start
(the two geometries are exclusive, so a sequential plan must not survive one).
EOF
```

---

## Task 3: the live-estimate marker travels with the plan

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:241-253` (the advance loop)
- Test: `tests/test_chain_carries_its_plan.py`

Background: `_run_ceiling` (`irrigation.py:2745-2749`) consumes `_live_run_zones` to grant a run a `maximum_bucket` ceiling instead of `max(target, pre_bucket)`. `_apply_live_durations` **rebinds** that set on every scheduled call (`irrigation.py:2292`, `:2296`), so a queued zone loses its allowance before its turn.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chain_carries_its_plan.py`:

```python
class TestTheLiveMarkerSurvivesTheQueue:
    async def test_a_queued_live_zone_keeps_its_ceiling_allowance(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = {1, 2}
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        # A second scheduled pass rebinds the set (irrigation.py:2296) and wipes
        # the marker of the zone still waiting its turn.
        c._live_run_zones = set()
        await _finish(c, 1)
        assert c._chain_state(const.WATERING_MODE_SERVICE).planned == {}
        # _run_ceiling consumed it at dispatch, which is the proof it was there.
        assert c._dispatched == [(1, 300.0), (2, 300.0)]
        assert 2 not in c._live_run_zones

    async def test_a_zone_the_cycle_did_not_mark_is_not_marked_later(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = set()
        await _dispatch(c, [z1, z2])
        await _finish(c, 1)
        assert c._live_run_zones == set()
```

The first test's real assertion is the ceiling, which `_coord` does not expose. Add this helper at the top of the module, under `_live`:

```python
def _ceiling_seen(c):
    """Record the ceiling _run_ceiling grants each dispatch, in order.

    _run_ceiling consumes the live marker, so asking it afterwards answers the
    wrong question; the only honest place to observe it is at dispatch time.
    """
    seen = []
    real = c._run_ceiling

    def _spy(zone):
        value = real(zone)
        seen.append((int(zone[const.ZONE_ID]), value))
        return value

    c._run_ceiling = _spy
    return seen
```

and rewrite the first test to use it:

```python
    async def test_a_queued_live_zone_keeps_its_ceiling_allowance(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = {1, 2}
        ceilings = _ceiling_seen(c)
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        c._live_run_zones = set()  # a second scheduled pass rebinds the set
        await _finish(c, 1)
        # 50.0 is _zone()'s ZONE_MAXIMUM_BUCKET: the live allowance, not the
        # max(target, pre_bucket) a normal run would be clamped to.
        assert ceilings == [(1, 50.0), (2, 50.0)]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestTheLiveMarkerSurvivesTheQueue -p _local_socket_unblock -q
```

Expected: 1 failed — `assert [(1, 50.0), (2, 0.0)] == [(1, 50.0), (2, 50.0)]`. The two numbers are measured, not assumed: `_run_ceiling` returns `ZONE_MAXIMUM_BUCKET` = 50.0 for a marked zone and `max(target, pre)` = `max(0.0, -20.0)` = **0.0** for an unmarked one, with `_zone_target_bucket` returning 0.0 for the plain fixture zone. The second test passes already; that is fine, it is the guard against over-marking.

- [ ] **Step 3: Re-assert the marker before dispatching a planned zone**

In `_chain_advance`, insert immediately before the `zone_run_in_flight` check:

```python
            if plan is not None and plan.live:
                # _apply_live_durations rebinds the whole set on every scheduled
                # call (irrigation.py:2296), so a zone queued across one loses the
                # allowance its own cycle granted it. Put it back for the dispatch;
                # _run_ceiling consumes it there as it would have on the first pass.
                live = getattr(self, "_live_run_zones", None)
                if live is None:
                    live = self._live_run_zones = set()
                live.add(zone_id)
            if self.zone_run_in_flight(zone_id):
                continue
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): a queued live-sized zone keeps its credit ceiling

_run_ceiling grants a live-estimate run a maximum_bucket ceiling by consuming a
marker in _live_run_zones. _apply_live_durations rebinds that set wholesale on
every scheduled call, so a zone waiting in a chain across one lost the
allowance its own cycle had granted it and was clamped as an ordinary run --
under-crediting water it did deliver.

ZonePlan.live records the marker at dispatch and the advance puts it back
before the run, where _run_ceiling consumes it exactly as it would have on the
first pass. A zone the cycle did not mark is still not marked.
EOF
```

---

## Task 4: a dropped zone hands its marker back

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:241-253`
- Test: `tests/test_chain_carries_its_plan.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestADroppedZoneHandsBackWhatItHolds:
    async def test_a_zone_dropped_for_a_mode_change_releases_its_marker(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = {1, 2}
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        # The user moves zone 2 to another watering mode while it waits.
        c._zones[2] = {
            **c._zones[2],
            const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER,
        }
        await _finish(c, 1)
        assert c._dispatched == [(1, 300.0)]
        # THE FIX: no leftover allowance for the next run of zone 2.
        assert 2 not in c._live_run_zones

    async def test_a_zone_dropped_for_a_zero_duration_releases_its_marker(self, hass):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = {1, 2}
        await _dispatch(c, [_live(z1, 300), _live(z2, 0)])
        await _finish(c, 1)
        assert c._dispatched == [(1, 300.0)]
        assert 2 not in c._live_run_zones
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestADroppedZoneHandsBackWhatItHolds -p _local_socket_unblock -q
```

Expected: 2 failed, both `assert 2 not in {1, 2}` — wait, zone 1's marker is consumed at its dispatch, so both fail on `assert 2 not in {2}`.

- [ ] **Step 3: Hand the marker back at each drop**

Rewrite the advance loop's three `continue` branches so each releases first. The loop now reads:

```python
        while state.zones:
            zone_id = state.zones.pop(0)
            plan = state.planned.pop(zone_id, None)
            zone = self.store.get_zone(zone_id) or {}
            if self._chain_zone_mode(zone) != mode:
                self._drop_live_run_marker(zone_id)
                continue
            if plan is not None:
                zone = dict(zone, **{const.ZONE_DURATION: plan.seconds})
            if (zone.get(const.ZONE_DURATION) or 0) <= 0:
                self._drop_live_run_marker(zone_id)
                continue
            if plan is not None and plan.live:
                live = getattr(self, "_live_run_zones", None)
                if live is None:
                    live = self._live_run_zones = set()
                live.add(zone_id)
            if self.zone_run_in_flight(zone_id):
                self._drop_live_run_marker(zone_id)
                continue
            if await self.async_run_self_closing(zone, trigger=state.trigger):
                return
            self._drop_live_run_marker(zone_id)
            # Refused: fall through to the next rather than stalling the chain.
        await self._chain_release(mode)
```

Keep the existing explanatory comments where they are; only the `_drop_live_run_marker` calls are new.

- [ ] **Step 4: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 11 passed.

- [ ] **Step 5: Fix the dangling reference in the docstring you just became a caller of**

`_drop_live_run_marker`'s docstring points at a function that does not exist. Verify
first, then fix:

```bash
grep -rn "_reprice_before_turn" custom_components/
```

Expected: exactly one hit, `irrigation.py:206` — the docstring itself. (A `.pyc` may
also match; ignore it.) The function it means is `_resize_queued_zone`, at
`irrigation.py:3165`. In `irrigation.py:204-207`, replace:

```python
        A live marker left behind is not inert: the next run of that zone consumes
        it and is handed a ceiling meant for a run that never watered — the same
        leak ``_reprice_before_turn`` guards against on the rotation path.
```

with:

```python
        A live marker left behind is not inert: the next run of that zone consumes
        it and is handed a ceiling meant for a run that never watered — the same
        leak ``_resize_queued_zone`` guards against on the rotation path.
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py custom_components/irrigation_plus/irrigation.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): a zone the chain drops hands its live marker back

A live marker left behind is not inert: _run_ceiling consumes it on the NEXT
run of that zone, handing a maximum_bucket allowance to a run that was priced
off the daily ledger. Every path that drops a queued zone -- reconfigured to
another mode, priced at zero, already running, or refused -- now releases it,
the way self_closing.py:645 and :765 already do for a run that never opened.

Also corrects that docstring's reference to _reprice_before_turn, a name that
exists nowhere in the package; the function is _resize_queued_zone.
EOF
```

---

## Task 5: nothing vanishes in silence

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:241-253`
- Test: `tests/test_chain_carries_its_plan.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestEveryDropIsNarrated:
    async def test_a_zone_dropped_for_its_mode_says_so(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        c._zones[2] = {
            **c._zones[2],
            const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER,
        }
        caplog.clear()
        await _finish(c, 1)
        assert any(
            "zone 2" in r.getMessage() and "watering mode" in r.getMessage()
            for r in caplog.records
        ), caplog.text

    async def test_a_zone_dropped_for_zero_duration_says_so(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 600), _live(z2, 0)])
        caplog.clear()
        await _finish(c, 1)
        assert any(
            "zone 2" in r.getMessage() and "nothing left to water" in r.getMessage()
            for r in caplog.records
        ), caplog.text

    async def test_a_refused_zone_says_so(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        z1, z2, z3 = _register(
            c, _zone(1, duration=600), _zone(2, duration=600), _zone(3, duration=600)
        )
        _refuse(c, 2)
        await _dispatch(c, [z1, z2, z3])
        caplog.clear()
        await _finish(c, 1)
        assert any(
            "zone 2" in r.getMessage() and "refused" in r.getMessage()
            for r in caplog.records
        ), caplog.text
        # and the cycle carries on rather than stopping at the refusal
        assert c._dispatched == [(1, 600.0), (3, 600.0)]
```

Add this helper next to `_live` at the top of the module. **A service zone has no
natural refusal path** — unlike an OpenSprinkler station, which refuses when it cannot
be resolved (`tests/test_opensprinkler.py:636`). Setting `ZONE_RUN_SERVICE` to `None`
does not refuse, it raises `ServiceNotFound`. So the return value is stubbed, which is
exactly the contract under test: what the chain does with a `False`.

```python
def _refuse(c, zone_id):
    """Make this one zone's dispatch return False, as a station refusal would."""
    spy = c.async_run_self_closing

    async def _maybe(zone, **kw):
        if int(zone[const.ZONE_ID]) == int(zone_id):
            return False
        return await spy(zone, **kw)

    c.async_run_self_closing = _maybe
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestEveryDropIsNarrated -p _local_socket_unblock -q
```

Expected: 3 failed, each on the `assert any(...)` with the full captured log shown and no matching line in it.

- [ ] **Step 3: Add a log line to each drop**

Add a `label` local at the top of `_chain_advance`'s loop section (the policy is already resolvable):

```python
        policy = chain_policy_for(mode)
        label = policy.label if policy else mode
```

Place it immediately before `while state.zones:`. Then give each drop its line:

```python
            if self._chain_zone_mode(zone) != mode:
                _LOGGER.info(
                    "%s: dropping zone %s from the cycle, its watering mode changed "
                    "while it waited",
                    label,
                    zone_id,
                )
                self._drop_live_run_marker(zone_id)
                continue
            if plan is not None:
                zone = dict(zone, **{const.ZONE_DURATION: plan.seconds})
            if (zone.get(const.ZONE_DURATION) or 0) <= 0:
                _LOGGER.info(
                    "%s: dropping zone %s from the cycle, nothing left to water",
                    label,
                    zone_id,
                )
                self._drop_live_run_marker(zone_id)
                continue
```

and, for the remaining two:

```python
            if self.zone_run_in_flight(zone_id):
                _LOGGER.info(
                    "%s: dropping zone %s from the cycle, another run took it over "
                    "while it waited",
                    label,
                    zone_id,
                )
                self._drop_live_run_marker(zone_id)
                continue
            if await self.async_run_self_closing(zone, trigger=state.trigger):
                return
            _LOGGER.warning(
                "%s: zone %s refused its dispatch; the cycle continues without it",
                label,
                zone_id,
            )
            self._drop_live_run_marker(zone_id)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): say which zone the cycle dropped, and why

All four ways a queued zone could leave a sequential cycle were bare
`continue`s. A zone the user had scheduled simply did not water, and the log
said nothing at all -- which is what made the duration bug above so hard to
see from the outside.

A refusal is a warning, the other three are info: they are ordinary outcomes
of a cycle that ran while the configuration moved under it.
EOF
```

---

## Task 6: the rotation's sister paths get the same treatment

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:406-413` and `:433-439`
- Test: `tests/test_chain_carries_its_plan.py`

The rotating branch writes a zone off in two places and is silent in both. Per the Schwester-Pfad rule these belong in the same change as Task 5.

- [ ] **Step 1: Write the failing test**

Append:

First extend the existing import block at the top of the module — do **not** add a
second `from .test_service_chain import` further down; `ROTATING` simply joins the
names already imported there:

```python
from .test_service_chain import (
    ROTATING,
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)
```

Then append:

```python
class TestTheRotationNarratesItsWriteOffsToo:
    async def test_a_rotating_zone_taken_over_says_which_reason_fired(
        self, hass, caplog
    ):
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        c._zones[2] = {
            **c._zones[2],
            const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER,
        }
        caplog.clear()
        await _finish(c, 1)
        assert any(
            "zone 2" in r.getMessage() and "watering mode" in r.getMessage()
            for r in caplog.records
        ), caplog.text

    async def test_a_refused_rotating_zone_says_so(self, hass, caplog):
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        _refuse(c, 2)
        await _dispatch(c, [z1, z2])
        caplog.clear()
        await _finish(c, 1)
        assert any(
            "zone 2" in r.getMessage() and "refused" in r.getMessage()
            for r in caplog.records
        ), caplog.text
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestTheRotationNarratesItsWriteOffsToo -p _local_socket_unblock -q
```

Expected: 2 failed on `assert any(...)`.

- [ ] **Step 3: Split the merged condition and narrate both halves**

In `_chain_rotation_advance`, replace:

```python
            zone = self.store.get_zone(zone_id) or {}
            if self._chain_zone_mode(zone) != mode or self.zone_run_in_flight(zone_id):
                # Reconfigured or being run by something else while the rotation
                # was waiting. Drop its remainder rather than come back to it
                # every turn for the rest of the cycle.
                rotation.remaining[zone_id] = 0.0
                continue
```

with:

```python
            zone = self.store.get_zone(zone_id) or {}
            # Split rather than merged, so the line can say which of the two it
            # was: one is the user reconfiguring, the other is a second actuator
            # taking the zone. They read identically in a log that conflates them.
            if self._chain_zone_mode(zone) != mode:
                _LOGGER.info(
                    "%s rotation: writing off zone %s, its watering mode changed "
                    "while it waited",
                    label,
                    zone_id,
                )
                self._drop_live_run_marker(zone_id)
                rotation.remaining[zone_id] = 0.0
                continue
            if self.zone_run_in_flight(zone_id):
                _LOGGER.info(
                    "%s rotation: writing off zone %s, another run took it over "
                    "while it waited",
                    label,
                    zone_id,
                )
                self._drop_live_run_marker(zone_id)
                rotation.remaining[zone_id] = 0.0
                continue
```

- [ ] **Step 4: Narrate the refusal write-off**

Replace:

```python
            # Refused. Abandon the zone rather than retry it on every turn until
            # the rotation ends.
            rotation.remaining[zone_id] = 0.0
```

with:

```python
            # Refused. Abandon the zone rather than retry it on every turn until
            # the rotation ends.
            _LOGGER.warning(
                "%s rotation: zone %s refused its slot; writing off its remaining "
                "%.0fs",
                label,
                zone_id,
                rotation.remaining[zone_id],
            )
            self._drop_live_run_marker(zone_id)
            rotation.remaining[zone_id] = 0.0
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 16 passed.

- [ ] **Step 6: Run the oracles**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_chain.py tests/test_opensprinkler.py -p _local_socket_unblock -q
```

Expected: 93 passed, 14 errors — unchanged from Task 1 Step 8.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): the rotation writes a zone off out loud as well

Same bug pattern as the sequential branch's silent drops, in the same module:
the rotation zeroes a zone's remainder in two places and neither says so. The
merged condition is split as well, because "reconfigured" and "taken over by
another run" are different events for whoever reads the log, and a conflated
line cannot tell them apart.
EOF
```

---

## Task 7: an abandoned queue is reported

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:284-302`
- Test: `tests/test_chain_carries_its_plan.py`

`_chain_teardown` is the only teardown a SERVICE chain ever gets — `async_abort_opensprinkler_runs` filters on `RUN_MODE == opensprinkler` and has no service twin. Without this, a live service cycle loses its whole queue on shutdown in silence.

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestAnAbandonedQueueIsReported:
    async def test_teardown_names_the_zones_it_abandons(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3))
        c._live_run_zones = {1, 2, 3}
        await _dispatch(c, zones)
        caplog.clear()
        c._chain_teardown()
        assert any(
            "2" in r.getMessage() and "3" in r.getMessage()
            for r in caplog.records
        ), caplog.text
        # and it hands their allowances back on the way out
        assert c._live_run_zones == set()

    async def test_teardown_of_an_idle_chain_says_nothing(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        _register(c, _zone(1))
        caplog.clear()
        c._chain_teardown()
        assert caplog.records == []
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestAnAbandonedQueueIsReported -p _local_socket_unblock -q
```

Expected: `test_teardown_names_the_zones_it_abandons` fails on the `assert any(...)`. The second test passes already.

- [ ] **Step 3: Report and release in `_chain_teardown`**

Replace the body of `_chain_teardown`:

```python
        for mode, state in list(self._chains().items()):
            self._chain_cancel_absorption(mode)
            state.zones, state.trigger, state.token = [], None, None
            state.rotation = None
            state.planned = {}
```

with:

```python
        for mode, state in list(self._chains().items()):
            self._chain_cancel_absorption(mode)
            self._chain_forfeit_queue(mode, state, "the integration is unloading")
            state.zones, state.trigger, state.token = [], None, None
            state.rotation = None
            state.planned = {}
```

- [ ] **Step 4: Add the shared forfeit helper**

Insert immediately above `_chain_release`:

```python
    def _chain_forfeit_queue(self, mode, state: Chain, why: str) -> None:
        """Report the zones a cycle is abandoning and hand back what they hold.

        A service chain never reaches ``async_abort_opensprinkler_runs`` -- that
        path filters on the station mode and has no service twin -- so this is the
        only place a shutdown mid-cycle can account for the queue. Silent on an
        idle chain, because unload runs for every install whether a cycle was up
        or not.
        """
        waiting = [int(z) for z in state.zones]
        if state.rotation is not None:
            waiting += [
                int(zid)
                for zid, left in state.rotation.remaining.items()
                if left > 0 and int(zid) not in waiting
            ]
        if not waiting:
            return
        policy = chain_policy_for(mode)
        _LOGGER.info(
            "%s: abandoning %s still queued (%s) -- %s",
            policy.label if policy else mode,
            "zone" if len(waiting) == 1 else "zones",
            ", ".join(str(zid) for zid in waiting),
            why,
        )
        for zid in waiting:
            self._drop_live_run_marker(zid)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 18 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): account for the queue a teardown abandons

A service chain has no abort path of its own -- async_abort_opensprinkler_runs
filters on the station mode -- so an unload mid-cycle was the one way a whole
queue could disappear with nothing written anywhere. It now names the zones it
is giving up and hands their live-estimate allowances back, and stays silent
when no cycle was up, which is every ordinary unload.
EOF
```

---

## Task 8: the chain does not re-water a zone that watered while it waited (`Eifel-Joe#43`)

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:255-267` (`_chain_advance_for_run`)
- Test: `tests/test_chain_carries_its_plan.py`

The invariant this rests on: **the cycle pops its own zone at `run_chain.py:242` before dispatching it**, so a zone still in `state.zones` when a run of it finalises was watered by something else.

**Do not** fix this by advancing before removing the run record. `self_closing.py:470` and `:1004` state that the ordering is deliberate — it exists so the deferred calculation no longer sees a run.

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestAZoneWateredWhileQueuedIsNotWateredAgain:
    async def test_a_manual_run_on_a_queued_zone_takes_it_out_of_the_cycle(
        self, hass, caplog
    ):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        # Irrigate-now on a zone that is merely QUEUED: both guards ask
        # zone_run_in_flight, which cannot see a queued zone, so it is accepted.
        await c.async_run_self_closing(z2, trigger="manual")
        caplog.clear()
        await _finish(c, 2)
        await _finish(c, 1)
        # THE FIX: watered once by the manual run, not a second time by the chain.
        assert c._dispatched == [(1, 600.0), (2, 600.0)]
        assert any(
            "zone 2" in r.getMessage() and "already watered" in r.getMessage()
            for r in caplog.records
        ), caplog.text

    async def test_the_cycles_own_zone_still_advances_normally(self, hass):
        """The zone the chain dispatched is already popped, so nothing changes."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2, z3 = _register(
            c, _zone(1, duration=600), _zone(2, duration=600), _zone(3, duration=600)
        )
        await _dispatch(c, [z1, z2, z3])
        await _finish(c, 1)
        await _finish(c, 2)
        assert c._dispatched == [(1, 600.0), (2, 600.0), (3, 600.0)]

    async def test_a_rotating_cycle_is_untouched(self, hass):
        """A rotation keeps state.zones empty, so this cannot reach it."""
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        before = dict(c._chain_state(const.WATERING_MODE_SERVICE).rotation.remaining)
        await _finish(c, 1)
        after = c._chain_state(const.WATERING_MODE_SERVICE).rotation.remaining
        assert set(before) == set(after), "no zone was written off by the drop"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py::TestAZoneWateredWhileQueuedIsNotWateredAgain -p _local_socket_unblock -q
```

Expected: `test_a_manual_run_on_a_queued_zone_takes_it_out_of_the_cycle` fails on
`assert [(1, 600.0), (2, 600.0), (2, 600.0)] == [(1, 600.0), (2, 600.0)]`. The other two pass already; they are the regression guards.

- [ ] **Step 3: Drop a finished zone from the queue before advancing**

Replace the body of `_chain_advance_for_run`:

```python
        mode = (run or {}).get(const.RUN_MODE)
        if mode is None or mode not in self._chains():
            return
        await self._chain_advance(mode, zone_id)
```

with:

```python
        mode = (run or {}).get(const.RUN_MODE)
        if mode is None or mode not in self._chains():
            return
        self._chain_forget_finished(mode, zone_id)
        await self._chain_advance(mode, zone_id)
```

- [ ] **Step 4: Add the helper**

Insert immediately below `_chain_advance_for_run`:

```python
    def _chain_forget_finished(self, mode, zone_id) -> None:
        """Take a zone the chain still holds out of the queue once it has watered.

        A sequential cycle pops a zone BEFORE dispatching it, so a zone that is
        still queued when a run of it finalises was watered by something else --
        Irrigate-now, a service call, a run_zone. Neither that caller's guard nor
        this chain's could see it: both ask ``zone_run_in_flight``, and a merely
        queued zone answers False.

        Without this the chain pops it one finalisation later and waters it a
        second time, seconds after it stopped, crediting the bucket twice. The
        guard at the pop cannot catch it, because the finaliser removes the run
        record BEFORE advancing (``self_closing.py:387`` then ``:477``) and that
        record is precisely what ``zone_run_in_flight`` reads. That ordering is
        deliberate (``self_closing.py:470``) and is not what should change.

        A rotation keeps ``zones`` empty, so it is unaffected; a rotating zone's
        turns are governed by ``remaining`` and may legitimately recur.
        """
        try:
            zid = int(zone_id)
        except (TypeError, ValueError):
            return
        state = self._chain_state(mode)
        if zid not in state.zones:
            return
        policy = chain_policy_for(mode)
        _LOGGER.info(
            "%s: taking zone %s out of the cycle, it was already watered by "
            "another run while it waited",
            policy.label if policy else mode,
            zid,
        )
        state.zones = [z for z in state.zones if int(z) != zid]
        state.planned.pop(zid, None)
        self._drop_live_run_marker(zid)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q
```

Expected: 21 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_carries_its_plan.py
git commit -F - <<'EOF'
fix(chain): do not re-water a zone that watered while it was queued

A sequential chain pops a zone before dispatching it, so a zone still in the
queue when a run of it finalises was watered by something else -- Irrigate-now
or a service call, neither of which can see a queued zone, because both ask
zone_run_in_flight and a queued zone answers False.

The chain then popped it one finalisation later and watered it again seconds
after it stopped, crediting the bucket twice. Its own guard could not catch
this: the finaliser removes the run record before advancing, and that record is
what zone_run_in_flight reads. The ordering is deliberate, so the fix is at the
other end -- the zone leaves the queue when it finishes.

Closes the double-dispatch half that the queued zones were invisible to.
EOF
```

---

## Task 9: full verification

**Files:** none modified.

- [ ] **Step 1: Run the full suite**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no > /d/Entwicklung/HASI/issue2-work/after-full.txt 2>&1
tail -3 /d/Entwicklung/HASI/issue2-work/after-full.txt
```

Expected: `7 failed, 3212 passed, 9 skipped, ... 320 errors` — 21 more passes than the baseline's 3191, everything else identical.

- [ ] **Step 2: Prove the failure set is unchanged**

```bash
grep -E "^(FAILED|ERROR) " /d/Entwicklung/HASI/issue2-work/after-full.txt \
  | sed -E 's/ - .*//' | sort > /d/Entwicklung/HASI/issue2-work/after-names.txt
diff /d/Entwicklung/HASI/issue2-work/baseline-names.txt \
     /d/Entwicklung/HASI/issue2-work/after-names.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`. Any line here is a regression and must be resolved before proceeding.

- [ ] **Step 3: Lint**

```bash
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Expected: black reports the same unchanged file count as the baseline (68) and ruff is silent.

- [ ] **Step 4: Confirm the forbidden route was not taken**

```bash
grep -n "_claim_chain_zones" custom_components/irrigation_plus/run_chain.py || echo "NOT USED - correct"
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest \
  "tests/test_opensprinkler.py::test_sequential_holds_the_second_station_until_the_first_finishes" \
  -p _local_socket_unblock -q
```

Expected: `NOT USED - correct`, and the oracle test passes.

---

## Task 10: retire the throwaway repro

**Files:**
- Delete: `tests/test_zz_repro_issue2.py`

- [ ] **Step 1: Confirm every assertion it made is now covered**

The nine repro assertions map onto the new suite as follows. Check each is present in `tests/test_chain_carries_its_plan.py` before deleting:

| Repro assertion | Now pinned by |
| --- | --- |
| F1(a) zone 2 waters the stored duration | `test_a_queued_zone_waters_the_live_duration_not_the_stored_one` |
| F1(b) stored zero makes zone 2 vanish | `test_a_zone_dropped_for_a_zero_duration_releases_its_marker` + `test_a_zone_dropped_for_zero_duration_says_so` |
| F1(c) the marker leaks | `test_a_zone_dropped_for_a_mode_change_releases_its_marker` |
| F4 queued zone invisible to the guard | *unchanged behaviour, deliberately* — see the spec, residue R1 |
| F4 recalculation shortens the run | `test_the_stored_duration_no_longer_decides_a_planned_zone` |
| F4 recalculation to zero deletes the run | `test_the_stored_duration_no_longer_decides_a_planned_zone` |
| M1 zone 2 waters twice | `test_a_manual_run_on_a_queued_zone_takes_it_out_of_the_cycle` |
| F3 queue clobbered | **second PR** — not covered here on purpose |
| F3 one master hold carries two cycles | **second PR** — not covered here on purpose |

- [ ] **Step 2: Delete and commit**

```bash
git rm tests/test_zz_repro_issue2.py
git commit -m "test: retire the throwaway Eifel-Joe#2 repro, its assertions now live in the suite"
```

---

# Second PR — the append guard (F3)

**Do not start this until the first PR is open.** It is separate because it is the only change that alters *when* a valve opens, and the maintainer should be able to weigh that on its own.

Branch it from `upstream/master` again, not from the first branch, unless the first has already merged.

## Task 11: a second dispatch joins the queue instead of replacing it

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:158-200`
- Test: `tests/test_chain_append_on_second_dispatch.py` (create)

Two placement traps, both verified at the code:

1. The guard must sit **below** the `parallel` / single-zone returns at `run_chain.py:183-186`. Above them it would also catch `parallel` dispatches, which are correct today.
2. `self._chain_state(mode)` **creates** the `Chain` object (`run_chain.py:147-149`). Do not hoist that call above those returns: it would flip `mode not in self._chains()` at `run_chain.py:265`, and `_chain_advance_for_run` would start running for parallel-mode runs that today return early.

- [ ] **Step 1: Write the failing test**

Create `tests/test_chain_append_on_second_dispatch.py`:

```python
"""A second dispatch joins a live cycle rather than replacing it (Eifel-Joe#2, F3).

async_dispatch_chained_zones overwrote state.zones unconditionally, so a dispatch
arriving mid-cycle -- a second schedule, or the user pressing Irrigate-now, which
reaches the same code via _dispatch_by_mode -- destroyed the queue of the cycle
already running and opened a valve next to the one already open.
"""

from custom_components.irrigation_plus import const

from .test_service_chain import (
    ROTATING,
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)


class TestASecondDispatchJoinsTheQueue:
    async def test_the_first_cycles_zones_are_kept(self, hass):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3), _zone(4), _zone(5))
        await _dispatch(c, zones[:3])
        await _dispatch(c, zones[3:])
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        assert state.zones == [2, 3, 4, 5]

    async def test_no_second_valve_is_opened(self, hass):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3), _zone(4))
        await _dispatch(c, zones[:2])
        await _dispatch(c, zones[2:])
        assert c._dispatched == [(1, 300.0)] or c._dispatched == [(1, 600.0)]
        assert len(c._dispatched) == 1, c._dispatched

    async def test_a_zone_already_queued_is_not_queued_twice(self, hass):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3))
        await _dispatch(c, zones[:3])
        await _dispatch(c, [zones[1], zones[2]])
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == [2, 3]

    async def test_the_running_zone_is_not_queued_behind_itself(self, hass):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2))
        await _dispatch(c, zones)
        await _dispatch(c, [zones[0]])
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == [2]

    async def test_the_join_is_logged(self, hass, caplog):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3))
        await _dispatch(c, zones[:2])
        caplog.clear()
        await _dispatch(c, zones[2:])
        assert any("joining" in r.getMessage() for r in caplog.records), caplog.text

    async def test_a_rotating_dispatch_onto_a_sequential_queue_is_refused(
        self, hass, caplog
    ):
        """The two geometries are exclusive; merging them is not defined."""
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3))
        await _dispatch(c, zones[:2])
        c.store.config.zone_sequencing = ROTATING
        caplog.clear()
        await _dispatch(c, zones[2:])
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        assert state.rotation is None, "the live sequential cycle is intact"
        assert state.zones == [2]
        assert any("sequencing changed" in r.getMessage() for r in caplog.records)

    async def test_a_parallel_dispatch_is_not_affected(self, hass):
        """The guard must sit below the parallel return, not above it."""
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3), _zone(4))
        await _dispatch(c, zones[:2])
        c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
        await _dispatch(c, zones[2:])
        assert (3, 600.0) in c._dispatched and (4, 600.0) in c._dispatched

    async def test_a_finished_cycle_starts_a_fresh_one(self, hass):
        c = _coord(hass, SEQUENTIAL)
        zones = _register(c, _zone(1), _zone(2), _zone(3), _zone(4))
        await _dispatch(c, zones[:2])
        await _finish(c, 1)
        await _finish(c, 2)
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == []
        await _dispatch(c, zones[2:])
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == [4]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_append_on_second_dispatch.py -p _local_socket_unblock -q
```

Expected: 6 failed, 2 passed. `test_a_parallel_dispatch_is_not_affected` and `test_a_finished_cycle_starts_a_fresh_one` pass already and are the guards against the two placement traps.

- [ ] **Step 3: Add the liveness test and the join**

In `async_dispatch_chained_zones`, replace the block from `state = self._chain_state(mode)` down to the `_LOGGER.info` call. Current:

```python
        state = self._chain_state(mode)
        live_now = getattr(self, "_live_run_zones", None) or set()
        state.zones = [int(z.get(const.ZONE_ID)) for z in zones[1:]]
        state.planned = {
            int(z.get(const.ZONE_ID)): ZonePlan(
                seconds=float(z.get(const.ZONE_DURATION) or 0),
                live=int(z.get(const.ZONE_ID)) in live_now,
            )
            for z in zones[1:]
        }
        state.trigger = trigger
        await self._chain_take_hold(state, policy)
        _LOGGER.info(
            "%s: dispatching zone %s, %s more chained behind it",
            policy.label,
            zones[0].get(const.ZONE_ID),
            len(state.zones),
        )
        if not await self.async_run_self_closing(zones[0], trigger=trigger):
            # Refused; the chain must not stall on it.
            await self._chain_advance(mode)
```

becomes:

```python
        state = self._chain_state(mode)
        live_now = getattr(self, "_live_run_zones", None) or set()

        def _plan(zone):
            return ZonePlan(
                seconds=float(zone.get(const.ZONE_DURATION) or 0),
                live=int(zone.get(const.ZONE_ID)) in live_now,
            )

        if self._chain_is_live(state):
            if state.rotation is not None:
                # Two geometries, no defined merge: the rotation prices slots from
                # a total it captured at its own start, and a sequential queue has
                # no slots at all. Leave the live cycle alone and say so.
                _LOGGER.warning(
                    "%s: a rotating cycle is still running and zone_sequencing "
                    "changed under it; not starting %s zone(s) now",
                    policy.label,
                    len(zones),
                )
                return
            queued = self._chain_join(state, zones, _plan)
            _LOGGER.info(
                "%s: a cycle is already running, joining %s zone(s) onto the back "
                "of its queue (%s waiting now)",
                policy.label,
                queued,
                len(state.zones),
            )
            return

        state.zones = [int(z.get(const.ZONE_ID)) for z in zones[1:]]
        state.planned = {int(z.get(const.ZONE_ID)): _plan(z) for z in zones[1:]}
        state.trigger = trigger
        await self._chain_take_hold(state, policy)
        _LOGGER.info(
            "%s: dispatching zone %s, %s more chained behind it",
            policy.label,
            zones[0].get(const.ZONE_ID),
            len(state.zones),
        )
        if not await self.async_run_self_closing(zones[0], trigger=trigger):
            # Refused; the chain must not stall on it.
            await self._chain_advance(mode)
```

- [ ] **Step 4: Add the two helpers**

Insert immediately above `_chain_take_hold`:

```python
    def _chain_is_live(self, state: Chain) -> bool:
        """Is a cycle of this mode still running?

        The token is part of the test rather than the queue alone: the last zone
        of a cycle is dispatched with an empty queue, and a dispatch landing in
        that window has to join rather than start a second cycle under the first
        one's master hold.
        """
        return bool(state.zones) or state.rotation is not None or state.token is not None

    def _chain_join(self, state: Chain, zones: list, plan_for) -> int:
        """Append zones to a live queue, skipping the ones already accounted for.

        Returns how many were actually added. A zone already queued keeps the plan
        it was queued with: the running cycle decided it first, and re-pricing a
        waiting zone from a later dispatch is a separate question (see the spec's
        non-goals). A zone whose valve is open right now is not queued behind
        itself.
        """
        added = 0
        for zone in zones:
            zid = int(zone.get(const.ZONE_ID))
            if zid in state.zones or self.zone_run_in_flight(zid):
                continue
            state.zones.append(zid)
            state.planned[zid] = plan_for(zone)
            added += 1
        return added
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_append_on_second_dispatch.py -p _local_socket_unblock -q
```

Expected: 8 passed.

- [ ] **Step 6: Run everything**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no | tail -3
```

Expected: `7 failed, 3220 passed, 9 skipped, ... 320 errors`, and the `diff` against `baseline-names.txt` is still empty.

- [ ] **Step 7: Commit**

```bash
git add custom_components/irrigation_plus/run_chain.py tests/test_chain_append_on_second_dispatch.py
git commit -F - <<'EOF'
fix(chain): a second dispatch joins the running cycle instead of replacing it

async_dispatch_chained_zones overwrote state.zones unconditionally. A dispatch
arriving mid-cycle -- a second schedule, or Irrigate-now, which reaches this
same code through _dispatch_by_mode -- therefore destroyed the queue of the
cycle already running and opened a valve next to the one already open, under a
sequencing setting whose whole promise is that it will not. The lost zones were
never mentioned anywhere.

New zones now join the back of the live queue, duplicates and the zone actually
watering are skipped, and the join is logged. A rotating dispatch arriving on a
live sequential cycle (the user changed zone_sequencing mid-cycle) has no
defined merge, so the live cycle is left alone and the refusal is warned about.
EOF
```

---

## Notes for whoever writes the PR bodies

**PR 1** must state what it does *not* close, because a reviewer will look for it:

- A calculation landing mid-chain is still not deferred: `calculation.py:504-505` gates on `zone_run_in_flight` (`run_state.py:132-142`), which has no knowledge of `state.zones`. After Task 1 this costs no water — the run delivers what the cycle planned — only a discarded recalculation.
- Queued self-closing zones stay invisible to the panel: `run_chain.py` never calls `_register_active_run`, so `get_active_runs` cannot see them.
- The chain is now deliberately deaf to rain falling mid-cycle. Today's store re-read did this by accident and in both directions; re-pricing a queued zone properly means porting `_resize_queued_zone` (`irrigation.py:3165`), which is a feature and gets its own issue.
- `ZONE_STATE_DISABLED` is not re-checked mid-cycle, before or after.

**Follow-up issues to open** (spec §6): the `_resize_queued_zone` port; run-log rows for dropped zones with their eight language files; `async_stop_zone` on a merely-queued zone confirming nothing; the dispatch-in-flight window (`self_closing.py:580`–`~626`).

**A free fix in passing:** `irrigation.py:206` refers to `_reprice_before_turn`, which exists nowhere in the package. The function is `_resize_queued_zone` at `irrigation.py:3165`.
