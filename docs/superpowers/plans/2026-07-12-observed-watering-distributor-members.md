# Observed Watering — Phase 2 (Distributor Member Zones) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An external inlet open→close through a mechanical distributor credits the current member zone's bucket (timed fallback) and writes an `observed` run-history entry, while short advance pulses are not credited and SI's own cycles are never double-credited.

**Architecture:** Reuse the existing inlet-state watch. The `off→on` edge (unchanged) already advances the ring; we additionally stash `{t, outlet}` for a foreign `count`-mode open. A new `on→off` decode calls `_dist_on_inlet_close`, which credits the stashed member iff the open lasted `≥ 2 × skip_pulse_seconds`. Crediting reuses `_dist_credit_zone` (extended with `result`/`trigger` kwargs) so the member gets the same teal `observed` run-log chip as Phase 1.

**Tech Stack:** Python 3.12, Home Assistant custom integration, pytest / pytest-asyncio. Backend-only — no frontend, no dist rebuild.

**Canonical test command (repo root `D:\Entwicklung\HASI\HAsmartirrigation`):**
```bash
./.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```
Format: `uvx black <files>` and `uvx ruff check <files>` (ephemeral).

**Branch:** `local/observed-distributor-members` (already created off `production`; spec already committed).

---

### Task 1: `RUN_TRIGGER_OBSERVED` const + adopt in the Phase-1 observer

**Files:**
- Modify: `custom_components/smart_irrigation/const.py:648`
- Modify: `custom_components/smart_irrigation/observed_watering.py:181`
- Test: `tests/test_observed_distributor_members.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_observed_distributor_members.py`:

```python
"""Observed watering Phase 2: crediting distributor member zones on an external
inlet open->close. Backend-only; hosts are built like the other distributor unit
tests (mixin composite + Mock hass/store)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.distributor import DistributorMixin
from custom_components.smart_irrigation.irrigation import IrrigationRunnerMixin
from custom_components.smart_irrigation.master import MasterMixin
from custom_components.smart_irrigation.skip_conditions import SkipConditionsMixin


class _Host(DistributorMixin, MasterMixin, SkipConditionsMixin, IrrigationRunnerMixin):
    """Minimal host to unit-test the distributor mixin in isolation."""


def _host(observed=True):
    c = _Host()
    c.hass = Mock()
    c.hass.data = {}
    c.store = Mock()
    c.store.async_update_distributor = AsyncMock()
    c.store.config = SimpleNamespace(observed_watering_enabled=observed)
    return c


def test_run_trigger_observed_const():
    assert const.RUN_TRIGGER_OBSERVED == "observed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py::test_run_trigger_observed_const -p _local_socket_unblock`
Expected: FAIL with `AttributeError: module ... has no attribute 'RUN_TRIGGER_OBSERVED'`

- [ ] **Step 3: Add the const**

In `const.py`, after line 648 (`RUN_TRIGGER_DISTRIBUTOR = "distributor"`):

```python
# Run-log trigger tag for distributor-delivered watering.
RUN_TRIGGER_DISTRIBUTOR = "distributor"
# Run-log trigger tag for observed (externally run) watering (opt-in): the valve
# ran outside Smart Irrigation and its estimated volume was credited.
RUN_TRIGGER_OBSERVED = "observed"
```

- [ ] **Step 4: Adopt the const in the observer (DRY)**

In `observed_watering.py`, in `_credit_observed_watering`'s `_record_run` call (~line 181), replace the string literal:

```python
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_OBSERVED,
            volume_l=volume_l,
            actual_s=round(seconds),
            trigger=const.RUN_TRIGGER_OBSERVED,
            add_to_total=True,
        )
```

- [ ] **Step 5: Run tests to verify green (new const + Phase-1 observer regression)**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py tests/test_observed_watering.py tests/test_experimental_features.py -p _local_socket_unblock`
Expected: PASS (trigger value is unchanged `"observed"`, so the Phase-1 run-log test stays green).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/observed_watering.py tests/test_observed_distributor_members.py
git commit -m "feat(observed): add RUN_TRIGGER_OBSERVED const, adopt in observer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `_dist_credit_zone` gains `result`/`trigger` keyword params

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:735-778`
- Test: `tests/test_observed_distributor_members.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_distributor_members.py`:

```python
def _credit_host():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._timed_volume_l = Mock(return_value=12.0)
    c._credited_depth_native = Mock(return_value=3.0)
    return c


async def test_credit_zone_defaults_completed_distributor():
    c = _credit_host()
    zone = {const.ZONE_ID: 5, const.ZONE_BUCKET: 0.0}
    await c._dist_credit_zone(zone, 300)
    kwargs = c._record_run.await_args.kwargs
    assert kwargs["result"] == const.RUN_RESULT_COMPLETED
    assert kwargs["trigger"] == const.RUN_TRIGGER_DISTRIBUTOR


async def test_credit_zone_observed_result_trigger():
    c = _credit_host()
    zone = {const.ZONE_ID: 5, const.ZONE_BUCKET: 0.0}
    await c._dist_credit_zone(
        zone, 300, result=const.RUN_RESULT_OBSERVED, trigger=const.RUN_TRIGGER_OBSERVED
    )
    kwargs = c._record_run.await_args.kwargs
    assert kwargs["result"] == const.RUN_RESULT_OBSERVED
    assert kwargs["trigger"] == const.RUN_TRIGGER_OBSERVED
    assert kwargs["add_to_total"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k credit_zone -p _local_socket_unblock`
Expected: FAIL — `test_credit_zone_observed_result_trigger` raises `TypeError: _dist_credit_zone() got an unexpected keyword argument 'result'`.

- [ ] **Step 3: Add the keyword params**

In `distributor.py`, change the `_dist_credit_zone` signature (line 735-741) to:

```python
    async def _dist_credit_zone(
        self,
        zone: dict,
        seconds: float,
        measured_l: float | None = None,
        planned_seconds: float | None = None,
        *,
        result: str = const.RUN_RESULT_COMPLETED,
        trigger: str = const.RUN_TRIGGER_DISTRIBUTOR,
    ) -> None:
```

And in its `_record_run` call (line 770-778), replace the two hard-coded values:

```python
        await self._record_run(
            zone_id,
            result=result,
            volume_l=volume_l,
            planned_s=planned_seconds if planned_seconds is not None else seconds,
            actual_s=seconds,
            trigger=trigger,
            add_to_total=True,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k credit_zone -p _local_socket_unblock`
Expected: PASS (both).

- [ ] **Step 5: Regression — existing distributor credit callers unaffected**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_cycle.py tests/test_metered_run.py -p _local_socket_unblock`
Expected: PASS (defaults reproduce today's behaviour).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_observed_distributor_members.py
git commit -m "refactor(distributor): _dist_credit_zone result/trigger kwargs

Defaults reproduce today's completed/distributor behaviour; the observed
member path passes result=observed/trigger=observed.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Open-edge stash of the foreign inlet open (`_dist_on_inlet_pulse`)

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:634-664` (add lazy map helper + stash in the `count` branch)
- Test: `tests/test_observed_distributor_members.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_distributor_members.py`:

```python
def _member(zid, outlet, state=const.ZONE_STATE_AUTOMATIC):
    return {
        const.ZONE_ID: zid,
        "distributor_id": 0,
        "outlet_number": outlet,
        const.ZONE_STATE: state,
    }


def _dist(**kw):
    d = {
        "id": 0,
        "watch_mode": const.DISTRIBUTOR_WATCH_MODE_COUNT,
        "inlet_entity": "switch.inlet",
        "skip_pulse_seconds": 30,
        "current_outlet": 2,
        "active_cycle": {},
    }
    d.update(kw)
    return d


def _pulse_host(dist, members, observed=True, open_time=100.0):
    c = _host(observed=observed)
    c.store.get_distributor = Mock(return_value=dist)
    c.store.async_get_zones = AsyncMock(return_value=members)
    c.hass.loop.time = Mock(return_value=open_time)
    return c


async def test_open_edge_stashes_preadvance_outlet_and_advances():
    dist = _dist(current_outlet=2)
    members = [_member(1, 1), _member(2, 2), _member(3, 3)]
    c = _pulse_host(dist, members, open_time=100.0)
    await c._dist_on_inlet_pulse(0)
    # Stash captured the PRE-advance ring index + open time.
    assert c._dist_observed_open_map()[0] == {"t": 100.0, "outlet": 2}
    # And the position still advanced exactly as before (2 -> 3 of 3 members).
    c.store.async_update_distributor.assert_awaited_once_with(0, {"current_outlet": 3})


async def test_open_edge_no_stash_when_observed_off():
    dist = _dist(current_outlet=2)
    members = [_member(1, 1), _member(2, 2), _member(3, 3)]
    c = _pulse_host(dist, members, observed=False)
    await c._dist_on_inlet_pulse(0)
    assert 0 not in c._dist_observed_open_map()
    c.store.async_update_distributor.assert_awaited_once()  # still advances


async def test_open_edge_no_stash_in_warn_mode():
    dist = _dist(watch_mode=const.DISTRIBUTOR_WATCH_MODE_WARN)
    members = [_member(1, 1), _member(2, 2)]
    c = _pulse_host(dist, members)
    c._dist_mark_uncertain = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    assert 0 not in c._dist_observed_open_map()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k open_edge -p _local_socket_unblock`
Expected: FAIL — `AttributeError: '_Host' object has no attribute '_dist_observed_open_map'`.

- [ ] **Step 3: Add the lazy map helper**

In `distributor.py`, immediately before `_dist_on_inlet_pulse` (before line 634), add:

```python
    def _dist_observed_open_map(self) -> dict:
        """Per-distributor record of an in-progress FOREIGN inlet open, for observed
        member crediting (Phase 2). Lazily created so no coordinator __init__ change
        is needed. Maps distributor_id -> {"t": open_time, "outlet": ring index
        (1-based) BEFORE the open-edge advance = the outlet flowing during the open}."""
        m = getattr(self, "_dist_observed_open", None)
        if m is None:
            m = self._dist_observed_open = {}
        return m

```

- [ ] **Step 4: Stash in the `count` branch**

In `_dist_on_inlet_pulse`, replace the tail (line 663-664):

```python
        cur = int(dist.get("current_outlet") or 1)
        await self._dist_store_update(distributor_id, {"current_outlet": (cur % n) + 1})
```

with:

```python
        cur = int(dist.get("current_outlet") or 1)
        # Phase 2 (observed watering): remember which outlet is flowing NOW (the
        # pre-advance ring index) and when this foreign open started, so the close
        # edge can credit this member if the open lasts long enough to be real
        # watering rather than a short advance pulse. Gated on the opt-in so count
        # users who don't use observed watering never grow the map.
        if getattr(self.store.config, "observed_watering_enabled", False):
            self._dist_observed_open_map()[distributor_id] = {
                "t": self.hass.loop.time(),
                "outlet": cur,
            }
        await self._dist_store_update(distributor_id, {"current_outlet": (cur % n) + 1})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k open_edge -p _local_socket_unblock`
Expected: PASS (all three).

- [ ] **Step 6: Regression — existing inlet-pulse behaviour unchanged**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_integration.py -p _local_socket_unblock`
Expected: PASS (existing count-mode tests don't set `observed_watering_enabled`, so no stash; the advance is identical).

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_observed_distributor_members.py
git commit -m "feat(distributor): stash foreign inlet open for observed member credit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `_dist_on_inlet_close` — credit or discard

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (add async method after `_dist_on_inlet_pulse`, ~line 665)
- Test: `tests/test_observed_distributor_members.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_distributor_members.py`:

```python
def _close_host(dist, members, observed=True, close_time=None, stash_outlet=2, stash_t=100.0):
    c = _host(observed=observed)
    c.store.get_distributor = Mock(return_value=dist)
    c.store.async_get_zones = AsyncMock(return_value=members)
    c._dist_credit_zone = AsyncMock()
    if close_time is not None:
        c.hass.loop.time = Mock(return_value=close_time)
    if stash_outlet is not None:
        c._dist_observed_open_map()[0] = {"t": stash_t, "outlet": stash_outlet}
    return c


async def test_close_credits_current_member_when_long():
    dist = _dist(skip_pulse_seconds=30)  # threshold = 60 s
    members = [_member(1, 1), _member(2, 2), _member(3, 3)]
    c = _close_host(dist, members, close_time=100.0 + 300, stash_outlet=2)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_awaited_once()
    zone_arg, seconds_arg = c._dist_credit_zone.await_args.args
    assert zone_arg[const.ZONE_ID] == 2  # ring index 2 -> members[1] -> zone id 2
    assert seconds_arg == 300
    kwargs = c._dist_credit_zone.await_args.kwargs
    assert kwargs["result"] == const.RUN_RESULT_OBSERVED
    assert kwargs["trigger"] == const.RUN_TRIGGER_OBSERVED
    assert 0 not in c._dist_observed_open_map()  # stash consumed


async def test_close_ignores_short_advance_pulse():
    dist = _dist(skip_pulse_seconds=30)  # threshold = 60 s
    members = [_member(1, 1), _member(2, 2)]
    c = _close_host(dist, members, close_time=100.0 + 45, stash_outlet=1)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_not_awaited()


async def test_close_race_guard_active_cycle():
    dist = _dist(active_cycle={"outlet": 2, "phase": "watering"})
    members = [_member(1, 1), _member(2, 2)]
    c = _close_host(dist, members, close_time=100.0 + 300, stash_outlet=1)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_not_awaited()


async def test_close_noop_when_observed_disabled():
    dist = _dist()
    members = [_member(1, 1), _member(2, 2)]
    c = _close_host(dist, members, observed=False, close_time=100.0 + 300, stash_outlet=1)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_not_awaited()


async def test_close_noop_without_stash():
    dist = _dist()
    members = [_member(1, 1), _member(2, 2)]
    c = _close_host(dist, members, close_time=100.0 + 300, stash_outlet=None)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_not_awaited()


async def test_close_skips_disabled_member():
    dist = _dist(skip_pulse_seconds=30)
    members = [
        _member(1, 1),
        _member(2, 2, state=const.ZONE_STATE_DISABLED),
        _member(3, 3),
    ]
    c = _close_host(dist, members, close_time=100.0 + 300, stash_outlet=2)
    await c._dist_on_inlet_close(0)
    c._dist_credit_zone.assert_not_awaited()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k close -p _local_socket_unblock`
Expected: FAIL — `AttributeError: '_Host' object has no attribute '_dist_on_inlet_close'`.

- [ ] **Step 3: Implement `_dist_on_inlet_close`**

In `distributor.py`, add immediately after `_dist_on_inlet_pulse` (after line 664, before `_dist_inlet_state_handler`):

```python
    async def _dist_on_inlet_close(self, distributor_id) -> None:
        """A foreign inlet on->off edge closed. If observed watering is enabled and
        the open lasted long enough to be real watering (>= 2 * skip_pulse_seconds),
        credit the member zone that was flowing during the open (the pre-advance ring
        index stashed on the open edge) and write an `observed` run-log entry. Short
        opens are advance pulses -> not credited (the ring already advanced on open).

        Only foreign, count-mode opens ever leave a stash (see _dist_on_inlet_pulse),
        so warn/ignore modes and SI's own cycles no-op here. A race guard additionally
        drops the credit if an SI cycle claimed the inlet between open and close."""
        open_rec = self._dist_observed_open_map().pop(distributor_id, None)
        if open_rec is None:
            return
        dist = self.store.get_distributor(distributor_id)
        if dist is None or dist.get("active_cycle"):
            # An SI cycle claimed the inlet between open and close -> not foreign.
            return
        if not getattr(self.store.config, "observed_watering_enabled", False):
            return
        duration = self.hass.loop.time() - float(open_rec.get("t") or 0)
        skip_pulse = max(
            int(dist.get("skip_pulse_seconds") or 30),
            const.DISTRIBUTOR_MIN_SKIP_PULSE_SECONDS,
        )
        if duration < 2 * skip_pulse:
            return  # short advance pulse, not watering
        members = await self._dist_members(distributor_id)
        n = len(members)
        if n == 0:
            return
        outlet = int(open_rec.get("outlet") or 1)
        member = members[(outlet - 1) % n]
        if member.get(const.ZONE_STATE) == const.ZONE_STATE_DISABLED:
            return
        await self._dist_credit_zone(
            member,
            duration,
            result=const.RUN_RESULT_OBSERVED,
            trigger=const.RUN_TRIGGER_OBSERVED,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k close -p _local_socket_unblock`
Expected: PASS (all six).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_observed_distributor_members.py
git commit -m "feat(distributor): credit member zone on external inlet close (observed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Decode the inlet close edge in the state handler

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:666-681` (`_dist_inlet_state_handler`)
- Test: `tests/test_observed_distributor_members.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_distributor_members.py`:

```python
def _evt(old, new):
    return SimpleNamespace(
        data={
            "old_state": SimpleNamespace(state=old),
            "new_state": SimpleNamespace(state=new),
        }
    )


def _handler_host():
    c = _host()
    c.hass.async_create_task = Mock()
    return c


def test_handler_open_edge_calls_pulse():
    c = _handler_host()
    c._dist_on_inlet_pulse = Mock(return_value="pulse_coro")
    c._dist_on_inlet_close = Mock(return_value="close_coro")
    handler = c._dist_inlet_state_handler(0)
    handler(_evt("off", "on"))
    c.hass.async_create_task.assert_called_once_with("pulse_coro")


def test_handler_close_edge_calls_close():
    c = _handler_host()
    c._dist_on_inlet_pulse = Mock(return_value="pulse_coro")
    c._dist_on_inlet_close = Mock(return_value="close_coro")
    handler = c._dist_inlet_state_handler(0)
    handler(_evt("on", "off"))
    c.hass.async_create_task.assert_called_once_with("close_coro")


def test_handler_ignores_unrelated_transition():
    c = _handler_host()
    handler = c._dist_inlet_state_handler(0)
    handler(_evt("on", "on"))
    c.hass.async_create_task.assert_not_called()
```

> Note: `_dist_on_inlet_pulse`/`_dist_on_inlet_close` are replaced with plain `Mock`s here so the handler test asserts the scheduling decision only, without running the coroutines (which would warn "coroutine never awaited"). Returning a sentinel string is what `async_create_task` receives.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k handler -p _local_socket_unblock`
Expected: FAIL — `test_handler_close_edge_calls_close` fails (`async_create_task` not called; current handler only decodes off→on).

- [ ] **Step 3: Add the close-edge decode**

In `distributor.py`, replace the `_handler` body inside `_dist_inlet_state_handler` (line 672-679):

```python
        @callback
        def _handler(event):
            old = event.data.get("old_state")
            new = event.data.get("new_state")
            if old is None or new is None:
                return
            if old.state in off_states and new.state in on_states:
                self.hass.async_create_task(self._dist_on_inlet_pulse(distributor_id))
            elif old.state in on_states and new.state in off_states:
                self.hass.async_create_task(self._dist_on_inlet_close(distributor_id))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_distributor_members.py -k handler -p _local_socket_unblock`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_observed_distributor_members.py
git commit -m "feat(distributor): decode inlet close edge to trigger observed credit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full regression, format, REGEL-8 sister-path review

**Files:**
- Review: `custom_components/smart_irrigation/distributor.py`, `observed_watering.py`, `const.py`
- Test: full suite

- [ ] **Step 1: Format**

Run: `uvx black custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/const.py custom_components/smart_irrigation/observed_watering.py tests/test_observed_distributor_members.py`
Then: `uvx ruff check custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/const.py custom_components/smart_irrigation/observed_watering.py tests/test_observed_distributor_members.py`
Expected: black reports "unchanged" or reformats; ruff clean (no errors).

- [ ] **Step 2: Full suite green**

Run: `./.venv/Scripts/python.exe -m pytest -p _local_socket_unblock`
Expected: all pass (teardown `_ssock`/`__del__` AttributeErrors on Windows are harmless — `exit 0` + "N passed" is authoritative).

- [ ] **Step 3: REGEL-8 sister-path review**

Read the complete `_dist_on_inlet_pulse` / `_dist_on_inlet_close` / `_dist_inlet_state_handler` trio and confirm:
- Every foreign-open path that stashes has a matching close path that pops (no leak). Warn/ignore never stash; `_dist_on_inlet_close` pops-and-discards defensively if a stash somehow exists in a non-count state (the `active_cycle`/observed/threshold gates all short-circuit safely).
- The `active_cycle` gate on open AND the close-edge race guard both exclude SI cycles — verify no fourth branch of the handler can credit during an SI cycle.
- `_dist_credit_zone`'s new kwargs default to today's values — grep all call sites: `grep -n "_dist_credit_zone(" custom_components/smart_irrigation/distributor.py` and confirm the pre-existing callers pass no `result`/`trigger` (unchanged behaviour).

Record findings in the commit message if any adjustment is needed; otherwise proceed.

- [ ] **Step 4: Commit any format/review fixups**

```bash
git add -A
git commit -m "style: black/ruff for observed distributor-member credit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(Skip if nothing changed after Step 1-3.)

- [ ] **Step 5: Commit the plan doc**

```bash
git add docs/superpowers/plans/2026-07-12-observed-watering-distributor-members.md
git commit -m "docs: implementation plan for observed distributor member zones

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## After all tasks

- Code review (superpowers:requesting-code-review / code-reviewer subagent) over the full diff.
- **Delivery (own step, user-gated):** cherry-pick the source commits onto `production` + version bump **v2026.07.16** (no dist rebuild — backend only). Release notes shown for approval before `gh` release (REGEL 5). Design/plan docs → `archive/observed-distributor-members-design-history`.
- **Upstream PR:** not now. Bundle all observed-watering work (service-zones + run-log + this member phase) into ONE clean branch off `upstream/master` when opened.

## Self-Review (author checklist — completed)

- **Spec coverage:** const+observer (Task 1) ✓; `_dist_credit_zone` params (Task 2) ✓; open-edge stash pre-advance outlet (Task 3) ✓; close-edge credit/discard with race guard + threshold + disabled-member guard (Task 4) ✓; two-edge decode (Task 5) ✓; regression/format/sister-path (Task 6) ✓. Threshold `2 × skip_pulse_seconds`, timed fallback, add_to_total, no frontend — all covered.
- **Placeholder scan:** none.
- **Type consistency:** `_dist_credit_zone(zone, seconds, ..., *, result, trigger)`; stash shape `{"t", "outlet"}` written in Task 3, read identically in Task 4; `_dist_observed_open_map()` defined Task 3, used Tasks 3-4; member lookup `members[(outlet - 1) % n]` matches the sweep convention.
