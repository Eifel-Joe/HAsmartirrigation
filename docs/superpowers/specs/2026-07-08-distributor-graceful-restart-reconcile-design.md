# Distributor graceful-restart reconciliation — Design

Date: 2026-07-08
Branch: `feature/gardena-distributor`
Origin: live test on HA-Test (b24, 2026-07-07) surfaced the gap.

## Problem

`async_resume_distributor_cycles` (`distributor.py:1176`) reconciles an interrupted
distributor cycle on boot: mid-watering → close the inlet (stay synced); mid-pausing →
mark the position uncertain (de-arm, require re-sync). It keys entirely on the persisted
`active_cycle` record.

But `async_run_distributor_cycle`'s `finally` (`distributor.py:825-827`) calls
`_dist_clear_cycle(dist_id)` on **every** exit path, including task cancellation. A
graceful `homeassistant.restart` (or an integration reload) cancels the awaiting service
task → the `finally` runs → `active_cycle = {}` is persisted (`SAVE_DELAY = 0`) → on the
next `async_setup_entry`, the resume reads an empty `active_cycle` → `if not cycle:
continue` → the reconcile is a **no-op**.

So on any graceful restart, neither the inlet-close nor the mid-pause-uncertain fires.
It only works on an ungraceful crash (power loss / kill) where the `finally` never runs
and `active_cycle` survives on disk.

Live-verified: mid-120 s-pause the store showed `active_cycle = {outlet:1, phase:
"pausing"}`, yet after a graceful restart the distributor came back `synced`,
`active_cycle` empty, no notification. The master reconcile (deliberately
`active_cycle`-independent) still worked (master off).

**Real-world impact:** a graceful restart mid-watering with a **classic** switch/valve
inlet leaves the inlet open (the `finally` clears the marker but does not close the
inlet, and the boot reconcile is a no-op; `restore_state` may bring the switch back on)
→ continuous watering until the next cycle. Mid-pause it stays synced when the software
advance may be incomplete.

## Decision (user, 2026-07-08): conservative

Preserve the in-flight `active_cycle` marker across a graceful interruption so the
**existing** boot reconcile fires exactly as designed. Do NOT distinguish clean shutdown
from crash — an interrupted cycle is treated the same way regardless (simplest, safest,
covers reload too). Consequence, fully understood by the user: a restart that lands
**during the brief inter-outlet pause of an actively-running cycle** de-arms the
distributor (→ uncertain, re-sync needed). Every other restart (idle distributor, or
mid-watering) is unaffected in position — mid-watering just closes the inlet and stays
synced.

## Design

### Core change — `async_run_distributor_cycle` (`distributor.py:811-827`)

Catch `asyncio.CancelledError` (raised when HA shutdown / integration reload cancels the
awaiting service task), flag it, re-raise; in the `finally`, release the in-memory
single-flight lock as today but **skip `_dist_clear_cycle` when interrupted**:

```python
        inflight.add(dist_id)
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
            # HA shutdown / integration reload cancels the awaiting task. Preserve the
            # persisted active_cycle marker (STARTING/WATERING/PAUSING, already on disk
            # via SAVE_DELAY=0) so async_resume_distributor_cycles can reconcile the
            # interrupted phase on the next setup — close the inlet mid-watering, mark
            # uncertain mid-pause. Release only the in-memory single-flight lock; the
            # marker is cleared by the boot reconcile.
            interrupted = True
            raise
        finally:
            inflight.discard(dist_id)
            if not interrupted:
                await self._dist_clear_cycle(dist_id)
```

The last-persisted `active_cycle` survives; boot reconcile handles the rest (unchanged).

### Why only `CancelledError`

Only a task cancellation (= HA shutdown / integration reload) preserves the marker. A
normal mid-sweep exception (HA still running) keeps today's behaviour — the `finally`
clears `active_cycle` (the cycle failed in-process; there is no restart, so nothing to
reconcile). Distinguishing on `CancelledError` is the precise signal for "the process is
going away", and it covers both a full HA restart and an integration reload.

### Single-flight invariant

Every `CancelledError` of the cycle is followed by an `async_setup_entry` (boot or
reload) whose `async_resume_distributor_cycles` clears the marker. No HA-still-running
path cancels the awaited cycle (service handlers run to completion; HA does not time out
service coroutines), so the preserved marker cannot get stuck blocking future
`run_now`/`test_run` calls via the single-flight guard.

### Sister-path check (REGEL 8) — not affected

`async_resume_self_closing_runs` (`self_closing.py:273`) reconciles self-closing zone
runs from a **persisted record list** (`CONF_ACTIVE_VALVE_RUNS`) with a time-based
elapsed/planned check. Those records are removed explicitly on completion, not cleared by
a cancellation `finally` (self_closing.py has no `finally`/`CancelledError`), so a
graceful restart does not lose them. This sister-path is NOT affected and needs no
change. (Verified 2026-07-08.)

## Testing

### Unit (test the `finally` clear-vs-preserve directly)

Mock `_dist_clear_cycle` and `_dist_persist_cycle`; drive `async_run_distributor_cycle`
with a mocked `_dist_run_sweep`:

- **Cancelled cycle preserves the marker:** `_dist_run_sweep` side-effect raises
  `asyncio.CancelledError`; assert `_dist_clear_cycle` is **not** awaited and the
  `CancelledError` propagates (`with pytest.raises(asyncio.CancelledError)`). This is the
  exact regression the fix targets — the old code always cleared.
- **Normal completion clears the marker:** `_dist_run_sweep` returns normally; assert
  `_dist_clear_cycle` **is** awaited once (unchanged behaviour).
- **Non-cancel error clears the marker:** `_dist_run_sweep` raises a plain `Exception`;
  assert `_dist_clear_cycle` **is** awaited once and the exception propagates (unchanged).
- The existing resume tests still pass unchanged (see below) — they already assert the
  resume acts correctly GIVEN a surviving `active_cycle`; this fix is what makes it
  survive.
- The existing resume tests (`test_resume_mid_pausing_marks_uncertain`,
  `test_resume_mid_watering_stays_synced_closes_inlet`,
  `test_resume_no_active_cycle_is_noop`) stay green.

### Live (now enabled by the fix — was a no-op pre-fix)

Build b25, install on HA-Test (HACS via MCP), restart. With the emulator distributor and
a large `pause_seconds`:
- graceful `homeassistant.restart` mid-**pause** → after boot `position_state=uncertain`,
  commissioning de-armed, halt notification (reason RESTART_MID_ADVANCE) — the exact
  case that stayed `synced` before the fix.
- graceful restart mid-**watering** → after boot the inlet is closed and the position
  stays `synced`.
- restart while **idle** → no change (stays synced + armed).

## Out of scope

- Distinguishing clean shutdown from a hard crash to avoid the mid-pause de-arm (the
  "clean-shutdown marker" alternative) — explicitly declined in favour of the
  conservative approach.
- Any change to the master reconcile (already correct, `active_cycle`-independent) or the
  self-closing resume (sister-path verified unaffected).
