"""Probe: what the run-start resolver answers when the calculation IS the dispatch.

Runs the REAL _next_governing_time and _advance_past_fired_occurrence. Only the
clock/sun layer (_resolve_bound) is stood in for, with a plain daily 06:00 UTC
bound. That is the layer test_next_run_start_for_zone.py replaces wholesale, which
is why its tests cannot see the defect the maintainer reported.

Two situations, one resolver:
  A) the calculation runs AHEAD of the run (a fixed-time autocalc)      -> want today's 06:00
  B) the calculation runs INSIDE the run's own dispatch (before_run)    -> want "now"
Run it against any checkout of the package:

    python 2026-09-27-before-run-anchor.py [path-to-checkout]

The default below is the scratch worktree it was measured in, which will not
survive a cleanup -- pass a path instead. Measured against the `JustChr#172` branch before the anchor fix; the resolver's own answer is
unchanged by that fix, so it prints the same rows on master.
"""

import asyncio
import datetime
import sys

_DEFAULT_CHECKOUT = "D:/Entwicklung/HASI/issue21-work/pr"
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_CHECKOUT)

from custom_components.irrigation_plus import const  # noqa: E402
from tests.test_scheduler import _make_manager  # noqa: E402

UTC = datetime.timezone.utc
SID = "s1"
# The run we are dispatching: today 06:00 UTC, with the daily bound at 06:00.
TODAY_RUN = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC)
TOMORROW_RUN = TODAY_RUN + datetime.timedelta(days=1)


def _schedule():
    return {
        const.SCHEDULE_CONF_ID: SID,
        const.SCHEDULE_CONF_ENABLED: True,
        const.SCHEDULE_CONF_ZONES: "all",
        const.SCHEDULE_CONF_RECURRENCE: const.SCHEDULE_RECURRENCE_DAILY,
        const.SCHEDULE_CONF_START_MODE: const.SCHEDULE_BOUND_MODE_TIME,
        const.SCHEDULE_CONF_FINISH_MODE: const.SCHEDULE_BOUND_MODE_NONE,
    }


def _install_daily_bound(manager, now):
    """A real daily 06:00 UTC bound, resolved strictly after the reference."""

    async def _resolve(schedule, end, reference_utc, *, direction):
        ref = reference_utc or now
        candidate = ref.replace(hour=6, minute=0, second=0, microsecond=0)
        while candidate <= ref:  # strictly after, like the real resolver
            candidate += datetime.timedelta(days=1)
        return candidate

    manager._resolve_bound = _resolve


async def main():
    import homeassistant.util.dt as dt_util

    from custom_components.irrigation_plus import scheduler as sched_mod

    rows = []

    # --- A) calculation AHEAD of the run: autocalc at 03:00, run at 06:00 -----
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    at_0300 = TODAY_RUN - datetime.timedelta(hours=3)
    _install_daily_bound(manager, at_0300)
    real_utcnow = dt_util.utcnow
    sched_mod.dt_util.utcnow = lambda: at_0300
    try:
        got = await manager.async_next_run_start_for_zone(1)
    finally:
        sched_mod.dt_util.utcnow = real_utcnow
    rows.append(("A  calc ahead of the run (03:00)", TODAY_RUN, got))

    # --- B) calculation INSIDE the dispatch (before_run), finish callback ----
    # What the fire callback does first, verbatim from scheduler.py:1656-1657.
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _install_daily_bound(manager, TODAY_RUN)
    manager._finish_last_target[SID] = TODAY_RUN.isoformat()
    manager._armed_runs.pop(SID, None)
    sched_mod.dt_util.utcnow = lambda: TODAY_RUN
    try:
        got = await manager.async_next_run_start_for_zone(1)
    finally:
        sched_mod.dt_util.utcnow = real_utcnow
    rows.append(("B1 dispatch, finish callback", TODAY_RUN, got))

    # --- B2) plain start-time schedule: nothing sets _finish_last_target -----
    # The second mechanism: _next_governing_time resolves STRICTLY after now, and
    # at dispatch "now" already is the occurrence.
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _install_daily_bound(manager, TODAY_RUN)
    sched_mod.dt_util.utcnow = lambda: TODAY_RUN
    try:
        got = await manager.async_next_run_start_for_zone(1)
    finally:
        sched_mod.dt_util.utcnow = real_utcnow
    rows.append(("B2 dispatch, plain start-time", TODAY_RUN, got))

    print(f"{'situation':34} {'run really starts':26} {'resolver says':26} verdict")
    print("-" * 104)
    for label, want, got in rows:
        ok = "OK" if got == want else f"WRONG (+{(got - want)})" if got else "None"
        print(f"{label:34} {str(want):26} {str(got):26} {ok}")


asyncio.run(main())
