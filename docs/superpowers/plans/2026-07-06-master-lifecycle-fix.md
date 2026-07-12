# Master-Lifecycle-Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two master-lifecycle bugs on the Gardena distributor in one cycle — the ~80 s pump dead-head after every real sweep (Bug 1) and the orphaned pump after a mid-cycle restart (Bug 2).

**Architecture:** Bug 1 decouples the terminal master shut-off decision from the static `parallel` flag, keying it instead on a master-off-deadline snapshot taken before the sweep (a real concurrent consumer). Bug 2 adds a one-shot, config-gated boot normalization that powers off an orphaned master when nothing HASI-driven is still running.

**Tech Stack:** Python 3.12 (local test env), Home Assistant custom integration, pytest (`asyncio_mode=auto`), mixin-composed coordinator.

**Spec:** `docs/superpowers/specs/2026-07-06-master-lifecycle-fix-design.md`

---

## Test environment (canonical local command)

The HA test stack only builds on Python 3.12 locally (Windows). Reuse the existing uv/3.12 env + socket-unblock plugin. From `D:\Entwicklung\HASI\HAsmartirrigation`:

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```

Baseline (2026-07-06): the full suite collects 745 items; the four master-end/H7 tests pass.

---

## File structure

- **Modify** `custom_components/smart_irrigation/distributor.py` — `_dist_master_end` (signature `concurrent` → `pre_deadline` + new terminal logic); `_dist_run_sweep` (snapshot `pre_deadline`, pass it to both `_dist_master_end` call sites).
- **Modify** `custom_components/smart_irrigation/master.py` — add `async_reconcile_master_after_restart`.
- **Modify** `custom_components/smart_irrigation/__init__.py` — call the new method after the two resume steps.
- **Modify** `tests/test_distributor.py` — add `import datetime`; 2 new `_dist_master_end` unit tests; update 1 existing.
- **Modify** `tests/test_distributor_dispatch.py` — update 1 existing; add 1 end-to-end Bug-1 test.
- **Modify** `tests/test_master.py` — add 5 Bug-2 reconciliation unit tests.

---

## Task 1: Bug 1 — terminal master collapse keyed on a pre-sweep snapshot

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:219-240` (`_dist_master_end`), `:722` (snapshot), `:799` + `:860` (call sites)
- Test: `tests/test_distributor_dispatch.py` (end-to-end), `tests/test_distributor.py` (unit)

- [ ] **Step 1: Write the failing end-to-end test**

Add to `tests/test_distributor_dispatch.py` (after `test_concurrent_long_window_extends_deadline`; `_host`, `_dist`, `_cycle_mocks`, `datetime`, `const` are already in scope):

```python
async def test_solo_run_under_parallel_collapses_master_at_last_valve_close():
    # Bug 1 end-to-end (2026-07-06): a solo real cycle under zone_sequencing=parallel
    # with NO pre-existing external deadline must power the master OFF synchronously at
    # the last valve close (deadline -> None), NOT ride the sweep's rolling
    # over-estimate for ~80 s. Reproduces the live dead-head; the H7 tests miss it
    # because they only assert the rolling notes, not the terminal collapse.
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    c._master_off_deadline = None
    c._master_on = True
    _cycle_mocks(c)
    # stub the HA-timer arming (Mock hass has no real loop for async_call_later); the
    # real rolling _master_note_run still runs, and the terminal solo branch is what we
    # assert.
    c.async_master_schedule_off = AsyncMock()
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {
                "id": 7,
                "distributor_id": 0,
                "outlet_number": 1,
                "duration": 60,
                "bucket": -1,
                "bucket_threshold": 0,
                "state": "automatic",
            },
        ]
    )
    c._dist_needs_water = Mock(return_value=True)
    await c.async_run_distributor_cycle(
        _dist(id=0, current_outlet=1),
        concurrent=c._distributor_concurrent(),  # True under parallel — the old trap
    )
    # solo collapse: master physically powered off + deadline cleared
    c.hass.services.async_call.assert_any_await(
        "homeassistant", "turn_off", {"entity_id": "input_boolean.pump"}
    )
    assert c._master_off_deadline is None
```

- [ ] **Step 2: Run it to verify it fails**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_solo_run_under_parallel_collapses_master_at_last_valve_close" -q
```
Expected: FAIL — on current code the run takes the concurrent defer path, so no `input_boolean.pump` `turn_off` is awaited and `_master_off_deadline` is a future datetime, not `None`.

- [ ] **Step 3: Implement — snapshot in `_dist_run_sweep`**

In `custom_components/smart_irrigation/distributor.py`, replace the single line `await self._dist_master_start(distributor)` (currently `:722`) with:

```python
        # Bug 1 (2026-07-06): snapshot the master-off deadline that pre-existed this
        # sweep. A genuine concurrent consumer (a parallel normal-zone run) sets it
        # BEFORE _dispatch_distributor_cycles runs (scheduler.py:782-787 /
        # irrigation.py:1468-1490 note the normal zones first). The terminal
        # _dist_master_end keys its synchronous-vs-defer decision on THIS snapshot, not
        # on the static parallel flag, so a solo run collapses the master at the last
        # valve close instead of dead-heading ~80 s on the inflated rolling deadline.
        pre_deadline = getattr(self, "_master_off_deadline", None)
        await self._dist_master_start(distributor)
```

- [ ] **Step 4: Implement — rewrite `_dist_master_end`**

Replace the whole `_dist_master_end` method (currently `:219-240`) with:

```python
    async def _dist_master_end(
        self, distributor: dict, *, pre_deadline=None
    ) -> None:
        """End of cycle. Decide synchronous shutdown vs. deferral by whether a REAL
        external master-off deadline pre-existed this sweep (a concurrent normal-zone
        run), NOT by the static parallel flag.

        Iter (2026-07-06, Bug 1 — master over-run ~80 s): the old `concurrent` branch
        keyed the terminal collapse on `_distributor_concurrent()` == parallel, which is
        True on EVERY real run under the default sequencing. That always took the defer
        path (`_master_note_run(0)` + `async_master_schedule_off()`), and since
        `_master_note_run` only EXTENDS (max, master.py), the terminal `note(0)` could
        never collapse the sweep's rolling over-estimate deadline (window+pause+settle+
        buffer+confirm, noted at each window START) -> the pump dead-headed ~80 s past
        the last valve close on every manual + scheduled run. Fix: `pre_deadline` is
        `_master_off_deadline` snapshotted BEFORE the sweep began noting (see
        `_dist_run_sweep`). If it is a real future time, a concurrent consumer
        legitimately holds the master -> defer, collapsing our own inflated rolling note
        back down to that external floor. Otherwise finalize synchronously (solo) so a
        back-to-back sibling re-arms (re-kicks) the master cleanly. Scenario 6 (a
        parallel normal-zone run that outlasts the sweep) stays protected because its
        deadline IS the snapshot.
        NOT-TO-DO: do not read `_distributor_concurrent()`/`zone_sequencing` here — the
        static flag is exactly what mis-fired; the live pre-sweep snapshot is the truth.
        The per-pause master cycling (`_dist_master_window_off/on`) still keys on the
        `concurrent` flag — only the TERMINAL collapse moved to the snapshot.
        siehe test_distributor_dispatch.py::test_master_end_finalizes_synchronously_when_solo
        and ::test_master_end_defers_when_concurrent
        """
        if not self._dist_uses_master(distributor):
            self._master_on = False
            return
        if pre_deadline is not None and self._master_now() < pre_deadline:
            # A genuine concurrent consumer holds the master: defer to ITS deadline,
            # collapsing our own inflated rolling note back down to the external floor.
            self._master_off_deadline = pre_deadline
            await self.async_master_schedule_off()
            return
        if self._dist_master_off_after():
            await self._master_turn(False)
        self._master_on = False
        self._master_off_deadline = None
        cancel = getattr(self, "_master_off_cancel", None)
        if cancel:
            cancel()
            self._master_off_cancel = None
```

- [ ] **Step 5: Implement — update both `_dist_master_end` call sites**

In `_dist_run_sweep`, the confirm-fail path (currently `:799`) and the terminal (currently `:860`) both read:
```python
            await self._dist_master_end(distributor, concurrent=concurrent)
```
Change BOTH to:
```python
            await self._dist_master_end(distributor, pre_deadline=pre_deadline)
```
(The `concurrent` parameter of `_dist_run_sweep` stays — it is still used by `_dist_master_window_off`/`_dist_master_window_on` in the pause block.)

- [ ] **Step 6: Run the end-to-end test to verify it passes**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_solo_run_under_parallel_collapses_master_at_last_valve_close" -q
```
Expected: PASS.

- [ ] **Step 7: Update the `_dist_master_end` direct tests in `test_distributor.py`**

REALITY CHECK (found during execution): there are FOUR existing tests that call
`_dist_master_end(..., concurrent=...)`, not two. `test_distributor.py:263`
(`use_master=False`, no kwarg) and `test_distributor_cycle.py:142` (method fully
mocked) need NO change. The two duplicate new unit tests the plan first proposed are
dropped — the existing `test_master_end_finalizes_synchronously_when_solo` and
`test_master_end_defers_when_concurrent` already cover solo/defer, so they are
updated to carry the Bug-1 collapse assertions instead (DRY).

In `tests/test_distributor.py`, add `import datetime` at the top (after
`from types import SimpleNamespace`). Then replace
`test_master_end_defers_to_overlap_safe_deadline_when_using_master`
(currently `:237-252`) with:

```python
async def test_master_end_defers_to_overlap_safe_deadline_when_using_master():
    # G2/H1 -> Bug 1 (2026-07-06): the defer path is now keyed on a real pre-existing
    # external deadline (pre_deadline snapshot), not the static concurrent flag. On a
    # real overlap: no immediate off, deadline collapsed to the external floor, shutdown
    # handed to the overlap-safe scheduler. Solo (pre_deadline None) finalizes
    # synchronously instead (see test_master_end_finalizes_synchronously_when_solo).
    c = _host(master_off_after=True)
    c.async_master_schedule_off = AsyncMock()
    c._master_on = True
    pre = c._master_now() + datetime.timedelta(seconds=120)
    await c._dist_master_end(_dist(), pre_deadline=pre)
    c.hass.services.async_call.assert_not_awaited()
    c.async_master_schedule_off.assert_awaited_once()
    assert c._master_off_deadline == pre
```

- [ ] **Step 8: Update the three `_dist_master_end` direct tests in `test_distributor_dispatch.py`**

`datetime` is already imported at module level. Replace the three tests:

`test_master_end_defers_to_pending_deadline_not_immediate_off` (currently `:10-20`):

```python
async def test_master_end_defers_to_pending_deadline_not_immediate_off():
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c.async_master_schedule_off = AsyncMock()
    # a concurrent normal-zone run has already claimed the master; its deadline is the
    # snapshot the sweep captured before it started noting (Bug 1, 2026-07-06).
    pre = c._master_now() + datetime.timedelta(seconds=120)
    c._master_off_deadline = pre
    await c._dist_master_end(_dist(), pre_deadline=pre)
    c.hass.services.async_call.assert_not_awaited()
    c.async_master_schedule_off.assert_awaited_once()
```

`test_master_end_finalizes_synchronously_when_solo` (currently `:394-402`) — set a
FUTURE (inflated rolling) deadline to prove the collapse to None:

```python
async def test_master_end_finalizes_synchronously_when_solo():
    # Bug 1 (2026-07-06): pre_deadline None -> no genuine concurrent consumer ->
    # synchronous shutdown at the last valve close, collapsing the sweep's inflated
    # rolling deadline to None. (Was the concurrent=False path; now keyed on the snapshot.)
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c._master_on = True
    c._master_off_deadline = c._master_now() + datetime.timedelta(seconds=999)
    c._master_turn = AsyncMock()
    await c._dist_master_end(_dist(id=0), pre_deadline=None)
    c._master_turn.assert_awaited_once_with(False)
    assert c._master_on is False
    assert c._master_off_deadline is None
```

`test_master_end_defers_when_concurrent` (currently `:405-416`) — drop the local
`import datetime`; assert the collapse to the external floor:

```python
async def test_master_end_defers_when_concurrent():
    # Bug 1 (2026-07-06): a real external deadline pre-existed the sweep (a concurrent
    # normal-zone run) -> defer, collapsing our inflated rolling note back to that
    # external floor (never powering the master off).
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c._master_on = True
    now = c._master_now()
    pre = now + datetime.timedelta(seconds=120)  # the external floor (snapshot)
    c._master_off_deadline = now + datetime.timedelta(seconds=300)  # inflated rolling
    c._master_turn = AsyncMock()
    c.async_master_schedule_off = AsyncMock()
    await c._dist_master_end(_dist(id=0), pre_deadline=pre)
    c._master_turn.assert_not_awaited()
    c.async_master_schedule_off.assert_awaited_once()
    assert c._master_on is True
    assert c._master_off_deadline == pre  # collapsed to the external floor
```

- [ ] **Step 9: Run the full master-end + H7 set to verify GREEN (incl. must-stay-green)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock \
  -k "test_master_end or test_master_note_is_rolling_not_upfront_estimate or test_concurrent_longer_normal_zone_deadline_wins or test_solo_run_under_parallel_collapses or test_concurrent_long_window_extends_deadline or test_cycle_notes_sweep_estimate_to_master_deadline" -q
```
Expected: PASS (all). Critically `test_master_note_is_rolling_not_upfront_estimate` and `test_concurrent_longer_normal_zone_deadline_wins` still pass.

- [ ] **Step 10: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py tests/test_distributor_dispatch.py
git commit -m "fix(distributor): collapse master synchronously on solo sweep end

Bug 1: key the terminal master shut-off on a pre-sweep _master_off_deadline
snapshot, not the static parallel flag, so a solo distributor run powers the
pump off at the last valve close instead of dead-heading ~80s on the inflated
rolling deadline. Scenario 6 (concurrent normal-zone run) stays deferred via the
snapshot floor.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Bug 2 — bounded boot-time master normalization

**Files:**
- Modify: `custom_components/smart_irrigation/master.py` (add method after `async_master_schedule_off`, currently ends `:135`)
- Modify: `custom_components/smart_irrigation/__init__.py:179` (wire the call)
- Test: `tests/test_master.py`

- [ ] **Step 1: Write the failing unit tests**

Add to `tests/test_master.py` (end of file; `datetime`, `AsyncMock`, `Mock`, `_mcoord` are in scope):

```python
async def test_reconcile_master_off_when_off_after_and_idle():
    # Bug 2 (2026-07-06): off_after enabled, master configured, nothing HASI-driven
    # still running -> defensively power the orphaned master off after a restart.
    c = _mcoord(master_off_after=True)
    c.store.async_get_distributors = AsyncMock(return_value=[])
    c._sc_active_runs = AsyncMock(return_value=[])
    c._master_on = True
    c._master_off_deadline = "stale"
    await c.async_reconcile_master_after_restart()
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_off", {"entity_id": "switch.pump"}
    )
    assert c._master_on is False
    assert c._master_off_deadline is None


async def test_reconcile_master_untouched_when_off_after_disabled():
    # off_after off -> HASI never auto-shuts the master, so it must not at boot either.
    c = _mcoord(master_off_after=False)
    c.store.async_get_distributors = AsyncMock(return_value=[])
    c._sc_active_runs = AsyncMock(return_value=[])
    await c.async_reconcile_master_after_restart()
    c.hass.services.async_call.assert_not_awaited()


async def test_reconcile_master_untouched_when_self_closing_active():
    # A self-closing run is still mid-window on hardware -> it legitimately needs the
    # master; defer (do not power off).
    c = _mcoord(master_off_after=True)
    c.store.async_get_distributors = AsyncMock(return_value=[])
    c._sc_active_runs = AsyncMock(return_value=[{"zone_id": 7}])
    await c.async_reconcile_master_after_restart()
    c.hass.services.async_call.assert_not_awaited()


async def test_reconcile_master_untouched_when_distributor_cycle_in_flight():
    # A distributor still has a persisted active_cycle -> something is (being) resumed;
    # do not force the master off.
    c = _mcoord(master_off_after=True)
    c.store.async_get_distributors = AsyncMock(
        return_value=[{"id": 0, "active_cycle": {"outlet": 1, "phase": "watering"}}]
    )
    c._sc_active_runs = AsyncMock(return_value=[])
    await c.async_reconcile_master_after_restart()
    c.hass.services.async_call.assert_not_awaited()


async def test_reconcile_noop_when_master_not_configured():
    c = _mcoord(master_entity=None)
    c.store.async_get_distributors = AsyncMock(return_value=[])
    c._sc_active_runs = AsyncMock(return_value=[])
    await c.async_reconcile_master_after_restart()
    c.hass.services.async_call.assert_not_awaited()
```

- [ ] **Step 2: Run them to verify they fail**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_reconcile_master or test_reconcile_noop" -q
```
Expected: FAIL — `AttributeError: ... has no attribute 'async_reconcile_master_after_restart'`.

- [ ] **Step 3: Implement the method**

In `custom_components/smart_irrigation/master.py`, add at the end of `class MasterMixin` (after `async_master_schedule_off`):

```python
    async def async_reconcile_master_after_restart(self) -> None:
        """One-shot boot normalization: kill an orphaned master left on across a
        restart. NOT a runtime watchdog.

        Iter (2026-07-06, Bug 2 — orphaned master): the master-off deadline + timer
        live only in memory and are lost on ANY restart (clean or crash); HA
        restore_state may also bring the master entity back to `on`. A narrow "mirror
        the inlet-close in async_resume_distributor_cycles" fix would MISS the observed
        clean-restart case — the `finally` in async_run_distributor_cycle self-clears
        `active_cycle`, so reconciliation is a no-op there. So key the shut-off on the
        master state + config, not on a surviving cycle record.

        Fires iff ALL hold: a master is configured AND `master_off_after` is enabled
        (the user opted into auto-off — else HASI never auto-shuts the master, so it
        must not at boot either) AND nothing HASI-driven is still running: no
        distributor `active_cycle` (crashed ones were already reconciled by
        async_resume_distributor_cycles just before) and no in-window self-closing run
        (those legitimately need the master — defer to them). Covers BOTH restart
        flavours because it does not depend on a surviving `active_cycle`.
        Called from __init__ AFTER async_resume_self_closing_runs and
        async_resume_distributor_cycles.
        siehe test_master.py::test_reconcile_master_off_when_off_after_and_idle
        """
        if not self._master_configured():
            return
        if not getattr(self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False):
            return
        for dist in await self.store.async_get_distributors():
            if dist.get("active_cycle"):
                return
        if await self._sc_active_runs():
            return
        await self._master_turn(False)
        self._master_on = False
        self._master_off_deadline = None
```

- [ ] **Step 4: Run the unit tests to verify they pass**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_reconcile_master or test_reconcile_noop" -q
```
Expected: PASS (all 5).

- [ ] **Step 5: Wire the call into `__init__.py`**

In `custom_components/smart_irrigation/__init__.py`, immediately after the line `await coordinator.async_resume_distributor_cycles()` (currently `:179`), insert:

```python

    # Bug 2 (2026-07-06): defensively kill an orphaned master left on across a restart
    # (its off-timer is in-memory only and gone after the reboot). One-shot, gated on
    # master_off_after; defers to any still-running self-closing run. Runs AFTER both
    # resume steps so crashed cycles are already reconciled. See master.py.
    await coordinator.async_reconcile_master_after_restart()
```

(No unit test for the one-line wiring — `async_setup_entry` needs the full HA setup harness; the wiring is verified by reading + the live restart re-test in Task 4. The method's behaviour is fully unit-covered above.)

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/master.py custom_components/smart_irrigation/__init__.py tests/test_master.py
git commit -m "fix(master): power off an orphaned master after a mid-cycle restart

Bug 2: the master-off deadline+timer are in-memory only and lost on any restart,
so a pump running when HA restarts can stay on indefinitely. Add a one-shot boot
normalization that powers the master off iff master_off_after is enabled and
nothing HASI-driven is still running (no distributor active_cycle, no in-window
self-closing run). Keyed on master state+config, not a surviving cycle record, so
it covers both clean-restart and hard-crash.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Full regression, sister-path review, formatting

**Files:** none new — verification + REGEL 8 review.

- [ ] **Step 1: Run the full distributor + master + irrigation + scheduler test set**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock \
  tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py \
  tests/test_distributor_integration.py tests/test_master.py -q
```
Expected: PASS, no regressions.

- [ ] **Step 2: Run the ENTIRE suite (catch cross-module regressions)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -15
```
Expected: the same pass count as baseline plus the 8 new tests; no NEW failures vs. the pre-change baseline (record the baseline failure count first if any environment-only failures exist).

- [ ] **Step 3: REGEL 8 — sister-path check**

Read the full `_dist_master_end` (all three branches: no-master / external-defer / solo-sync) and confirm each is internally consistent. Then scan for structurally-similar master shut-off paths that could share the "keyed on the wrong signal" pattern:
- `master.py::async_master_schedule_off` `_fire` — deadline-driven, already correct.
- The self-closing subsystem's master handling — noted OUT OF SCOPE in the spec; confirm it is not silently regressed by these changes (it is not touched).
Document findings inline in the task notes; fold any mirror bug into this cycle (none expected).

- [ ] **Step 4: Format check (if ruff/black available in the env)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black --check custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/master.py custom_components/smart_irrigation/__init__.py tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_master.py 2>&1 | tail -5 || echo "black not in env — CI (Linux) is the formatting gate"
```
Expected: all files formatted (or the note that CI is the gate). If black reformats, `git add` + amend the relevant commit.

---

## Task 4: Beta build, deploy to HA-Test, live re-test

**Files:** none — operational. NOTE: this fix is BACKEND-ONLY (Python) — no frontend/TS change, so the frontend `dist` is unchanged.

- [ ] **Step 1: Code review checkpoint (REGEL 1, sensitive subsystem G2→H1→H7→now)**

Dispatch `superpowers:code-reviewer` (or self-review) on the diff of `distributor.py` + `master.py` + `__init__.py` against the spec before any hardware touch. Address findings before deploy.

- [ ] **Step 2: Deploy the changed integration to HA-Test**

Backend-only: sync `custom_components/smart_irrigation/{distributor.py,master.py,__init__.py}` to the HA-Test instance per the established deploy path. HA-Test restart is REQUIRED to load new Python — per memory `ha-no-auto-restart`, get explicit user go-ahead before restarting. Use `mcp__HA-Test__` to confirm the integration reloaded and the running version.

- [ ] **Step 3: Live re-test Bug 1 (the ~80 s dead-head)**

Trigger a real distributor run on HA-Test (manual member run or a scheduled sweep) and, via `mcp__HA-Test__` history, confirm the master goes OFF ~0 s after the last valve close (NOT ~80 s later). Compare against the pre-fix live trace (last valve close vs. master-off timestamp).

- [ ] **Step 4: Live re-test Bug 2 (orphaned master)**

With `master_off_after` enabled and the pump on mid-cycle, trigger an HA-Test restart (user go-ahead required). After boot, confirm via `mcp__HA-Test__` that the master entity is OFF (no orphaned pump), with no in-window self-closing run present.

- [ ] **Step 5: Update memories**

Update `hasi-distributor-master-overrun`, `hasi-distributor-restart-recovery`, and `hasi-distributor-fix-roadmap` (Phase 1) to reflect the fix + live verification result.

---

## Self-review

- **Spec coverage:** Bug 1 (snapshot + terminal collapse + scenario-6 protection) → Task 1. Bug 2 (config-gated, self-closing-deferring boot normalization) → Task 2. New regression tests (solo-collapse-under-parallel + reconciliation) → Tasks 1 & 2. Must-stay-green tests → Task 1 Step 9. Live re-test → Task 4. All spec sections mapped.
- **Placeholders:** none — every code/test step contains full content and exact paths.
- **Type/signature consistency:** `_dist_master_end(distributor, *, pre_deadline=None)` used consistently at both call sites and in all four unit/e2e tests; `async_reconcile_master_after_restart(self)` used consistently in `master.py`, `__init__.py`, and all five Bug-2 tests; `pre_deadline` local threaded from `_dist_run_sweep` snapshot; `_sc_active_runs`, `store.async_get_distributors`, `CONF_MASTER_OFF_AFTER`, `_master_configured`, `_master_turn` match their real definitions.
