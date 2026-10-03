"""What an unload leaves behind, and what a disable or a removal has to stop.

A self-closing run owns two timers per zone: the flow sampler, a 15 s interval,
and the backstop, an async_call_later. async_unload cancelled neither, so both
stayed armed against the coordinator being torn down:

* on a reload the new coordinator re-arms a backstop of its own
  (async_resume_self_closing_runs) and settles the run. The old backstop then
  finds no record and returns before it ever reaches its sampler, which ticks on
  until Home Assistant restarts -- and holds the whole dead coordinator;
* a run ending while the reload is under way was settled by the DEAD
  coordinator, its chain, its deferred calculation and its master included.

Cancelling them is right for a reload, which a successor adopts. It is not
enough for an unload nothing adopts: the dead backstop was, by accident, what
settled a run after a disable and released its master, whose off timer then
switched a "master off after" pump off. So a disable now stops and settles what
the integration started, as OpenSprinkler and batch already do, and a removal
sends the stop without settling. The master is ended directly, because its own
off timer is cancelled with the rest.

The scenes run on the real ``hass``: a timer that fires is the defect, and a
double replaces exactly the thing under test.
"""

import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from freezegun import freeze_time
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.exceptions import ServiceNotFound
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_mock_service,
)

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    async_remove_entry,
    async_unload_entry,
    const,
)
from tests.test_master import _mcoord
from tests.test_service_chain import ROTATING, SEQUENTIAL, _finish, _register
from tests.test_service_chain import _coord as _chain_coord
from tests.test_service_chain import _dispatch as _chain_dispatch
from tests.test_service_chain import _ids as _chain_ids
from tests.test_service_chain import _zone as _chain_zone
from tests.test_service_watch import (
    RATE,
    VALVE,
    _advance,
    _coord,
    _dispatch,
    _flow,
    _litres,
    _metered,
    _metered_zone,
    _report,
    _set,
    _the_real_backstop_from_here,
    _walk,
    _zone,
)

DISABLED = "the Irrigation Plus config entry is being disabled"
REMOVED = "the Irrigation Plus config entry is being removed"


def _unloadable(c):
    """Give a test host what async_unload reads without a guard.

    The trackers and _subscriptions are set by __init__, which these hosts skip;
    observed watering is not under test. _os_cancel_watch goes back to the real
    method, so the unload drops the run's watcher as it does in production.
    """
    c.hass.data.setdefault(const.DOMAIN, {})
    c._pending_track_update_unsub = None
    c._track_auto_update_time_unsub = None
    c._track_auto_calc_time_unsub = None
    c._track_midnight_time_unsub = None
    c._track_buffer_flush_unsub = None
    c.async_teardown_observed_watering = Mock()
    c._dist_inlet_watchers = {}
    c._subscriptions = []
    del c._os_cancel_watch
    return c


def _real_master(c, hass, *, off_after=True):
    """Swap the host's master doubles for the real refcount on a mocked pump."""
    del c.async_master_acquire
    del c.async_master_release
    c.store.config.master_entity = "switch.pump"
    c.store.config.master_off_after = off_after
    c.store.config.master_settle_seconds = 0
    c.store.config.master_kick_enabled = False
    c.store.config.master_kick_pause_seconds = 0
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")


def _stops(calls):
    return [
        e.data["service_data"]
        for e in calls
        if e.data["service"] == "stop_irrigation_beet"
    ]


def _opened(calls):
    return [
        e.data["service_data"]["zone_id"]
        for e in calls
        if e.data["service"] == "irrigation_beet"
    ]


def _pump_offs(calls):
    return [
        e
        for e in calls
        if e.data["domain"] == "switch" and e.data["service"] == "turn_off"
    ]


def _called(coordinator):
    return [name for name, _args, _kwargs in coordinator.mock_calls]


def _unload_patches(hass):
    return (
        patch("custom_components.irrigation_plus.remove_panel"),
        patch.object(
            hass.config_entries,
            "async_forward_entry_unload",
            new=AsyncMock(return_value=True),
        ),
    )


# --------------------------------------------------------------------------- #
# The teardown itself
# --------------------------------------------------------------------------- #
class TestTheTeardownCancelsBothTimers:
    """async_teardown_self_closing_handles: cancel, empty, touch nothing else."""

    async def test_both_timers_are_cancelled_and_both_tables_emptied(self, hass):
        """Each table on its own, and every zone in it.

        Zone 2 has both timers. Zone 3 has a backstop only, as every zone
        without a flow sensor does. Zone 4's sampler is running while its
        dispatch has not armed the backstop yet.
        """
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        now = dt_util.utcnow()
        sampler2, sampler4, backstop2, backstop3 = Mock(), Mock(), Mock(), Mock()
        c._sc_meters()[2] = (Mock(), sampler2, 120.0, now)
        c._sc_meters()[4] = (Mock(), sampler4, 120.0, now)
        c._sc_cleanup_timers()[2] = backstop2
        c._sc_cleanup_timers()[3] = backstop3

        c.async_teardown_self_closing_handles()

        for handle in (sampler2, sampler4, backstop2, backstop3):
            handle.assert_called_once_with()
        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}

    async def test_nothing_is_read_settled_or_written(self, hass):
        """The successor owns the run: no final read, no settle, no write."""
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        run = {const.RUN_ZONE_ID: 2}
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [run]
        meter = Mock()
        c._sc_meters()[2] = (meter, Mock(), 120.0, dt_util.utcnow())
        c._sc_cleanup_timers()[2] = Mock()

        c.async_teardown_self_closing_handles()
        await hass.async_block_till_done()  # anything it scheduled has run

        meter.sample.assert_not_called()
        meter.delivered.assert_not_called()
        c._sc_finish_flow.assert_not_called()
        c.store.async_update_config.assert_not_called()
        c.store.async_update_zone.assert_not_called()
        c._record_run.assert_not_called()
        assert c._cfg[const.CONF_ACTIVE_VALVE_RUNS] == [run]  # left for the resume

    def test_a_coordinator_that_never_ran_one_tears_down_cleanly(self):
        c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)

        c.async_teardown_self_closing_handles()

        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}


# --------------------------------------------------------------------------- #
# A reload in the middle of a run
# --------------------------------------------------------------------------- #
class TestAReloadMidRun:
    """The old coordinator unloads, the new one adopts the run from the store."""

    async def test_the_run_is_booked_once_by_the_new_coordinator(self, hass):
        """And the old sampler stops: it used to tick until the next restart.

        The meter does not cross the reload, exactly as it does not cross a
        restart: the new coordinator books the run by time (1 L in this host).
        """
        old = _unloadable(_coord(hass))
        _metered(old)
        _the_real_backstop_from_here(old)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _flow(hass, RATE)
            await _dispatch(hass, old, _metered_zone(600))
            await _walk(hass, frozen, 300)
            old._sc_sample_flow = Mock(wraps=old._sc_sample_flow)
            await old.async_unload()

            new = _coord(hass)
            new.store = old.store  # one store, as across a real reload
            _metered(new)
            _the_real_backstop_from_here(new)
            await new.async_resume_self_closing_runs()
            await hass.async_block_till_done()

            await _walk(hass, frozen, 300)  # 600: the valve closes
            await _flow(hass, 0)
            await _report(hass, "off", started + timedelta(seconds=600))
            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)
            await _walk(hass, frozen, 60)  # past where the old backstop was due

        assert await new._sc_find_run(2) is None
        new._record_run.assert_awaited_once()
        assert _litres(new) == 1.0
        old._record_run.assert_not_awaited()
        old._sc_sample_flow.assert_not_called()
        assert old._sc_meters() == {}
        assert old._sc_cleanup_timers() == {}

    async def test_a_run_ending_during_the_reload_waits_for_the_successor(self, hass):
        """The old backstop used to settle it through the dead coordinator."""
        old = _unloadable(_coord(hass))
        _the_real_backstop_from_here(old)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, old, _zone())
            await _advance(hass, frozen, 300)
            await old.async_unload()
            await _advance(hass, frozen, 400)  # 700: past plan and grace

            assert await old._sc_find_run(2) is not None
            old._record_run.assert_not_awaited()

            new = _coord(hass)
            new.store = old.store
            await new.async_resume_self_closing_runs()
            await hass.async_block_till_done()

        assert await new._sc_find_run(2) is None
        new._record_run.assert_awaited_once()
        assert new._record_run.await_args.kwargs["planned_s"] == 600
        old._record_run.assert_not_awaited()


# --------------------------------------------------------------------------- #
# The master's off timer goes with the coordinator
# --------------------------------------------------------------------------- #
class TestTheMasterOffTimerGoesWithTheCoordinator:
    """It closes over the coordinator and reads its holds when it fires."""

    async def test_release_all_cancels_a_pending_off(self, monkeypatch):
        """Left armed it read the emptied holds as "nothing running"."""
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        monkeypatch.setattr(
            "custom_components.irrigation_plus.master.async_call_later",
            Mock(return_value=cancel),
        )
        await c.async_master_acquire("sc:2")
        await c.async_master_release("sc:2")  # the last hold: the off timer
        assert c._master_off_cancel is cancel

        c._master_release_all()

        cancel.assert_called_once_with()
        assert c._master_off_cancel is None

    async def test_an_unload_leaves_no_off_timer_behind(self, hass):
        """On the real timer, scheduled while a hold was still taken.

        A distributor schedules the off while it still holds the master. The
        unload empties the holds, so a timer left armed read "nothing running"
        when it fired and switched the pump off, under whatever the next
        coordinator had started on it by then.
        """
        c = _unloadable(_coord(hass))
        _real_master(c, hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await c.async_master_acquire("dist:1")
            c._master_note_run(60)
            await c.async_master_schedule_off()
            assert c._master_off_cancel is not None

            await c.async_unload()
            await _advance(hass, frozen, 120)

        assert _pump_offs(calls) == []
        assert c._master_off_cancel is None
        assert c.master_holds() == set()

    async def test_the_boot_clean_up_switches_the_pump_off_once(self, hass):
        """The resume pass can arm the off timer before the clean-up runs.

        Settling a run that ended during the outage releases a hold this
        process never took, and that schedules the off. The clean-up switches
        the master off itself; the timer only did it again, five seconds later.
        """
        c = _coord(hass)
        _real_master(c, hass)
        c.store.async_get_distributors = AsyncMock(return_value=[])
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await c.async_master_release("sc:2")  # the resume pass, settling
            assert c._master_off_cancel is not None

            await c.async_reconcile_master_after_restart()
            await _advance(hass, frozen, 30)

        assert len(_pump_offs(calls)) == 1


# --------------------------------------------------------------------------- #
# Ending the master cycle at once
# --------------------------------------------------------------------------- #
def _cycle_ending(c, cancel):
    """A cycle whose last hold just went: master on, off timer pending."""
    c._master_on = True
    c._master_off_deadline = dt_util.utcnow() + timedelta(seconds=5)
    c._master_off_cancel = cancel


class TestEndingTheMasterCycleNow:
    """async_master_end_cycle_now: the end no timer is left to give the cycle."""

    async def test_a_master_we_switched_on_is_switched_off(self):
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        _cycle_ending(c, cancel)

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_awaited_once_with(
            "switch", "turn_off", {"entity_id": "switch.pump"}
        )
        cancel.assert_called_once_with()
        assert c._master_off_cancel is None
        assert c._master_on is False
        assert c._master_off_deadline is None

    async def test_a_stay_on_pump_is_left_on(self):
        c = _mcoord(master_off_after=False)
        cancel = Mock()
        _cycle_ending(c, cancel)

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        cancel.assert_called_once_with()
        assert c._master_off_cancel is None
        assert c._master_on is False
        assert c._master_off_deadline is None

    async def test_a_master_we_did_not_switch_on_is_left_alone(self):
        c = _mcoord(master_off_after=True)
        c._master_on = False

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()

    async def test_a_hold_still_taken_leaves_the_cycle_to_its_owner(self):
        """A classic run runs on as a task and ends the cycle as it releases."""
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        _cycle_ending(c, cancel)
        c._master_hold_set().add("seq:abcd1234")

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        cancel.assert_not_called()
        assert c._master_on is True

    async def test_without_a_master_nothing_happens(self):
        c = _mcoord(master_entity=None, master_off_after=True)
        c._master_on = True

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        assert c._master_on is True

    async def test_a_switch_that_raises_does_not_block_the_unload(self, caplog):
        """What reaches this call: the service call fails before dispatch."""
        c = _mcoord(master_off_after=True)
        _cycle_ending(c, Mock())
        c.hass.services.async_call = AsyncMock(
            side_effect=ServiceNotFound("switch", "turn_off")
        )

        await c.async_master_end_cycle_now()  # must not raise

        assert "Could not end the master cycle" in caplog.text
        assert "switch.pump" in caplog.text

    async def test_after_the_unload_a_removal_still_switches_it_off(self, monkeypatch):
        """A removal comes after the unload: no hold and no timer are left.

        Whether a cycle of ours is up rests on _master_on alone then.
        """
        c = _mcoord(master_off_after=True)
        monkeypatch.setattr(
            "custom_components.irrigation_plus.master.async_call_later",
            Mock(return_value=Mock()),
        )
        await c.async_master_acquire("sc:2")
        await c.async_master_release("sc:2")
        c._master_release_all()  # the unload
        c.hass.services.async_call.reset_mock()

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_awaited_once_with(
            "switch", "turn_off", {"entity_id": "switch.pump"}
        )


# --------------------------------------------------------------------------- #
# Releasing every chain
# --------------------------------------------------------------------------- #
class TestReleasingEveryChain:
    """A chain holds the master for its whole cycle, pauses included."""

    async def test_a_rotation_absorbing_between_slots_hands_back_its_hold(
        self, hass, caplog
    ):
        caplog.set_level(logging.INFO)
        c = _chain_coord(hass, ROTATING, slot=1, absorb=10)
        await _chain_dispatch(c, _register(c, _chain_zone(1, duration=180)))
        await _finish(c, 1)
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        token = state.token
        assert state.absorb is not None and token is not None

        await c.async_release_all_chains(DISABLED)

        assert state.absorb is None
        assert state.rotation is None
        assert state.token is None
        c.async_master_release.assert_any_await(token)
        assert DISABLED in caplog.text

    async def test_a_sequential_queue_starts_nothing_after_its_release(self, hass):
        c = _chain_coord(hass, SEQUENTIAL)
        await _chain_dispatch(c, _register(c, _chain_zone(1), _chain_zone(2)))
        assert _chain_ids(c) == [1]

        await c.async_release_all_chains(DISABLED)
        await _finish(c, 1)

        assert _chain_ids(c) == [1]
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == []

    async def test_an_idle_chain_releases_nothing(self, hass, caplog):
        """A finished cycle leaves its chain behind, empty and holding nothing."""
        c = _chain_coord(hass, SEQUENTIAL)
        await _chain_dispatch(c, _register(c, _chain_zone(1), _chain_zone(2)))
        await _finish(c, 1)
        await _finish(c, 2)
        c.async_master_release.reset_mock()
        caplog.clear()

        await c.async_release_all_chains(DISABLED)

        c.async_master_release.assert_not_awaited()
        assert DISABLED not in caplog.text

    @pytest.mark.parametrize("failing", [0, 1])
    async def test_one_chain_that_raises_does_not_stop_the_others(
        self, hass, caplog, failing
    ):
        c = _chain_coord(hass, SEQUENTIAL)
        c._chain_state(const.WATERING_MODE_SERVICE)
        c._chain_state(const.WATERING_MODE_OPENSPRINKLER)
        effects = [None, None]
        effects[failing] = RuntimeError("boom")
        c._chain_release = AsyncMock(side_effect=effects)

        await c.async_release_all_chains(DISABLED)  # must not raise

        assert [ck.args for ck in c._chain_release.await_args_list] == [
            (const.WATERING_MODE_SERVICE, DISABLED),
            (const.WATERING_MODE_OPENSPRINKLER, DISABLED),
        ]
        assert "Could not release" in caplog.text
        assert any(record.exc_info for record in caplog.records)


# --------------------------------------------------------------------------- #
# The stop instruction on its own
# --------------------------------------------------------------------------- #
class TestTheStopInstruction:
    async def test_the_stop_service_gets_a_zero_duration_under_its_field(self, hass):
        """The payload carries the run's zone id, not the id field of the zone."""
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)

        sent = await c._sc_dispatch_stop(7, _zone())
        await hass.async_block_till_done()

        assert sent is True
        assert _stops(calls) == [{"zone_id": 7, "dauer": 0}]

    @pytest.mark.parametrize(
        "unset", ["absent", None, ""], ids=["absent", "none", "empty"]
    )
    async def test_a_zone_without_a_stop_service_sends_nothing(self, hass, unset):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        zone = _zone()
        if unset == "absent":
            del zone[const.ZONE_STOP_SERVICE]
        else:
            zone[const.ZONE_STOP_SERVICE] = unset

        sent = await c._sc_dispatch_stop(2, zone)
        await hass.async_block_till_done()

        assert sent is False
        assert calls == []

    @pytest.mark.parametrize("with_stop_service", [True, False])
    async def test_an_opensprinkler_zone_stops_through_its_station(
        self, hass, with_stop_service
    ):
        """Never through the stop_service adapter, configured or not.

        opensprinkler.stop is entity-targeted and rejects the zone_id the
        adapter sends.
        """
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        c._os_dispatch_stop = AsyncMock()
        zone = _zone(**{const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER})
        if not with_stop_service:
            del zone[const.ZONE_STOP_SERVICE]

        sent = await c._sc_dispatch_stop(2, zone)
        await hass.async_block_till_done()

        assert sent is True
        c._os_dispatch_stop.assert_awaited_once_with(zone)
        assert _stops(calls) == []


# --------------------------------------------------------------------------- #
# Aborting the service runs
# --------------------------------------------------------------------------- #
async def _a_run_halfway(hass, c, frozen, zone=None):
    await _dispatch(hass, c, zone or _zone())
    await _advance(hass, frozen, 300)


class TestAbortingTheServiceRuns:
    """The service twin of async_abort_opensprinkler_runs."""

    async def test_a_service_run_is_stopped_and_settled(self, hass, caplog):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen)
            stopped = await c.async_abort_self_closing_runs(DISABLED)
            await hass.async_block_till_done()

        assert stopped is True
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(300, abs=1)
        c.async_master_release.assert_awaited_once_with("sc:2")
        assert "without a stop_service" not in caplog.text  # it was closed

    async def test_a_record_without_a_mode_is_a_service_run(self, hass):
        """The resume path reads it as one, so the abort does too."""
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        c._zones[2] = _zone()
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {
                const.RUN_ZONE_ID: 2,
                const.RUN_PLANNED_SECONDS: 600,
                const.RUN_PLANNED_MM: 10.0,
                const.RUN_STARTED: dt_util.utcnow().isoformat(),
                const.RUN_PRE_BUCKET: -20.0,
            }
        ]

        assert await c.async_abort_self_closing_runs(DISABLED) is True
        await hass.async_block_till_done()

        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is None

    async def test_opensprinkler_and_batch_runs_are_left_to_their_own_abort(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        runs = [
            {const.RUN_ZONE_ID: 5, const.RUN_MODE: const.WATERING_MODE_OPENSPRINKLER},
            {const.RUN_ZONE_ID: 6, const.RUN_MODE: const.WATERING_MODE_BATCH},
        ]
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [dict(r) for r in runs]
        c._chain_release = AsyncMock()

        assert await c.async_abort_self_closing_runs(DISABLED) is False
        await hass.async_block_till_done()

        assert calls == []
        assert c._cfg[const.CONF_ACTIVE_VALVE_RUNS] == runs
        c._chain_release.assert_not_awaited()

    async def test_the_chain_is_released_before_the_first_stop(self, hass):
        """Otherwise the settled stop advances the chain and opens the next zone."""
        c = _coord(hass)
        c.store.config.zone_sequencing = SEQUENTIAL
        c.store.config.zone_sequencing_max_consecutive_duration = 5
        c.store.config.zone_sequencing_min_absorption_time = 0
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        first, second = _zone(), _zone(3, confirm=None)
        c._zones[2], c._zones[3] = first, second
        await _set(hass, VALVE, "on")
        await c.async_dispatch_chained_zones(
            [first, second], mode=const.WATERING_MODE_SERVICE, trigger="schedule"
        )
        await hass.async_block_till_done()
        assert _opened(calls) == [2]

        await c.async_abort_self_closing_runs(DISABLED)
        await hass.async_block_till_done()

        assert _opened(calls) == [2]
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == []

    async def test_without_settling_only_the_stop_goes_out(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen)
            stopped = await c.async_abort_self_closing_runs(REMOVED, settle=False)
            await hass.async_block_till_done()

        assert stopped is True
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is not None  # the store is deleted next
        c._record_run.assert_not_awaited()
        c.async_master_release.assert_not_awaited()
        c._watch_cancel(2)  # the run's watcher, still armed

    async def test_a_zone_without_a_stop_service_is_still_settled(self, hass, caplog):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        zone = _zone()
        del zone[const.ZONE_STOP_SERVICE]
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen, zone)
            assert await c.async_abort_self_closing_runs(DISABLED) is True
            await hass.async_block_till_done()

        assert _stops(calls) == []
        assert c._record_run.await_args.kwargs["result"] == const.RUN_RESULT_PARTIAL
        assert "without a stop_service" in caplog.text

    async def test_a_stop_that_raises_does_not_stop_the_rest(self, hass, caplog):
        c = _coord(hass)
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {const.RUN_ZONE_ID: 2, const.RUN_MODE: const.WATERING_MODE_SERVICE},
            {const.RUN_ZONE_ID: 4, const.RUN_MODE: const.WATERING_MODE_SERVICE},
        ]
        c.async_stop_self_closing = AsyncMock(side_effect=[RuntimeError("boom"), True])

        assert await c.async_abort_self_closing_runs(DISABLED) is True

        stopped = [ck.args[0] for ck in c.async_stop_self_closing.await_args_list]
        assert stopped == [2, 4]
        assert "could not stop its self-closing run" in caplog.text

    async def test_an_unreadable_store_stops_nothing_and_does_not_raise(
        self, hass, caplog
    ):
        c = _coord(hass)
        c.store.async_get_config = AsyncMock(side_effect=RuntimeError("store gone"))

        assert await c.async_abort_self_closing_runs(DISABLED) is False

        assert "Could not read active runs" in caplog.text

    async def test_nothing_in_flight_stops_nothing(self, hass):
        c = _coord(hass)

        assert await c.async_abort_self_closing_runs(DISABLED) is False

    async def test_without_settling_a_zone_without_a_stop_service_is_named(
        self, hass, caplog
    ):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        zone = _zone()
        del zone[const.ZONE_STOP_SERVICE]
        c._zones[2] = zone
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {const.RUN_ZONE_ID: 2, const.RUN_MODE: const.WATERING_MODE_SERVICE}
        ]

        assert await c.async_abort_self_closing_runs(REMOVED, settle=False) is False
        await hass.async_block_till_done()

        assert _stops(calls) == []
        assert "has no stop_service" in caplog.text

    async def test_a_chain_that_cannot_be_released_stops_nothing(self, hass, caplog):
        """A settle could then dispatch the chain's next zone on the way out."""
        c = _coord(hass)
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {const.RUN_ZONE_ID: 2, const.RUN_MODE: const.WATERING_MODE_SERVICE}
        ]
        c._chain_release = AsyncMock(side_effect=RuntimeError("boom"))
        c.async_stop_self_closing = AsyncMock()

        assert await c.async_abort_self_closing_runs(DISABLED) is False  # no raise

        c.async_stop_self_closing.assert_not_awaited()
        assert "Could not release the service chain" in caplog.text


# --------------------------------------------------------------------------- #
# The entry paths
# --------------------------------------------------------------------------- #
def _steps(coordinator):
    """Each call on the mock coordinator, with its arguments, in order."""
    return [(name, args, kwargs) for name, args, kwargs in coordinator.mock_calls]


class TestTheEntryPaths:
    """Which unload stops what, and in which order (mock coordinator)."""

    @staticmethod
    def _coordinator(hass):
        coordinator = AsyncMock()
        hass.data[const.DOMAIN] = {"coordinator": coordinator}
        return coordinator

    async def test_a_reload_stops_nothing(self, hass, mock_config_entry):
        """A pin: green before the change too. The successor adopts the runs."""
        coordinator = self._coordinator(hass)
        panel, forward = _unload_patches(hass)
        with panel, forward:
            assert await async_unload_entry(hass, mock_config_entry) is True

        assert _called(coordinator) == ["async_unload"]

    async def test_disabling_stops_everything_before_the_unload(
        self, hass, mock_config_entry
    ):
        """Every abort settles: the master's end relies on the holds they free."""
        coordinator = self._coordinator(hass)
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        panel, forward = _unload_patches(hass)
        with panel, forward:
            assert await async_unload_entry(hass, mock_config_entry) is True

        assert _steps(coordinator) == [
            ("async_release_all_chains", (DISABLED,), {}),
            ("async_abort_opensprinkler_runs", (DISABLED,), {}),
            ("async_abort_batch_runs", (DISABLED,), {}),
            ("async_abort_self_closing_runs", (DISABLED,), {}),
            ("async_master_end_cycle_now", (), {}),
            ("async_unload", (), {}),
        ]

    async def test_removal_stops_without_settling_before_the_delete(
        self, hass, mock_config_entry
    ):
        """Nothing is written to the store about to be deleted."""
        coordinator = self._coordinator(hass)
        with (
            patch("custom_components.irrigation_plus.remove_panel"),
            patch(
                "custom_components.irrigation_plus.async_remove_card_resource",
                new=AsyncMock(),
            ),
        ):
            await async_remove_entry(hass, mock_config_entry)

        assert _steps(coordinator) == [
            ("async_abort_opensprinkler_runs", (REMOVED,), {"settle": False}),
            ("async_abort_batch_runs", (REMOVED,), {"settle": False}),
            ("async_abort_self_closing_runs", (REMOVED,), {"settle": False}),
            ("async_master_end_cycle_now", (), {}),
            ("async_delete_config", (), {}),
        ]


class TestDisablingMidRun:
    """The whole disable, through async_unload_entry, on the real hass."""

    @pytest.mark.parametrize(("off_after", "pump_offs"), [(True, 1), (False, 0)])
    async def test_the_run_is_stopped_and_booked_and_the_cycle_ended(
        self, hass, mock_config_entry, off_after, pump_offs
    ):
        """600 s plan, a queued second zone, disabled at 300 s.

        Measured 50 L (10 L/min for 300 s): not the 1 L this host books by
        time, not the 100 L of the plan. The queued zone never opens, and the
        pump goes off only if it is set to go off after its runs.
        """
        c = _unloadable(_coord(hass))
        _metered(c)
        _the_real_backstop_from_here(c)
        _real_master(c, hass, off_after=off_after)
        c.store.config.zone_sequencing = SEQUENTIAL
        c.store.config.zone_sequencing_max_consecutive_duration = 5
        c.store.config.zone_sequencing_min_absorption_time = 0
        hass.data[const.DOMAIN] = {"coordinator": c}
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        first, second = _metered_zone(600), _zone(3, confirm=None)
        c._zones[2], c._zones[3] = first, second
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _flow(hass, RATE)
            await _set(hass, VALVE, "on")
            await c.async_dispatch_chained_zones(
                [first, second], mode=const.WATERING_MODE_SERVICE, trigger="schedule"
            )
            await hass.async_block_till_done()
            await _walk(hass, frozen, 300)
            panel, forward = _unload_patches(hass)
            with panel, forward:
                assert await async_unload_entry(hass, mock_config_entry) is True
            await hass.async_block_till_done()
            await _walk(hass, frozen, 600)  # past the plan, any grace, any off timer

        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        c._record_run.assert_awaited_once()
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["volume_l"] == pytest.approx(RATE * 300 / 60, abs=0.01)
        assert _opened(calls) == [2]
        assert len(_pump_offs(calls)) == pump_offs
        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}

    async def test_a_disable_in_an_absorption_pause_switches_the_pump_off(
        self, hass, mock_config_entry
    ):
        """No run in flight, so no abort releases the chain; its hold would stay."""
        c = _unloadable(_chain_coord(hass, ROTATING, slot=1, absorb=10))
        _real_master(c, hass)
        hass.data[const.DOMAIN] = {"coordinator": c}
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _chain_dispatch(c, _register(c, _chain_zone(1, duration=180)))
            await _finish(c, 1)
            state = c._chain_state(const.WATERING_MODE_SERVICE)
            assert state.absorb is not None and state.token is not None

            panel, forward = _unload_patches(hass)
            with panel, forward:
                assert await async_unload_entry(hass, mock_config_entry) is True
            await hass.async_block_till_done()
            await _advance(hass, frozen, 700)  # past the 600 s absorption wait

        assert state.absorb is None and state.token is None
        assert len(_pump_offs(calls)) == 1
        assert _chain_ids(c) == [1]  # no second slot


class TestRemovingMidRun:
    """Home Assistant unloads first, then removes the entry: on the real hass."""

    async def test_the_valve_is_closed_and_the_pump_switched_off(
        self, hass, mock_config_entry
    ):
        """Nothing is booked, and the pump goes off after the valve's stop.

        The plain unload drops the run's hold without releasing it, so only
        async_master_end_cycle_now ends the master's cycle.
        """
        c = _unloadable(_coord(hass))
        _metered(c)
        _the_real_backstop_from_here(c)
        _real_master(c, hass)
        c.store.config.zone_sequencing = SEQUENTIAL
        c.store.config.zone_sequencing_max_consecutive_duration = 5
        c.store.config.zone_sequencing_min_absorption_time = 0
        c.store.async_delete = AsyncMock()
        hass.data[const.DOMAIN] = {"coordinator": c}
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        first, second = _metered_zone(600), _zone(3, confirm=None)
        c._zones[2], c._zones[3] = first, second
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _flow(hass, RATE)
            await _set(hass, VALVE, "on")
            await c.async_dispatch_chained_zones(
                [first, second], mode=const.WATERING_MODE_SERVICE, trigger="schedule"
            )
            await hass.async_block_till_done()
            await _walk(hass, frozen, 300)
            panel, forward = _unload_patches(hass)
            with panel, forward:
                assert await async_unload_entry(hass, mock_config_entry) is True
            with (
                patch("custom_components.irrigation_plus.remove_panel"),
                patch(
                    "custom_components.irrigation_plus.async_remove_card_resource",
                    new=AsyncMock(),
                ),
            ):
                await async_remove_entry(hass, mock_config_entry)
            await hass.async_block_till_done()
            await _walk(hass, frozen, 600)

        services = [e.data["service"] for e in calls]
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        c._record_run.assert_not_awaited()
        assert _opened(calls) == [2]
        assert len(_pump_offs(calls)) == 1
        assert services.index("stop_irrigation_beet") < services.index("turn_off")
        c.store.async_delete.assert_awaited_once()
