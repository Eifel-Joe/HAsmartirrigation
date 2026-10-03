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
