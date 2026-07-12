# Master-Lifecycle-Fix (Gardena distributor) — Design

Date: 2026-07-06
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 1 (see memory `hasi-distributor-fix-roadmap`)

## Problem

Two live-confirmed bugs (HA-Test, 2026-07-06) in how the Gardena distributor
drives the ONE shared global master (pump). Both are the *same* subsystem —
"when does the master get shut off" — hanging the shut-off decision on the wrong
signal. This is the next iteration on the master-coordination line
(G2 → H1 → H7), so it is treated as a single systematic fix, not a patch
(REGEL 3).

### Bug 1 — master over-run (~80 s dead-head on every real run)

After a real distributor sweep the master keeps running ~80 s after the last
valve closed, on **every** real run (manual member run + scheduled sweep),
whenever `zone_sequencing = parallel` (the default).

Root cause (code-verified):
- `_distributor_concurrent()` (`distributor.py:185-186`) returns `True`
  **unconditionally** under `parallel`, even when no other consumer of the
  master is actually running.
- So every real run takes the *concurrent* branch of `_dist_master_end`
  (`distributor.py:229-232`): `_master_note_run(0)` + `async_master_schedule_off()`,
  i.e. it **defers** instead of shutting down.
- `_master_note_run` only ever **extends** the deadline (`max()`, `master.py:99`),
  so the terminal `note(0)` cannot collapse the rolling over-estimate deadline set
  during the sweep (last outlet: `window + pause + settle + buffer(30) + confirm(30)`).
- Result: the master rides that inflated deadline ~80 s past the real sweep end.

The core mistake: `_distributor_concurrent()` conflates the *static parallel
flag* with an *actually-active* concurrent master consumer.

### Bug 2 — orphaned master after a mid-cycle restart

If HA restarts while the pump is running, the pump can stay on indefinitely.

Root cause (code-verified + live 2026-07-06):
- The master-off deadline + timer live **only in memory** and are **always lost
  on any restart** (clean or crash). Plus HA `restore_state` may bring the master
  entity back to `on`.
- `async_resume_distributor_cycles` (`distributor.py:892-910`) closes the inlet
  but never touches the master.

Key finding that shaped the fix scope: a **narrow** "mirror the inlet-close in
reconciliation" fix (gated on a surviving `active_cycle`) would **not** catch the
actually-observed incident. On a clean `ha_restart` the `finally` in
`async_run_distributor_cycle` (`distributor.py:595-597`) self-clears
`active_cycle`, so reconciliation is a no-op — yet the master was still left on.
The narrow fix only helps on a hard crash (SIGKILL, no `finally`), which we could
not even reproduce over MCP. So the fix must key on the master state itself, not
on a surviving cycle record.

## Requirements & constraints

- One cycle, both bugs (same subsystem).
- Bug 1: decouple the terminal shut-off decision from the static parallel flag.
  Scenario 6 (a genuinely parallel normal-zone run legitimately holding the
  master) MUST stay protected.
- Bug 2: the boot-time master shut-off fires **only when `master_off_after` is
  enabled** (user decision). If `off_after` is off, HASI never auto-shuts the
  master in normal operation and MUST NOT do so at boot either.
- No runtime watchdog. HASI only cleans up state it can honestly reason about at
  boot; it does not attempt to catch runtime- or user-induced orphans.
- Must not break `test_master_note_is_rolling_not_upfront_estimate` or
  `test_concurrent_longer_normal_zone_deadline_wins`.

## Design — Bug 1: terminal collapse keyed on a live snapshot

Decouple the terminal shut-off from `concurrent`; key it on the master-off
deadline that pre-existed the sweep.

1. In `_dist_run_sweep`, right before `_dist_master_start`, snapshot
   `pre_deadline = getattr(self, "_master_off_deadline", None)`. This is the
   deadline that existed *before* this distributor noted anything — i.e. a
   genuine external consumer (a parallel normal-zone run). Confirmed safe: in both
   the scheduled path (`scheduler.py:782-787`) and the manual path
   (`irrigation.py:1468-1490`) the normal zones note their master deadline
   **before** `_dispatch_distributor_cycles` runs, so the snapshot reliably
   captures a real concurrent run.
2. Change `_dist_master_end`'s signature: replace `concurrent` with `pre_deadline`.
   New terminal logic:
   - `external = pre_deadline is not None and self._master_now() < pre_deadline`
   - **external (scenario 6):** `self._master_off_deadline = pre_deadline`
     (collapse our inflated rolling note back to the real external floor) +
     `await self.async_master_schedule_off()` → defer to the external run's end.
   - **solo (scenarios 1/3):** finalize synchronously — identical to today's
     `else` branch: if `_dist_master_off_after()` → `await self._master_turn(False)`;
     then `self._master_on = False`; `self._master_off_deadline = None`; cancel any
     pending `_master_off_cancel`.
3. Thread `pre_deadline` as a **local parameter** through the call stack
   (re-entrancy-safe; not an instance attribute). Both `_dist_master_end`
   call sites (confirm-fail path ~`distributor.py:799`, terminal ~`distributor.py:860`)
   pass it.

Left unchanged: `_distributor_concurrent()` and the per-pause master cycling
(`_dist_master_window_off/on`) still key on the `concurrent` flag — only the
*terminal collapse* moves to the live snapshot. This keeps the change surgical.

Design decision (defer branch collapses to the floor): in the external branch we
actively reset `_master_off_deadline = pre_deadline` rather than leaving the
inflated rolling value. This removes the ~80 s over-run in the mixed case too, not
just solo.

### Hardening (added after code review, 2026-07-06): foreign mid-sweep note

Code review surfaced that a user manually starting a normal zone
(`async_run_zone`/`async_irrigate_now`) *during* a solo sweep notes a later master
deadline AFTER the snapshot; the pre-snapshot-only terminal then took the solo branch
and *hard-cut* that run's pump. Fix: the sweep tracks `own_deadline` — the ceiling of
its OWN rolling notes (`_master_note_run` now returns the deadline it computed; the
datetime class is read from `_master_now()`, NOT `import datetime`, because the package
ships a sibling `datetime.py` platform that shadows a plain import here). The terminal
now defers when EITHER `pre_deadline` is future (pre-existing consumer) OR the shared
`_master_off_deadline` exceeds `own_deadline` (a foreign consumer noted a later
deadline mid-sweep) — otherwise the deadline is purely our inflation → collapse. So a
manual run of normal duration mid-sweep is honored, not cut.

RESIDUAL LIMITATION (rare, accepted): a foreign note whose deadline falls BELOW our
own inflated ceiling `own_deadline` (a SHORT manual run fired near the sweep end, i.e.
ending within our pause+settle+buffer margin) is still not distinguished and would be
cut. Much narrower than the pre-hardening "cut every mid-sweep manual run"; a fully
general fix needs per-consumer refcounting on the shared master (a bigger refactor,
out of scope, REGEL 3). On the normal scheduled/manual paths (normal zones all note
*before* the distributor dispatch) neither case occurs at all.

## Design — Bug 2: bounded boot-time master normalization

Add a one-shot boot reconciliation (NOT a runtime watchdog):
`async_reconcile_master_after_restart()`, called from `__init__.py` **after** both
existing resume steps (`async_resume_self_closing_runs`,
`async_resume_distributor_cycles`).

It shuts the master off iff ALL hold:
- `self._master_configured()` — a master entity is set;
- `self._dist_master_off_after()` (`CONF_MASTER_OFF_AFTER`) — the user opted into
  auto-off (the user's gate);
- no distributor has a persisted `active_cycle` (nothing HASI is still resuming —
  crashed distributor cycles were already reconciled/closed by
  `async_resume_distributor_cycles` just before);
- `_sc_active_runs()` is empty — no self-closing run is still mid-window (those
  legitimately need the master; defer to them).

Action when all hold: `await self._master_turn(False)`; `self._master_on = False`;
`self._master_off_deadline = None`.

Why this is safe and bounded:
- At boot, before any schedule fires, nothing HASI-driven is running once both
  resume steps have completed. Fire-and-forget normal-zone tasks do not survive a
  restart. Self-closing runs are explicitly deferred to.
- It covers BOTH restart flavours (clean restart AND hard crash), because it keys
  on the master state + config, not on a surviving `active_cycle`.
- It respects the user's config: no `off_after` → master untouched.

Placement: the method lives in `master.py` (master-lifecycle logic). It reads
`self.store.async_get_distributors()` and `self._sc_active_runs()` as
coordinator-provided helpers — consistent with the existing mixin composition
(the distributor mixin already calls `self._master_turn`, `self._master_note_run`,
etc. on the same `self`).

Known limitation (documented, out of scope to fix here): if a restart happens with
BOTH an in-window self-closing run AND an orphaned distributor master, the
self-closing gate defers the master-off, so the distributor orphan persists until
the self-closing cleanup. The self-closing subsystem's own master lifecycle is a
separate concern.

## Tests

New regression tests (not covered by the existing H7 tests):

Bug 1:
- `_dist_master_end(pre_deadline=None)` with `off_after=True`, `_master_on=True`:
  asserts a synchronous master turn-off (`hass` `turn_off` on the master entity),
  `_master_on is False`, `_master_off_deadline is None`. (Solo collapse.)
- `_dist_master_end(pre_deadline=<future>)`: asserts NO direct off, deadline
  collapsed to `pre_deadline`, `async_master_schedule_off` awaited. (External defer.)
- End-to-end: a solo real (non-test) cycle under `zone_sequencing=parallel` with
  `_master_off_deadline=None` collapses the master synchronously at the last valve
  close (the direct Bug-1 catch that H7 misses).

Bug 2 (`async_reconcile_master_after_restart`):
- `off_after=True`, master configured, no distributor `active_cycle`, no
  self-closing runs → master turned off (`turn_off` on the master entity),
  `_master_on/_master_off_deadline` cleared.
- `off_after=False` → master NOT touched (no `turn_off`).
- `off_after=True` but `_sc_active_runs()` non-empty → master NOT touched.
- master not configured → no-op.

Must stay green (verified compatible with the snapshot logic):
- `test_master_note_is_rolling_not_upfront_estimate`
- `test_concurrent_longer_normal_zone_deadline_wins`

Updated to the new signature (they encode the exact behaviour being fixed):
- `test_master_end_defers_to_overlap_safe_deadline_when_using_master`
  (`test_distributor.py`)
- `test_master_end_defers_to_pending_deadline_not_immediate_off`
  (`test_distributor_dispatch.py`)

## Out of scope (separate roadmap phases)

Self-closing inlet-watch gap, soil-veto scope brainstorm, UI to-dos, flow-volume
feature, and the self-closing subsystem's own master lifecycle.
