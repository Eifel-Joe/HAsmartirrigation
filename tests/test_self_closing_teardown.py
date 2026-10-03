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
    async_fire_time_changed,
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
