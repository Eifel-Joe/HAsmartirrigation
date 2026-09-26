"""RecurringScheduleManager.async_next_run_start_for_zone (Eifel-Joe#21).

The forecast weighting runs inside calculate_module, so anything it calls that
reads a zone's bucket or duration closes a loop around the number being
computed. async_get_next_run_projection is therefore unusable there: it sizes
every zone from the bucket at the decision point. This resolver exists to answer
the one question the weighting needs -- when does the next run begin -- while
touching recurrence resolution only.

The recurrence math is tested in test_scheduler.py and the schedule-anchor
suites. These tests patch _next_governing_time so they exercise the resolver's
own decisions instead of re-testing its dependency.
"""

import datetime

import pytest

from custom_components.irrigation_plus import const

from tests.test_scheduler import _make_manager

UTC = datetime.timezone.utc
TARGET = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC)


def _schedule(sid="s1", zones="all", enabled=True):
    return {
        const.SCHEDULE_CONF_ID: sid,
        const.SCHEDULE_CONF_ENABLED: enabled,
        const.SCHEDULE_CONF_ZONES: zones,
        const.SCHEDULE_CONF_RECURRENCE: const.SCHEDULE_RECURRENCE_DAILY,
        const.SCHEDULE_CONF_START_MODE: const.SCHEDULE_BOUND_MODE_TIME,
        const.SCHEDULE_CONF_FINISH_MODE: const.SCHEDULE_BOUND_MODE_NONE,
    }


def _fixed_target(manager, target=TARGET):
    """Stand in for the clock/sun resolution, which has its own tests."""

    async def _governing(schedule, end, reference_utc=None):
        return target

    async def _advance(schedule, end, t, *, quiet=False):
        return t

    manager._next_governing_time = _governing
    manager._advance_past_fired_occurrence = _advance


@pytest.mark.asyncio
async def test_a_schedule_naming_all_zones_answers_for_any_zone():
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) == TARGET


@pytest.mark.asyncio
async def test_a_schedule_naming_the_zone_answers_for_it():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(zones=[2, 3])]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(3) == TARGET


@pytest.mark.asyncio
async def test_a_schedule_not_naming_the_zone_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(zones=[2, 3])]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_a_disabled_schedule_does_not_answer():
    manager, _ = _make_manager()
    manager._schedules = [_schedule(enabled=False)]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_no_schedules_at_all_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = []

    assert await manager.async_next_run_start_for_zone(1) is None


@pytest.mark.asyncio
async def test_a_non_numeric_zone_id_answers_nothing():
    manager, _ = _make_manager()
    manager._schedules = [_schedule()]
    _fixed_target(manager)

    assert await manager.async_next_run_start_for_zone(None) is None
