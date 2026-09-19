"""A confirmed service valve is watched for the rest of its run (issue #88).

``confirm_entity`` used to be read exactly once, at open, and nothing subscribed
to it afterwards. So a valve that shut mid-run -- a Zigbee dropout, a hardware
fault, someone closing it by hand -- left the wall clock running: the run was
recorded as ``actual_s == planned_s``, ``completed``, with its full optimistic
credit standing, and the next calculation went on believing the zone had been
watered. Reported by Eifel-Joe, who runs three service zones on a cistern pump.

Batch mode already had this accounting, because it promotes the same entity to a
watch entity. Service mode now registers its own ``WatchPolicy`` on the shared
engine rather than growing a second copy of the lifecycle.

Driven against the real ``hass`` fixture, for the reason the batch and
OpenSprinkler suites are: the feature IS a state subscription, and a double
replaces exactly the thing under test.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const

VALVE = "binary_sensor.beet_valve"


def _coord(hass):
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    c.hass = hass
    c.store = Mock()
    c._cfg = {}
    c._zones = {}
    c.store.async_get_config = AsyncMock(side_effect=lambda: dict(c._cfg))
    c.store.async_update_config = AsyncMock(side_effect=c._cfg.update)
    c.store.async_update_zone = AsyncMock()
    c.store.get_zone = Mock(side_effect=lambda zid: c._zones.get(int(zid)))
    c.store.config = Mock()
    c.store.config.master_entity = None
    c._record_run = AsyncMock()
    c._set_zone_fault = Mock()
    c._fire_zone_problem = Mock()
    c._note_si_valve = Mock()
    c.async_master_acquire = AsyncMock()
    c.async_master_release = AsyncMock()
    c.async_run_deferred_calculation = AsyncMock()
    c.async_write_watered_bucket = AsyncMock()
    c._stamp_run_finalized = AsyncMock()
    c._timed_volume_l = Mock(return_value=100.0)
    c._credited_depth_native = Mock(return_value=20.0)
    c._flow_calibration_check = AsyncMock()
    c._sc_start_flow_sampling = AsyncMock()
    c._sc_finish_flow = Mock(return_value=(None, {}))
    c._sc_schedule_cleanup = Mock()
    c._sc_cancel_cleanup = Mock()
    c._os_cancel_watch = Mock()
    c._os_chain_advance = AsyncMock()
    async_mock_service(hass, "script", "irrigation_beet")
    async_mock_service(hass, "script", "stop_irrigation_beet")
    return c


def _zone(zone_id=2, confirm=VALVE, duration=600, **kw):
    z = {
        const.ZONE_ID: zone_id,
        const.ZONE_NAME: "Beet",
        const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        const.ZONE_RUN_SERVICE: "script.irrigation_beet",
        const.ZONE_STOP_SERVICE: "script.stop_irrigation_beet",
        const.ZONE_DURATION_FIELD: "dauer",
        const.ZONE_DURATION_UNIT: const.DURATION_UNIT_SECONDS,
        const.ZONE_DURATION: duration,
        const.ZONE_BUCKET: -20.0,
        const.ZONE_MAXIMUM_BUCKET: 50.0,
    }
    if confirm is not None:
        z[const.ZONE_CONFIRM_ENTITY] = confirm
    z.update(kw)
    return z


async def _set(hass, entity, state):
    hass.states.async_set(entity, state)
    await hass.async_block_till_done()


async def _settle(hass):
    """Run out the window a valve-off is held open in, in case it was a blip.

    Assertions about the end of a run are only meaningful once this has passed:
    before it, the run is un-settled whether the off was real or not.
    """
    async_fire_time_changed(
        hass,
        dt_util.utcnow() + timedelta(seconds=const.SERVICE_WATCH_SETTLE_SECONDS + 1),
    )
    await hass.async_block_till_done()


async def _off(hass):
    """The valve stops, and stays stopped."""
    await _set(hass, VALVE, "off")
    await _settle(hass)


async def _dispatch(hass, c, zone, *, valve_state="on"):
    c._zones[int(zone[const.ZONE_ID])] = zone
    if zone.get(const.ZONE_CONFIRM_ENTITY):
        await _set(hass, zone[const.ZONE_CONFIRM_ENTITY], valve_state)
    ok = await c.async_run_self_closing(zone, trigger="schedule")
    await hass.async_block_till_done()
    return ok


class TestAValveThatShutsMidRunEndsTheRun:
    async def test_the_run_is_recorded_for_what_it_actually_watered(self, hass):
        c = _coord(hass)
        started = dt_util.utcnow()
        await _dispatch(hass, c, _zone())

        # 100 s in, the valve drops out
        with freeze_time(started + timedelta(seconds=100)):
            await _off(hass)

        c._record_run.assert_awaited()
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["planned_s"] == 600
        assert 90 <= kw["actual_s"] <= 110  # not the full window

    async def test_the_optimistic_credit_is_reconciled_down(self, hass):
        c = _coord(hass)
        started = dt_util.utcnow()
        await _dispatch(hass, c, _zone())

        with freeze_time(started + timedelta(seconds=300)):
            await _off(hass)

        # 20 mm was credited at dispatch from a -20 mm bucket; half the window ran,
        # so half of it has to come back off.
        written = [ck.args[1] for ck in c.async_write_watered_bucket.await_args_list]
        # approx: the elapsed is real wall clock, so the dispatch's own microseconds
        # are in it. The point is the half, not the millisecond.
        assert written[-1] == pytest.approx(-10.0, abs=0.01)

    async def test_the_run_no_longer_holds_the_zone(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        assert await c._sc_find_run(2) is not None

        await _off(hass)

        assert await c._sc_find_run(2) is None

    async def test_the_master_hold_is_dropped_with_it(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c.async_master_release.reset_mock()

        await _off(hass)

        c.async_master_release.assert_awaited()


class TestAFullRunIsStillAFullRun:
    async def test_a_valve_off_at_the_planned_end_completes(self, hass):
        """Completed, and recorded for the window the valve reported (#139).

        actual_s is now the off report minus the on report rather than planned_s.
        The dispatch runs under the same frozen clock as the close, so the on
        report (clamped to the dispatch) is ``started`` exactly and a close at
        the planned end is a window of exactly 600 s.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())

            frozen.tick(timedelta(seconds=600))
            await _off(hass)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600

    async def test_the_observed_start_is_the_dispatch_instant(self, hass):
        """Not the moment the observation arrived.

        The confirm poll runs BEFORE the watcher is armed, so anchoring the run to
        when the subscription first saw the valve would shorten every run by that
        poll -- and settle a full one as a partial, with its credit reversed.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        run = await c._sc_find_run(2)
        assert run[const.RUN_OBSERVED_START] == run[const.RUN_STARTED]

    async def test_the_flow_meter_is_not_re_seeded_by_the_observation(self, hass):
        """It was started at dispatch, for the window that actually began.

        Re-seeding it at the observed start would throw away everything sampled
        since. The engine does that because a QUEUED run's dispatch precedes its
        water by hours -- which is not true of a valve that opens as it is told.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        c._sc_start_flow_sampling.assert_awaited_once()

    async def test_the_finish_backstop_is_armed_once(self, hass):
        """Re-arming it from the observation would push it past the real close.

        Armed once, at dispatch, and already carrying a confirmed run's finish
        grace: the planned 600 s plus the 5 s debounce plus the default 4 s
        latency margin (#139). Armed at exactly the window, it beat the valve's
        own off report on every normal run.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        assert c._sc_schedule_cleanup.call_count == 1
        assert c._sc_schedule_cleanup.call_args.args == (2, 609)


class TestAConfirmedRunFreezesItsMarginAtDispatch:
    """The margin a run waits for is the one it was dispatched under (#139).

    Frozen into the record, so a margin edited mid-run cannot move a backstop
    that is already armed, and so a record without it (write-only, unverifiable,
    or persisted before this change) keeps the timing it started with.
    """

    async def test_the_default_margin_is_frozen_into_the_record(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        run = await c._sc_find_run(2)
        assert run[const.RUN_LATENCY_MARGIN] == 4

    async def test_the_zones_own_margin_is_frozen_into_the_record(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 7}))

        run = await c._sc_find_run(2)
        assert run[const.RUN_LATENCY_MARGIN] == 7

    async def test_a_write_only_run_carries_neither_margin_nor_valve_on(self, hass):
        """No confirm_entity: nothing reports the valve, nothing to wait for."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone(confirm=None))

        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert const.RUN_VALVE_ON not in run

    async def test_an_unverifiable_run_carries_neither_margin_nor_valve_on(self, hass):
        """A confirm of None is "cannot verify": the run stays write-only."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert const.RUN_VALVE_ON not in run


class TestTheValveOnReportIsClampedToTheDispatch:
    """RUN_VALVE_ON is the valve's own on report, never older than the dispatch.

    RUN_STARTED is stamped after the confirm poll returns, up to a poll after
    the water started. The valve's last_changed is closer, but a valve that was
    already open before the dispatch would drag the anchor back by however long
    it had been open, so the report is clamped to [dispatch, confirm return].
    """

    async def test_a_valve_already_open_is_anchored_at_the_dispatch(self, hass):
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started):
            c = _coord(hass)
            zone = _zone()
            c._zones[2] = zone
            # on for an hour already: the confirm poll accepts it at first read
            hass.states.async_set(
                VALVE, "on", timestamp=(started - timedelta(hours=1)).timestamp()
            )
            await hass.async_block_till_done()

            assert await c.async_run_self_closing(zone, trigger="schedule")
            await hass.async_block_till_done()

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == started.isoformat()

    async def test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report(
        self, hass
    ):
        started = dt_util.utcnow().replace(microsecond=0)
        reported = started + timedelta(seconds=0.4)
        with freeze_time(started) as frozen:
            c = _coord(hass)
            zone = _zone()

            async def _slow_confirm(zone_id, entity_id, retry=True):
                # the valve reports on 0.4 s after the dispatch, and the poll
                # that sees it returns a whole second after the dispatch
                hass.states.async_set(entity_id, "on", timestamp=reported.timestamp())
                frozen.tick(timedelta(seconds=1))
                return True

            c._confirm_valve_running = AsyncMock(side_effect=_slow_confirm)
            await _dispatch(hass, c, zone, valve_state="off")

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == reported.isoformat()
        assert run[const.RUN_STARTED] == (started + timedelta(seconds=1)).isoformat()

    async def test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it(
        self, hass
    ):
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            c = _coord(hass)
            zone = _zone()

            async def _skewed_confirm(zone_id, entity_id, retry=True):
                stamp = (started + timedelta(seconds=5)).timestamp()
                hass.states.async_set(entity_id, "on", timestamp=stamp)
                frozen.tick(timedelta(seconds=1))
                return True

            c._confirm_valve_running = AsyncMock(side_effect=_skewed_confirm)
            await _dispatch(hass, c, zone, valve_state="off")

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == (started + timedelta(seconds=1)).isoformat()


class TestTheBackstopWaitsOnlyForAConfirmedValve:
    async def test_a_margin_of_zero_still_waits_out_the_debounce(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}))

        assert c._sc_schedule_cleanup.call_args.args == (2, 605)

    async def test_a_write_only_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(confirm=None))

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)

    async def test_an_unverifiable_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)


def _finished(hass):
    """Capture the irrigation_finished events the coordinator fires."""
    return async_capture_events(hass, f"{const.DOMAIN}_{const.EVENT_IRRIGATE_FINISHED}")


def _the_real_backstop_from_here(c):
    """Swap _coord's backstop double for the real timer, its calls still recorded.

    With the double a test reads the delay the backstop is armed with but never
    sees it fire, so it cannot show whether the backstop or a debounce comes
    first, nor what the backstop settles when it does. Dropping the instance
    doubles falls back to the coordinator's own _sc_schedule_cleanup and
    _sc_cancel_cleanup; wrapping the first keeps its calls assertable. Only a
    backstop armed after the call is real, so it is called before the dispatch
    (or the restart) whose backstop the test is about.
    """
    del c._sc_schedule_cleanup
    del c._sc_cancel_cleanup
    c._sc_schedule_cleanup = Mock(wraps=c._sc_schedule_cleanup)


class TestAMissedCloseStillSettlesViaTheBackstop:
    """A close the valve never reports is still finished, by the backstop (#139).

    The watcher settles a confirmed run on the valve's own reports. When the
    off report never comes (the close was missed, or its report was lost), the
    backstop is what ends the run, as it always was, only now at the end of the
    finish grace, planned + debounce + margin, rather than at the planned end.
    The delay it is armed with is pinned above on the double; here it is the
    real timer, so the test sees when it fires and what it settles.
    """

    async def test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out(
        self, hass
    ):
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        finished = _finished(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 4}))

            frozen.tick(timedelta(seconds=608))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()

            # 608 s: past the plan, a second short of the grace (600 + 5 + 4)
            assert await c._sc_find_run(2) is not None
            c._record_run.assert_not_awaited()
            assert not finished
            c.async_master_release.assert_not_awaited()

            frozen.tick(timedelta(seconds=2))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()

        # 610 s: the backstop, due at 609, has finished the run for its plan
        assert await c._sc_find_run(2) is None
        c._record_run.assert_awaited_once()
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600
        assert len(finished) == 1
        c.async_master_release.assert_awaited_once()
        assert not c._sc_cleanup_timers()  # nothing left armed


class TestTheWatcherNeverWritesAWateringRunOff:
    async def test_an_unavailable_valve_does_not_end_the_run(self, hass):
        """No information is not "the run stopped"."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _set(hass, VALVE, "unavailable")

        assert await c._sc_find_run(2) is not None
        c._record_run.assert_not_awaited()

    async def test_no_give_up_clock_is_armed(self, hass):
        """A service run has no queue to wait behind -- nothing to give up on.

        A give-up clock here could only ever fire against a run that IS watering,
        reversing its credit and raising a fault while the water flowed. That is
        the defect ``arm_give_up_after_start`` documents, reached by a different
        door.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        await _set(hass, VALVE, "unavailable")

        async_fire_time_changed(
            hass,
            dt_util.utcnow()
            + timedelta(seconds=const.SERVICE_WATCH_GIVE_UP_SECONDS + 30),
        )
        await hass.async_block_till_done()

        assert await c._sc_find_run(2) is not None
        c._set_zone_fault.assert_not_called()


class TestOneOffSampleIsNotEvidenceTheWaterStopped:
    """These are the valves ``_confirm_valve_running`` is written around.

    Its own docstring: sleepy Zigbee/Tuya timers "actuate but report their new
    state back slowly, or silently drop the first command". Ending a run on the
    first `off` would settle those as partials and reverse the credit for water
    that never stopped flowing — trading the defect this feature fixes for a
    worse one on the same hardware.
    """

    async def test_a_valve_that_blips_off_and_back_on_keeps_its_run(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _set(hass, VALVE, "off")
        await _set(hass, VALVE, "on")  # back before the window is out
        await _settle(hass)

        assert await c._sc_find_run(2) is not None
        c._record_run.assert_not_awaited()

    async def test_the_run_is_not_settled_before_the_window_is_out(self, hass):
        """Held open, not finished — the decision is genuinely deferred."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _set(hass, VALVE, "off")

        assert await c._sc_find_run(2) is not None
        c._record_run.assert_not_awaited()

    async def test_a_valve_that_stays_off_still_ends_the_run(self, hass):
        """The debounce is a debounce, not a licence to ignore the valve."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _off(hass)

        assert await c._sc_find_run(2) is None


async def _report(hass, state, when, attributes=None):
    """The valve reports ``state``, stamped ``when`` (the state's last_changed)."""
    hass.states.async_set(VALVE, state, attributes, timestamp=when.timestamp())
    await hass.async_block_till_done()


class TestTheWatcherRecordsTheValvesOwnOffReport:
    """RUN_VALVE_OFF is the first off report since the last on (#139).

    Read off the event's state.last_changed rather than stamped when the
    watcher gets round to it: the evaluate runs as a task, a poll or more after
    the report, and every later off update of the same valve (an attribute
    refresh, a link-quality tick) is an event of its own that would move a
    clock-stamped value. Recorded only from an event whose previous state was
    running: an off that follows unavailable, unknown or no state the watcher
    saw carries the entity's return in its last_changed, not the close. Each
    test asserts before the debounce runs out: the report is recorded at the
    event, not when the run is settled.
    """

    async def test_an_off_event_records_the_states_last_changed(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        c._record_run.assert_not_awaited()
        await _settle(hass)

    async def test_an_attribute_only_update_does_not_move_the_off_report(self, hass):
        """HA keeps last_changed while the state text stays the same."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)
        await _report(hass, "off", closed + timedelta(seconds=3), {"linkquality": 42})

        state = hass.states.get(VALVE)
        assert state.last_changed == closed
        assert state.last_updated == closed + timedelta(seconds=3)
        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        await _settle(hass)

    async def test_an_off_after_an_unavailable_spell_keeps_the_first_off_report(
        self, hass
    ):
        """unavailable is no information, not an on: the valve closed at the first.

        The first off follows the on and is the close. The off after the spell
        follows unavailable, not a running state, and moves nothing.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)
        await _report(hass, "unavailable", closed + timedelta(seconds=1))
        await _report(hass, "off", closed + timedelta(seconds=2))

        assert hass.states.get(VALVE).last_changed == closed + timedelta(seconds=2)
        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        await _settle(hass)

    async def test_an_off_after_an_unavailable_mid_run_records_nothing(self, hass):
        """on -> unavailable -> off: the off does not follow a running state.

        Its last_changed is when the entity came back, which can be any time
        after the valve really closed. Nothing is recorded, and the run is
        settled like any close nobody reported (accepted trade-off, #139).
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        now = dt_util.utcnow().replace(microsecond=0)

        await _report(hass, "unavailable", now + timedelta(seconds=1))
        await _report(hass, "off", now + timedelta(seconds=3))

        # the off was evaluated: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_an_on_inside_the_debounce_clears_the_off_report(self, hass):
        """A blip is not a close: the next off starts a fresh window end."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)
        await _report(hass, "off", closed)
        assert (await c._sc_find_run(2))[const.RUN_VALVE_OFF] == closed.isoformat()

        await _report(hass, "on", closed + timedelta(seconds=1))

        run = await c._sc_find_run(2)
        assert run is not None
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)
        assert await c._sc_find_run(2) is not None
        c._record_run.assert_not_awaited()

    async def test_a_re_adopted_run_does_not_record_the_initial_off(self, hass):
        """After a restart last_changed is the entity's return, not the close.

        The watcher re-adopting the run evaluates the valve once, and finds it
        off. That evaluation must not stamp RUN_VALVE_OFF: the state it reads
        was restored when the entity came back, so its last_changed can be any
        time after the real close.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}  # the subscription lived in memory only
        await _report(
            hass, "off", dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2)
        )

        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        # the initial evaluate did see the off: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_a_re_adopted_run_does_not_record_an_off_after_unavailable(
        self, hass
    ):
        """The valve is unavailable when the run is re-adopted, then reports off.

        After a restart a Zigbee valve comes back as unavailable first. The off
        that follows is the first report the new subscription sees, but its
        previous state is unavailable: its last_changed is the entity's return,
        not the close.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._watch_cancel(2)  # the subscription lived in memory only
        now = dt_util.utcnow().replace(microsecond=0)
        await _report(hass, "unavailable", now + timedelta(seconds=1))

        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()
        assert c._watchers()[2].finish_cancel is None  # unavailable: no information

        await _report(hass, "off", now + timedelta(seconds=3))

        # the off was evaluated: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_a_record_from_before_the_update_records_nothing(self, hass):
        """No frozen margin, no finish grace: the run keeps the timing it had."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        for record in c._cfg[const.CONF_ACTIVE_VALVE_RUNS]:
            del record[const.RUN_LATENCY_MARGIN]

        await _report(
            hass, "off", dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2)
        )

        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)


async def _advance(hass, frozen, seconds):
    """Move the frozen clock on by ``seconds`` and fire every timer now due."""
    frozen.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def _run_until_the_valve_closes(hass, c, zone, closed_after, *, before=None):
    """Dispatch, report the valve off ``closed_after`` s later, run out the debounce.

    All under one frozen clock: RUN_VALVE_ON is then the dispatch instant
    exactly, and the debounce timer is armed on the clock it is advanced on.
    The clock stands AT the close when the off is reported (stamped with that
    instant explicitly) and is moved PAST the debounce before the timer fires,
    so a run measured when the decision is taken, rather than at the off
    report, comes out visibly longer. ``before`` runs after the dispatch and
    before the close.
    """
    started = dt_util.utcnow().replace(microsecond=0)
    with freeze_time(started) as frozen:
        await _dispatch(hass, c, zone)
        if before is not None:
            before()
        frozen.tick(timedelta(seconds=closed_after))
        await _report(hass, "off", started + timedelta(seconds=closed_after))
        await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)


class TestAConfirmedRunIsSettledOnItsValveWindow:
    """The debounce decides WHETHER the run ended; the reports say how long (#139).

    actual_s is the valve's off report minus its on report, and a close within
    the zone's latency margin of the planned end still completes. Before, the
    elapsed time was read when the debounce expired, 5 s after the close, and a
    completed run discarded it for planned_s, so neither the late Tuya close nor
    an early one was ever recorded as what the valve did.

    Only a close the valve reported is settled that way. With no off report on
    record the one clock left is read after the debounce, and the margin as a
    tolerance on it would let a close nobody reported complete up to debounce +
    margin short of the plan; such a run keeps the old rule.
    """

    async def test_a_close_just_after_the_window_completes_on_the_reported_window(
        self, hass
    ):
        """The Beet valve: it reports its close 2-3 s after the planned end."""
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 602)

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["planned_s"] == 600
        assert kw["actual_s"] == pytest.approx(602, abs=0.01)  # not 608, not 600
        # Only the recorded duration moves: the timed volume and the calibration
        # sample stay on the window the run was credited and sized for.
        assert c._timed_volume_l.call_args.args[1] == 600
        c._flow_calibration_check.assert_awaited_once()
        assert c._flow_calibration_check.await_args.args[2] == 600

    async def test_a_close_inside_the_margin_completes_on_the_reported_window(
        self, hass
    ):
        """3 s short with the default 4 s margin: a normal end, not a stop."""
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 597)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == pytest.approx(597, abs=0.01)

    async def test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window(
        self, hass
    ):
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 590)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(590, abs=0.01)  # not 596
        # 20 mm credited at dispatch from -20 mm; 590 of 600 s were delivered
        written = [ck.args[1] for ck in c.async_write_watered_bucket.await_args_list]
        assert written[-1] == pytest.approx(-20 + 20 * 590 / 600, abs=0.001)

    async def test_a_margin_of_zero_still_tolerates_one_second(self, hass):
        """max(1, margin): the old one-second slack is the floor, not the margin."""
        c = _coord(hass)

        await _run_until_the_valve_closes(
            hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}), 599.5
        )

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == pytest.approx(599.5, abs=0.01)

    async def test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial(
        self, hass
    ):
        c = _coord(hass)

        await _run_until_the_valve_closes(
            hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}), 598.5
        )

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(598.5, abs=0.01)

    async def test_an_off_after_an_unavailable_mid_run_keeps_the_old_rule(self, hass):
        """on -> unavailable -> off mid-run: no off report, so the old rule settles.

        The off at +302 s follows unavailable, so its last_changed is the
        entity's return and not the close, and nothing is recorded. The run is
        settled like any close nobody reported: on its elapsed time since the
        observed start, read when the debounce decides (+308 s), and not on the
        302 s a recorded off would have given.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=300))
            await _report(hass, "unavailable", started + timedelta(seconds=300))
            frozen.tick(timedelta(seconds=2))
            await _report(hass, "off", started + timedelta(seconds=302))

            run = await c._sc_find_run(2)
            assert not run.get(const.RUN_VALVE_OFF)
            observed = dt_util.parse_datetime(run[const.RUN_OBSERVED_START])

            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)
            decided = dt_util.utcnow()

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(
            (decided - observed).total_seconds(), abs=0.01
        )  # 308 s, not 302

    async def test_an_unreported_close_seven_seconds_early_stays_partial(self, hass):
        """No off report: the margin is not added to a clock that holds the debounce.

        The valve drops out at +590 s and comes back off at +593 s, so nothing
        is recorded and the debounce decides at +598 s, exactly as it would
        live. The old rule reads that clock: 598 + 1 < 600 is a partial. The
        margin as tolerance on the same clock (598 + 4 >= 600) would complete
        it, and with it any close nobody reported up to 9 s short of the plan.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=590))
            await _report(hass, "unavailable", started + timedelta(seconds=590))
            frozen.tick(timedelta(seconds=3))
            await _report(hass, "off", started + timedelta(seconds=593))
            assert not (await c._sc_find_run(2)).get(const.RUN_VALVE_OFF)

            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS)  # 598

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(598, abs=0.01)
        c._flow_calibration_check.assert_not_awaited()

    async def test_an_unreported_close_inside_the_old_second_completes_for_its_plan(
        self, hass
    ):
        """No off report, decided at +599.5 s: completed and recorded for the plan.

        599.5 + 1 >= 600 completes under the old rule, through the finish that
        has no reported window to record, so actual_s is planned_s and not the
        599.5 s the clock read after the debounce.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=592))
            await _report(hass, "unavailable", started + timedelta(seconds=592))
            frozen.tick(timedelta(seconds=2.5))
            await _report(hass, "off", started + timedelta(seconds=594.5))
            assert not (await c._sc_find_run(2)).get(const.RUN_VALVE_OFF)

            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS)  # 599.5

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600

    async def test_a_record_from_before_the_update_keeps_the_old_rule(self, hass):
        """No frozen margin: elapsed at the decision + 1 >= planned, planned_s kept.

        Closed at 593.5 s, so the debounce decides at 599.5 s. The old rule
        completes that with actual_s == planned_s; the window rule would have
        recorded 599.5 s, so this pins that such a record is not routed there.
        """
        c = _coord(hass)

        def _strip_the_new_keys():
            for record in c._cfg[const.CONF_ACTIVE_VALVE_RUNS]:
                del record[const.RUN_LATENCY_MARGIN]
                del record[const.RUN_VALVE_ON]

        await _run_until_the_valve_closes(
            hass, c, _zone(), 593.5, before=_strip_the_new_keys
        )

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600


class TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged:
    """A close reported later than the margin is still finished for its plan (#139).

    Known and deliberately unchanged, as agreed on #139 (2026-09-16). With the
    off reported at +606 and a margin of 4 s the debounce would decide at +611,
    but the backstop is due at +609 (600 + 5 + 4) and comes first. It finishes
    the run for planned_s, as the backstop always has, and the off report
    already on the record is not used. Settling that run on the reported
    window instead would only make its record better than it is today, not
    close a hole the grace opens, so it waits. Pinned so it reads as a
    decision, not an oversight, and so changing it is a decision too.
    """

    async def test_the_backstop_finishes_it_for_the_plan_before_the_debounce(
        self, hass
    ):
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 4}))
            frozen.tick(timedelta(seconds=606))
            await _report(hass, "off", started + timedelta(seconds=606))

            run = await c._sc_find_run(2)
            reported = (started + timedelta(seconds=606)).isoformat()
            assert run[const.RUN_VALVE_OFF] == reported
            assert c._watchers()[2].finish_cancel is not None  # due at 611

            await _advance(hass, frozen, 4)  # 610: the backstop (609) is out

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == kw["planned_s"] == 600  # not the reported 606

            await _advance(hass, frozen, 2)  # 612: where the debounce was due

            c._record_run.assert_awaited_once()  # no second settle
            watcher = c._watchers().get(2)
            assert watcher is None or watcher.finish_cancel is None  # none pending
            assert not c._sc_cleanup_timers()


class TestAWriteOnlyValveIsUntouched:
    async def test_a_zone_with_no_confirm_entity_is_not_watched(self, hass):
        """Nothing to subscribe to, and the hardware still owns the close."""
        c = _coord(hass)

        await _dispatch(hass, c, _zone(confirm=None))

        run = await c._sc_find_run(2)
        assert const.RUN_WATCH_ENTITY not in run
        assert const.RUN_OBSERVED_START not in run
        assert not c._watchers()

    async def test_an_unreadable_confirm_entity_is_not_watched(self, hass):
        """``None`` from the confirm poll means "cannot verify", not "confirmed"."""
        c = _coord(hass)

        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        run = await c._sc_find_run(2)
        assert const.RUN_WATCH_ENTITY not in run
        assert not c._watchers()


class TestTheSubscriptionSurvivesARestart:
    async def test_a_run_still_inside_its_window_is_re_adopted(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}  # the subscription lived in memory only

        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        assert 2 in c._watchers()

    async def test_and_it_still_ends_the_run_on_a_valve_off(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}
        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        await _off(hass)

        assert await c._sc_find_run(2) is None
