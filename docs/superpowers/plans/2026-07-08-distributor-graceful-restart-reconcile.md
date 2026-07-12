# Distributor graceful-restart reconciliation fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the distributor's in-flight `active_cycle` marker across a graceful restart/reload so the existing boot reconcile (inlet-close mid-watering, uncertain mid-pause) fires instead of being a no-op.

**Architecture:** In `async_run_distributor_cycle`, catch `asyncio.CancelledError` (raised when HA shutdown / integration reload cancels the awaited service task), flag it, re-raise; the `finally` releases the in-memory single-flight lock but skips `_dist_clear_cycle` when interrupted. The last-persisted `active_cycle` survives on disk (`SAVE_DELAY=0`), so `async_resume_distributor_cycles` reconciles it on the next setup. Only `CancelledError` preserves the marker; normal completion and in-process errors still clear it.

**Tech Stack:** Python 3.12, Home Assistant custom integration.

**Spec:** `docs/superpowers/specs/2026-07-08-distributor-graceful-restart-reconcile-design.md`

---

## Test env
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```
black-format Python before committing. Commit via a Bash heredoc `git commit -F - <<'EOF' … EOF` — NEVER PowerShell.

## File structure
- `custom_components/smart_irrigation/distributor.py` — `async_run_distributor_cycle` try/except/finally (`:811-827`).
- Tests: `tests/test_distributor_cycle.py` (reuses `_loop_host`, which mocks `_dist_clear_cycle`).

No other files. `asyncio` is already imported in `distributor.py`. Sister-path (`async_resume_self_closing_runs`) verified unaffected in the spec — no change.

---

## Task 1: Preserve active_cycle on graceful cancellation

**Files:** Modify `distributor.py:811-827`; Test `tests/test_distributor_cycle.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_distributor_cycle.py`, ensure `import pytest` is present at the top (add it after `import asyncio` on line 3 if missing). Then add these three tests (they reuse the existing `_loop_host`/`_dist_cfg`/`_mem` helpers; `_loop_host` already mocks `_dist_clear_cycle` as an AsyncMock):

```python
async def test_cancelled_cycle_preserves_active_cycle_marker():
    # HA shutdown / integration reload cancels the awaited cycle task. The active_cycle
    # marker must be PRESERVED (not cleared) so async_resume_distributor_cycles can act
    # on the interrupted phase on the next setup. The old finally always cleared it,
    # making the boot reconcile a no-op on every graceful restart.
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    c._dist_run_sweep = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await c.async_run_distributor_cycle(_dist_cfg())
    c._dist_clear_cycle.assert_not_awaited()  # marker kept for the boot reconcile
    assert 0 not in c._dist_inflight_ids()     # in-memory single-flight lock released


async def test_normal_cycle_clears_active_cycle_marker():
    # Unchanged: a cycle that completes normally still clears the marker.
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    c._dist_run_sweep = AsyncMock(return_value=True)
    ran = await c.async_run_distributor_cycle(_dist_cfg())
    assert ran is True
    c._dist_clear_cycle.assert_awaited_once_with(0)


async def test_errored_cycle_clears_active_cycle_marker():
    # Unchanged: an in-process (non-cancel) error still clears the marker — HA keeps
    # running, so there is no restart to reconcile.
    c = _loop_host([_mem(1, 1), _mem(2, 2)])
    c._dist_run_sweep = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await c.async_run_distributor_cycle(_dist_cfg())
    c._dist_clear_cycle.assert_awaited_once_with(0)
```

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "cancelled_cycle_preserves or normal_cycle_clears or errored_cycle_clears" -q
```
Expected: `test_cancelled_cycle_preserves_active_cycle_marker` FAILS (the current finally clears the marker unconditionally, so `_dist_clear_cycle` IS awaited). The other two PASS already (they assert the unchanged clear-on-normal/error behaviour).

- [ ] **Step 3: Apply the fix**

In `distributor.py`, replace the `try/finally` at the end of `async_run_distributor_cycle` (currently `:811-827`):
```python
        inflight.add(dist_id)
        try:
            await self._dist_persist_cycle(
                dist_id,
                int(distributor.get("current_outlet") or 1),
                const.DISTRIBUTOR_PHASE_STARTING,
            )
            return await self._dist_run_sweep(
                distributor,
                concurrent=concurrent,
                test_run=test_run,
                only_zone_ids=only_zone_ids,
                duration_override=duration_override,
                force_water=force_water,
            )
        finally:
            inflight.discard(dist_id)
            await self._dist_clear_cycle(dist_id)
```
with:
```python
        inflight.add(dist_id)
        # (2026-07-08, live-test finding) Preserve active_cycle across a graceful
        # interruption. HA shutdown / integration reload cancels this awaited task,
        # raising CancelledError; the old finally ALWAYS cleared active_cycle, so on the
        # next setup async_resume_distributor_cycles read an empty marker and skipped —
        # the inlet-close (mid-watering) and uncertain (mid-pause) reconcile never fired
        # on a graceful restart (only a hard crash, where finally never runs, worked).
        # Keep the last-persisted marker (already on disk, SAVE_DELAY=0) on cancellation
        # so the boot reconcile acts on the interrupted phase; the boot reconcile clears
        # it. A normal return or an in-process error still clears it here (no restart to
        # reconcile). NOT-TO-DO: don't await _dist_close_inlet here — awaiting during
        # cancellation is fragile; the boot reconcile owns the inlet close.
        # siehe test_distributor_cycle.py::test_cancelled_cycle_preserves_active_cycle_marker
        interrupted = False
        try:
            await self._dist_persist_cycle(
                dist_id,
                int(distributor.get("current_outlet") or 1),
                const.DISTRIBUTOR_PHASE_STARTING,
            )
            return await self._dist_run_sweep(
                distributor,
                concurrent=concurrent,
                test_run=test_run,
                only_zone_ids=only_zone_ids,
                duration_override=duration_override,
                force_water=force_water,
            )
        except asyncio.CancelledError:
            interrupted = True
            raise
        finally:
            inflight.discard(dist_id)
            if not interrupted:
                await self._dist_clear_cycle(dist_id)
```

- [ ] **Step 4: Run the three tests + the full distributor-cycle suite**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_cycle.py tests/test_distributor_dispatch.py tests/test_distributor_integration.py -q
```
Expected: PASS, 0 failures. In particular the existing single-flight and resume tests stay green: `test_second_concurrent_cycle_rejected_by_single_flight_lock` (the lock still releases via `inflight.discard`), `test_lock_released_when_cycle_returns_early` (the nothing-due sweep returns False normally → `interrupted` stays False → the finally still clears the marker), `test_resume_mid_pausing_marks_uncertain`, `test_resume_mid_watering_stays_synced_closes_inlet`.

- [ ] **Step 5: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_cycle.py
git commit -F - <<'EOF'
fix(distributor): keep active_cycle across a graceful restart so boot reconcile fires

async_run_distributor_cycle's finally cleared active_cycle on EVERY exit, including task
cancellation. A graceful homeassistant.restart / integration reload cancels the awaited
cycle task -> finally cleared the marker -> async_resume_distributor_cycles read an empty
active_cycle on the next setup and skipped: the mid-watering inlet-close and mid-pause
uncertain reconcile never fired on a graceful restart (only a hard crash, where finally
never runs, worked). Now catch CancelledError and skip the clear so the last-persisted
marker (on disk, SAVE_DELAY=0) survives for the boot reconcile; normal completion and
in-process errors still clear it. Surfaced by live testing on HA-Test (b24).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: Regression, code review, release (b25)

- [ ] **Step 1: Full backend suite vs baseline (no new failures) + black --check.**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -3
```
Expected: only the pre-existing ~67 failures/errors (diagnostics/init/panel/schedule_time_anchor/watering_calendar); 0 distributor failures.

- [ ] **Step 2: Code-review checkpoint** — dispatch `superpowers:code-reviewer` on the diff vs the spec (focus: only `CancelledError` preserves the marker; single-flight lock still released on every path; normal/error paths unchanged; no await during cancellation; sister-path unaffected).

- [ ] **Step 3: Version bump b24 -> b25** (const.py, manifest.json, frontend/package.json) + `npm run build`; same recipe as prior betas.

- [ ] **Step 4: Release** — show notes for approval (REGEL 5), then push + `gh release create v2026.07.11b25 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor`.

- [ ] **Step 5: Update memory** — `hasi-distributor-fix-roadmap` (graceful-restart-reconcile fixed in b25; dismiss/settle the spawn_task chip task_1ab247f4).

---

## Task 3: Live verification on HA-Test (controller, via MCP — not a subagent)

The fix makes the mid-pause→uncertain path reachable by a graceful `homeassistant.restart`, so it is now live-testable. Done by the controller (needs HA-Test MCP access + user go-ahead for install/restart).

- [ ] **Step 1:** Install b25 on HA-Test via HACS (MCP `ha_manage_hacs` update to the new pre-release) and restart.
- [ ] **Step 2:** Set `pause_seconds` large enough for the ~50 s restart config-check to land inside the pause (user sets it, or reuse the existing 120 s) and re-arm commissioning.
- [ ] **Step 3 — mid-pause:** start a test-run, catch `phase=pausing`, `homeassistant.restart`; after boot assert `position_state=uncertain`, commissioning de-armed, halt notification. (Pre-fix this stayed `synced`.)
- [ ] **Step 4 — mid-watering:** start a run, restart while a valve is open; after boot assert the inlet is closed and `position_state=synced`.
- [ ] **Step 5 — idle:** restart while idle; assert no change (`synced` + armed).
- [ ] **Step 6:** restore the test system (re-sync home, reset `pause_seconds` to 15, note commissioning state).

---

## Self-review

- **Spec coverage:** catch `CancelledError` + skip clear when interrupted → Task 1 Step 3; only-CancelledError-preserves (normal/error still clear) → Task 1 tests 2+3; single-flight invariant (lock released via `inflight.discard`) → Task 1 test 1 assert + Step 4 regression; sister-path unaffected → spec-documented, no code; live re-enablement → Task 3. All spec sections mapped.
- **Placeholders:** none — full test + impl code; exact release/version steps mirror prior betas.
- **Type/name consistency:** `interrupted` flag, `asyncio.CancelledError`, `_dist_clear_cycle`, `_dist_run_sweep`, `_dist_inflight_ids`, `_loop_host`, `_dist_cfg`, `_mem` all match the current code/tests.
