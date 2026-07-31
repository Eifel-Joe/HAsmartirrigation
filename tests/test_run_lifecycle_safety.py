"""Lifecycle safety for schedules and in-progress valve runs (review 2026-07-31).

Three independent defects, all in the "what happens when something ends
unexpectedly" seam that the feature tests never exercise:

R1  ``RecurringScheduleManager`` had no teardown and ``coordinator.async_unload``
    never cancelled its trackers. HA listeners registered by the OLD manager
    survived a config-entry reload still bound to the OLD coordinator, so every
    reload added a second armed copy of every schedule -> N reloads, N+1 firings
    of each schedule (each driving its own coordinator).

R2  No valve-open path guaranteed the valve was closed again. ``turn_off`` sat on
    the happy path inside ``try`` whose ``finally`` only cleared the run marker,
    so any exception (store write, flow-meter arithmetic) or a ``CancelledError``
    at shutdown left the valve PHYSICALLY OPEN with nothing scheduled to close
    it. There is no other net: ``async_unload`` does not stop runs.

R3  Irrigation was dispatched with bare ``asyncio.create_task``. The event loop
    keeps only a weak reference to a task, so a run could be garbage-collected
    mid-execution, and the tasks were invisible to HA's shutdown handling.
    ``hass.async_create_task`` is tracked, cancelled on shutdown and logs
    exceptions.

Coordinators are built with ``__new__`` so only the touched attributes are wired,
matching tests/test_stop_zone.py and tests/test_rain_delay.py.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const
from custom_components.smart_irrigation.scheduler import RecurringScheduleManager


class _FakeStore:
    def __init__(self, zones=None, config=None):
        self.zones = {int(z[const.ZONE_ID]): dict(z) for z in (zones or [])}
        self.config = config or SimpleNamespace(
            rain_delay_until=None,
            zone_sequencing=const.CONF_ZONE_SEQUENCING_PARALLEL,
            live_estimate_enabled=False,
        )

    def get_zone(self, zone_id):
        z = self.zones.get(int(zone_id))
        return dict(z) if z is not None else None

    async def async_update_zone(self, zone_id, changes):
        self.zones.setdefault(int(zone_id), {const.ZONE_ID: int(zone_id)}).update(
            changes
        )
        return dict(self.zones[int(zone_id)])

    async def async_get_zones(self):
        return [dict(z) for z in self.zones.values()]

    async def async_get_distributors(self):
        return []


def _coord(monkeypatch, zones=None, config=None, units=METRIC_SYSTEM):
    monkeypatch.setattr(
        "custom_components.smart_irrigation.irrigation.async_dispatcher_send", Mock()
    )
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.config = Mock()
    hass.config.units = units
    hass.loop = asyncio.get_event_loop()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.states = Mock()
    # Swallow the coroutine so an un-awaited-coroutine warning can't mask a failure.
    hass.async_create_task = Mock(side_effect=lambda coro, *a, **k: coro.close())
    coord.hass = hass
    coord.store = _FakeStore(zones, config)
    coord._live_run_zones = set()
    return coord


def _timed_zone(**over):
    z = {
        const.ZONE_ID: 1,
        const.ZONE_NAME: "Lawn",
        const.ZONE_LINKED_ENTITY: "switch.valve",
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 300,
        const.ZONE_SIZE: 100.0,
        const.ZONE_THROUGHPUT: 10.0,
        const.ZONE_BUCKET: -5.0,
        const.ZONE_BUCKET_THRESHOLD: 0.0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_RUN_LOG: [],
    }
    z.update(over)
    return z


def _turn_off_calls(hass):
    return [
        c
        for c in hass.services.async_call.call_args_list
        if len(c.args) >= 2 and c.args[1] == "turn_off"
    ]


# --------------------------------------------------------------------------- #
# R1 — scheduler teardown on unload
# --------------------------------------------------------------------------- #
def _unloadable_coord():
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.data = {const.DOMAIN: {}}
    coord.hass = hass
    coord._pending_track_update_unsub = None
    coord._track_auto_update_time_unsub = None
    coord._track_auto_calc_time_unsub = None
    coord._track_midnight_time_unsub = None
    coord._track_buffer_flush_unsub = None
    coord.async_teardown_observed_watering = Mock()
    coord._dist_inlet_watchers = {}
    coord._subscriptions = []
    return coord


@pytest.mark.asyncio
async def test_manager_unload_cancels_every_tracker_and_the_rearm():
    """The manager must release every HA listener it registered."""
    manager = RecurringScheduleManager(Mock(), Mock())
    daily, sunrise = Mock(), Mock()
    manager._schedule_trackers = {"daily": daily, "sunrise": sunrise}
    manager._unsub_rearm = Mock()
    manager._finish_last_target = {"daily": "2026-07-31T06:00:00+00:00"}
    rearm = manager._unsub_rearm

    await manager.async_unload()

    daily.assert_called_once_with()
    sunrise.assert_called_once_with()
    rearm.assert_called_once_with()
    assert manager._schedule_trackers == {}
    assert manager._unsub_rearm is None
    assert manager._finish_last_target == {}


@pytest.mark.asyncio
async def test_manager_unload_tolerates_none_trackers():
    """A tracker slot can legitimately hold None (setup returned no handle)."""
    manager = RecurringScheduleManager(Mock(), Mock())
    manager._schedule_trackers = {"broken": None}
    manager._unsub_rearm = None
    await manager.async_unload()  # must not raise
    assert manager._schedule_trackers == {}


@pytest.mark.asyncio
async def test_coordinator_unload_tears_down_the_schedule_manager():
    """R1 regression: without this, a reload leaves the old trackers armed and
    every schedule fires once per surviving manager."""
    coord = _unloadable_coord()
    manager = RecurringScheduleManager(Mock(), coord)
    tracker = Mock()
    manager._schedule_trackers = {"daily": tracker}
    manager._unsub_rearm = Mock()
    rearm = manager._unsub_rearm
    coord.recurring_schedule_manager = manager

    await coord.async_unload()

    tracker.assert_called_once_with()
    rearm.assert_called_once_with()


@pytest.mark.asyncio
async def test_coordinator_unload_survives_a_missing_schedule_manager():
    """Unload must never fail the config-entry unload (failed_unload is only
    recoverable by a full HA restart)."""
    coord = _unloadable_coord()
    await coord.async_unload()  # no recurring_schedule_manager attribute at all


# --------------------------------------------------------------------------- #
# R2 — the valve is always closed
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_metered_run_closes_valve_when_the_loop_raises(monkeypatch):
    """R2 regression: an exception mid-run must not strand the valve open."""
    coord = _coord(monkeypatch, zones=[_timed_zone()])
    coord._confirm_valve_running = AsyncMock(return_value=True)
    coord._sleep_or_stopped = AsyncMock(side_effect=RuntimeError("store exploded"))

    with pytest.raises(RuntimeError):
        await coord._run_valve_metered(_timed_zone(), "switch.valve", real_flow=False)

    assert _turn_off_calls(coord.hass), "valve was left open after a mid-run error"


@pytest.mark.asyncio
async def test_metered_run_closes_valve_on_cancellation(monkeypatch):
    """Shutdown/reload cancels the run task; the valve must still close."""
    coord = _coord(monkeypatch, zones=[_timed_zone()])
    coord._confirm_valve_running = AsyncMock(return_value=True)
    coord._sleep_or_stopped = AsyncMock(side_effect=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await coord._run_valve_metered(_timed_zone(), "switch.valve", real_flow=False)

    assert _turn_off_calls(coord.hass), "valve was left open after cancellation"


@pytest.mark.asyncio
async def test_metered_run_closes_the_valve_exactly_once_on_the_happy_path(
    monkeypatch,
):
    """Guard against the obvious fix regressing into a double turn_off."""
    coord = _coord(monkeypatch, zones=[_timed_zone(**{const.ZONE_DURATION: 1})])
    coord._confirm_valve_running = AsyncMock(return_value=True)
    coord._sleep_or_stopped = AsyncMock(return_value=False)

    await coord._run_valve_metered(
        _timed_zone(**{const.ZONE_DURATION: 1}), "switch.valve", real_flow=False
    )

    assert len(_turn_off_calls(coord.hass)) == 1


@pytest.mark.asyncio
async def test_flow_slot_closes_valve_when_the_loop_raises(monkeypatch):
    """The rotating path's flow slot has the same exposure."""
    zone = _timed_zone(**{const.ZONE_FLOW_SENSOR: "sensor.flow"})
    coord = _coord(monkeypatch, zones=[zone])
    coord._read_flow_sample = Mock(side_effect=RuntimeError("sensor exploded"))

    with pytest.raises(RuntimeError):
        await coord._irrigate_zone_flow_slot(zone, "switch.valve", 60.0, 10.0)

    assert _turn_off_calls(coord.hass), "flow slot left the valve open"


# --------------------------------------------------------------------------- #
# R3 — irrigation runs are tracked tasks
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_sequential_dispatch_uses_a_tracked_task(monkeypatch):
    """R3 regression: a bare asyncio.create_task is GC-able mid-run and invisible
    to HA shutdown."""
    config = SimpleNamespace(
        rain_delay_until=None,
        zone_sequencing=const.CONF_ZONE_SEQUENCING_SEQUENTIAL,
        live_estimate_enabled=False,
    )
    coord = _coord(monkeypatch, zones=[_timed_zone()], config=config)
    coord._apply_live_durations = AsyncMock(side_effect=lambda zs: zs)
    coord._apply_soil_moisture_veto = AsyncMock(side_effect=lambda zs: zs)
    coord._sc_is_self_closing = Mock(return_value=False)
    coord.async_master_begin_cycle = AsyncMock()
    coord.async_master_schedule_off = AsyncMock()
    coord._master_note_run = Mock()

    assert await coord._irrigate_linked_entities() is True
    coord.hass.async_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_parallel_dispatch_uses_tracked_tasks(monkeypatch):
    coord = _coord(monkeypatch, zones=[_timed_zone()])
    await coord._irrigate_zones_parallel([_timed_zone()])
    coord.hass.async_create_task.assert_called_once()


# --------------------------------------------------------------------------- #
# R4 — master/pump stays on for the whole cycle
# --------------------------------------------------------------------------- #
def _seq_coord(monkeypatch, sequencing, self_closing_ids=()):
    config = SimpleNamespace(
        rain_delay_until=None,
        zone_sequencing=sequencing,
        live_estimate_enabled=False,
    )
    coord = _coord(monkeypatch, config=config)
    ids = set(self_closing_ids)
    coord._sc_is_self_closing = Mock(side_effect=lambda z: z.get(const.ZONE_ID) in ids)
    return coord


def test_master_cycle_seconds_sums_for_sequential(monkeypatch):
    """R4 regression: back-to-back zones need the SUM, not the longest zone.

    With max(), 3x300s shut the master off at 300s of a 900s cycle — zones 2
    and 3 then opened against a dead pump, delivered nothing, and still credited
    their buckets.
    """
    coord = _seq_coord(monkeypatch, const.CONF_ZONE_SEQUENCING_SEQUENTIAL)
    zones = [
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 3, const.ZONE_DURATION: 300}),
    ]
    assert coord._master_cycle_seconds(zones) == 900


def test_master_cycle_seconds_sums_for_rotating(monkeypatch):
    """Rotating also runs zones back-to-back (in slices)."""
    coord = _seq_coord(monkeypatch, const.CONF_ZONE_SEQUENCING_ROTATING)
    zones = [
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 120}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 240}),
    ]
    assert coord._master_cycle_seconds(zones) == 360


def test_master_cycle_seconds_keeps_max_for_parallel(monkeypatch):
    """Parallel zones really do overlap — max is correct and must not regress."""
    coord = _seq_coord(monkeypatch, const.CONF_ZONE_SEQUENCING_PARALLEL)
    zones = [
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 120}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 240}),
    ]
    assert coord._master_cycle_seconds(zones) == 240


def test_master_cycle_seconds_handles_no_zones(monkeypatch):
    coord = _seq_coord(monkeypatch, const.CONF_ZONE_SEQUENCING_SEQUENTIAL)
    assert coord._master_cycle_seconds([]) == 0.0


def test_self_closing_zones_are_concurrent_not_summed(monkeypatch):
    """Self-closing runs are fire-and-forget (hardware owns the close), so they
    overlap each other AND the linked sequence — summing them dead-heads the pump.

    2 SC x 600s + 2 linked x 300s sequential: the cycle really ends at 600s
    (max(SC group=600, linked group=600)); summing all four gives 1800s, i.e.
    20 minutes of the pump running against closed valves.
    """
    coord = _seq_coord(
        monkeypatch, const.CONF_ZONE_SEQUENCING_SEQUENTIAL, self_closing_ids={10, 11}
    )
    zones = [
        _timed_zone(**{const.ZONE_ID: 10, const.ZONE_DURATION: 600}),
        _timed_zone(**{const.ZONE_ID: 11, const.ZONE_DURATION: 600}),
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 300}),
    ]
    assert coord._master_cycle_seconds(zones) == 600


def test_self_closing_only_cycle_uses_the_longest_zone(monkeypatch):
    """4 SC zones all start together — the cycle is 600s, not 2400s."""
    coord = _seq_coord(
        monkeypatch,
        const.CONF_ZONE_SEQUENCING_SEQUENTIAL,
        self_closing_ids={1, 2, 3, 4},
    )
    zones = [
        _timed_zone(**{const.ZONE_ID: i, const.ZONE_DURATION: 600})
        for i in (1, 2, 3, 4)
    ]
    assert coord._master_cycle_seconds(zones) == 600


def test_linked_sequence_wins_when_it_outlasts_self_closing(monkeypatch):
    """The cycle ends at the LATER group, whichever that is."""
    coord = _seq_coord(
        monkeypatch, const.CONF_ZONE_SEQUENCING_SEQUENTIAL, self_closing_ids={10}
    )
    zones = [
        _timed_zone(**{const.ZONE_ID: 10, const.ZONE_DURATION: 100}),
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 300}),
    ]
    assert coord._master_cycle_seconds(zones) == 600


@pytest.mark.asyncio
async def test_sequential_cycle_notes_the_full_duration(monkeypatch):
    """End-to-end: the scheduled path must note 900s, not 300s."""
    config = SimpleNamespace(
        rain_delay_until=None,
        zone_sequencing=const.CONF_ZONE_SEQUENCING_SEQUENTIAL,
        live_estimate_enabled=False,
    )
    zones = [
        _timed_zone(**{const.ZONE_ID: 1, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 2, const.ZONE_DURATION: 300}),
        _timed_zone(**{const.ZONE_ID: 3, const.ZONE_DURATION: 300}),
    ]
    coord = _coord(monkeypatch, zones=zones, config=config)
    coord._apply_live_durations = AsyncMock(side_effect=lambda zs: zs)
    coord._apply_soil_moisture_veto = AsyncMock(side_effect=lambda zs: zs)
    coord._sc_is_self_closing = Mock(return_value=False)
    coord.async_master_begin_cycle = AsyncMock()
    coord.async_master_schedule_off = AsyncMock()
    coord._master_note_run = Mock()

    await coord._irrigate_linked_entities()

    coord._master_note_run.assert_called_once_with(900)
